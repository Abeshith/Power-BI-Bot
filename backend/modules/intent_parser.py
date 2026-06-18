import json
import logging
from groq import Groq
from config import GROQ_API_KEY, GROQ_MODEL
from modules.query_optimizer import get_relevant_columns
from modules.hybrid_intent_engine import classify_query_complexity, extract_simple_filters, format_simple_response

client = Groq(api_key=GROQ_API_KEY)
logger = logging.getLogger("PowerBIBot")

schema = None


def set_schema(dashboard_schema: dict):
    global schema
    schema = dashboard_schema


def get_schema_description() -> str:
    if not schema:
       return "No schema available"
    return get_schema_description_from_schema(schema)

def get_schema_description_from_schema(sch: dict) -> str:
    if not sch:
       return "No schema available"
    columns_info = []
    for col_name, col_info in sch.get("columns", {}).items():
       data_type = col_info.get("type", col_info.get("data_type", "string"))
       aliases = col_info.get("aliases", [])
       distinct_values = col_info.get("distinct_values", col_info.get("valid_values", []))
       alias_str = f" (also: {', '.join(aliases)})" if aliases else ""
       if distinct_values:
           values_str = ", ".join(str(v) for v in distinct_values[:10])
           columns_info.append(f"- {col_name}{alias_str}: [{values_str}]")
       else:
           columns_info.append(f"- {col_name}{alias_str}: {data_type}")
    return "\n".join(columns_info) if columns_info else "No columns defined"


def parse_intent(query: str, dashboard_schema: dict = None) -> dict:
    if dashboard_schema:
       set_schema(dashboard_schema)
      
    if not schema:
       return {
           "intent": "unknown",
           "entities": {},
           "confidence": 0.0,
           "error": "No schema configured"
       }
     
    complexity = classify_query_complexity(query)
    logger.info(f"Query complexity: {complexity}")
      
    if complexity == "simple":
       logger.info(f"Using simple filter extraction")
       simple_filters = extract_simple_filters(query, schema)
       logger.info(f"Simple filters result: {simple_filters}")
       if simple_filters:
           result = format_simple_response(simple_filters)
           logger.info(f"Returning early with simple response: {result}")
           return result
      
    optimized_schema = get_relevant_columns(query, schema)
    logger.info(f"Optimized schema keys: {list(optimized_schema.get('columns', {}).keys())}")
    schema_desc = get_schema_description_from_schema(optimized_schema)
    logger.info(f"Schema description sent to LLM: {schema_desc}")
     
    prompt = f"""You are a Power BI filter extractor. Analyze the query and extract ALL filter conditions.

SCHEMA (Available Columns):
{schema_desc}

USER QUERY: "{query}"

TASK: Extract filter conditions from the query by:
1. Find ANY words that match column values from the schema
2. Map them to their column names
3. For MULTIPLE values in one column, return as LIST: "column": ["value1", "value2"]
4. Be flexible - recognize variations and case-insensitive matching
5. When query mentions "and" or multiple values → include ALL of them as a list
6. Always return at least confidence 0.7 if ANY match found, 0.0 only if NO matches
7. Match EXACTLY against the available values in the schema

GENERIC EXAMPLES:
- "Show North region products" → Look for "North" and "products" in available columns and values
- "Electronics from East" → Find "Electronics", "East" in schema values
- "High profit items" → Find "High", "profit" in schema columns/values
- "North and South" → Return as LIST ["North", "South"] if same column
- "Smartphones and laptops" → Return as LIST ["Smartphones", "laptops"] if same column

Return ONLY valid JSON, no explanations."""

    try:
       response = client.chat.completions.create(
           model=GROQ_MODEL,
           messages=[{"role": "user", "content": prompt}],
           temperature=0.15,
           max_tokens=500
       )
        
       response_text = response.choices[0].message.content.strip()
       logger.info(f"LLM raw response: {response_text}")
        
       # Strip markdown code blocks if present (```json ... ```)
       if response_text.startswith("```"):
           response_text = response_text.split("```")[1]
           if response_text.startswith("json"):
               response_text = response_text[4:]
           response_text = response_text.strip()
        
       logger.info(f"Cleaned response: {response_text}")
        
       # Try to parse as JSON
       intent_data = json.loads(response_text)
       logger.info(f"Parsed intent_data: {intent_data}")
        
       # Handle flexible LLM response formats
       # If LLM returns flat structure (e.g., {"category": ["electronics"], "confidence": 0.7})
       # Reconstruct it to the expected format
       if "intent" not in intent_data:
           extracted = {}
           confidence = intent_data.pop("confidence", 0.7)
            
           # Remaining keys are filters
           for key, value in intent_data.items():
               if value is not None and key not in ["time_filters"]:
                   extracted[key] = value
            
           logger.info(f"Reconstructed extracted filters: {extracted}")
           intent_data = {
               "intent": "filter_data",
               "entities": {
                   "extracted_filters": extracted,
                   "time_filters": {}
               },
               "confidence": confidence
           }
        
       logger.info(f"Final intent_data: {intent_data}")
       # Ensure confidence is never 0 if filters were extracted
       if intent_data.get("entities", {}).get("extracted_filters"):
           if intent_data.get("confidence", 0) <= 0.1:
               intent_data["confidence"] = 0.8
        
       return intent_data
    except json.JSONDecodeError:
       return {
           "intent": "filter_data",
           "entities": {"extracted_filters": {}, "time_filters": {}},
           "confidence": 0.0,
           "error": f"Failed to parse LLM response: {response_text}"
       }
    except Exception as e:
       return {
           "intent": "unknown",
           "entities": {},
           "confidence": 0.0,
           "error": str(e)
       }
