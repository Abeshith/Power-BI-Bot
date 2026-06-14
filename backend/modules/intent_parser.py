import json
from groq import Groq
from config import GROQ_API_KEY, GROQ_MODEL

client = Groq(api_key=GROQ_API_KEY)

schema = None


def set_schema(dashboard_schema: dict):
    global schema
    schema = dashboard_schema


def get_schema_description() -> str:
    if not schema:
       return "No schema available"
    
    columns_info = []
    for col_name, col_info in schema.get("columns", {}).items():
       data_type = col_info.get("data_type", "string")
       table = col_info.get("table", "unknown")
       valid_values = col_info.get("valid_values", [])
        
       if valid_values:
           values_str = ", ".join(str(v) for v in valid_values)
           columns_info.append(f"- {col_name} ({data_type}): valid values are [{values_str}]")
       else:
           columns_info.append(f"- {col_name} ({data_type}): numeric or date field")
    
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
    
    schema_desc = get_schema_description()
    
    prompt = f"""You are a Power BI filter extractor. Analyze the query and extract ALL filter conditions.

SCHEMA (Available Columns):
{schema_desc}

USER QUERY: "{query}"

TASK: Extract filter conditions from the query by:
1. Find ANY words that match column values from the schema
2. Map them to their column names
3. For MULTIPLE values in one column, return as LIST: "column": ["value1", "value2"]
4. Be flexible - recognize variations like:
   - "ICU" = department
   - "Critical" or "critical" = patient_condition
   - "Stable" or "stable" = patient_condition  
   - "Surgery" = department
   - "Emergency" = department
   - "Recovering" or "recovering" = patient_condition
   - "Admitted" = admission_status
5. For "patients" queries → look for department or patient_condition values
6. For "department" queries → extract department value
7. For status queries → extract admission_status value
8. When query mentions "and" between values → include ALL of them as a list
9. Always return at least confidence 0.7 if ANY match found, 0.0 only if NO matches

EXAMPLES:
- "Show ICU critical patients" → {{"intent":"filter_data","entities":{{"extracted_filters":{{"department":"ICU","patient_condition":"Critical"}},"time_filters":{{}}}},"confidence":0.95}}
- "Emergency department" → {{"intent":"filter_data","entities":{{"extracted_filters":{{"department":"Emergency"}},"time_filters":{{}}}},"confidence":0.9}}
- "Stable patients" → {{"intent":"filter_data","entities":{{"extracted_filters":{{"patient_condition":"Stable"}},"time_filters":{{}}}},"confidence":0.9}}
- "Surgery patients" → {{"intent":"filter_data","entities":{{"extracted_filters":{{"department":"Surgery"}},"time_filters":{{}}}},"confidence":0.9}}
- "ICU Patients" → {{"intent":"filter_data","entities":{{"extracted_filters":{{"department":"ICU"}},"time_filters":{{}}}},"confidence":0.9}}
- "Admitted in Cardiology" → {{"intent":"filter_data","entities":{{"extracted_filters":{{"admission_status":"Admitted","department":"Cardiology"}},"time_filters":{{}}}},"confidence":0.9}}
- "Cardiology and Surgery patients" → {{"intent":"filter_data","entities":{{"extracted_filters":{{"department":["Cardiology","Surgery"]}},"time_filters":{{}}}},"confidence":0.95}}
- "ICU and Emergency departments" → {{"intent":"filter_data","entities":{{"extracted_filters":{{"department":["ICU","Emergency"]}},"time_filters":{{}}}},"confidence":0.95}}

Return ONLY valid JSON, no explanations."""

    try:
       response = client.chat.completions.create(
           model=GROQ_MODEL,
           messages=[{"role": "user", "content": prompt}],
           temperature=0.15,
           max_tokens=500
       )
        
       response_text = response.choices[0].message.content.strip()
        
       # Try to parse as JSON
       intent_data = json.loads(response_text)
        
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
