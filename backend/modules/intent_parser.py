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


def extract_filters_from_schema(query: str, dashboard_schema: dict) -> dict:
    """Pre-LLM: Search all categorical columns for exact value matches (case-insensitive, returns exact case)."""
    filters = {}
    query_lower = query.lower()

    for col_name, col_info in dashboard_schema.get("columns", {}).items():
        distinct_values = col_info.get("distinct_values", [])
        if not distinct_values:
            continue
        for val in distinct_values:
            if str(val).lower() in query_lower:
                if col_name not in filters:
                    filters[col_name] = []
                if val not in filters[col_name]:
                    filters[col_name].append(val)  # Exact case from schema

    return filters


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
            values_str = ", ".join(str(v) for v in distinct_values[:15])
            columns_info.append(f"- {col_name}{alias_str}: [{values_str}]")
        else:
            columns_info.append(f"- {col_name}{alias_str}: {data_type}")
    return "\n".join(columns_info) if columns_info else "No columns defined"


def get_schema_description() -> str:
    if not schema:
        return "No schema available"
    return get_schema_description_from_schema(schema)


def parse_intent(query: str, dashboard_schema: dict = None) -> dict:
    if dashboard_schema:
        set_schema(dashboard_schema)

    if not schema:
        return {"intent": "unknown", "entities": {}, "confidence": 0.0, "error": "No schema configured"}

    # STEP 1: Pre-LLM schema scan - finds exact values with correct case
    pre_extracted = extract_filters_from_schema(query, schema)
    if pre_extracted:
        logger.info(f"Pre-LLM extraction found: {pre_extracted}")
        result = format_simple_response(pre_extracted)
        logger.info(f"Returning pre-LLM response: {result}")
        return result

    complexity = classify_query_complexity(query)
    logger.info(f"Query complexity: {complexity}")

    if complexity == "simple":
        simple_filters = extract_simple_filters(query, schema)
        logger.info(f"Simple filters result: {simple_filters}")
        if simple_filters:
            return format_simple_response(simple_filters)

    optimized_schema = get_relevant_columns(query, schema)
    schema_desc = get_schema_description_from_schema(optimized_schema)
    logger.info(f"Schema description sent to LLM:\n{schema_desc}")

    prompt = f"""You are a Power BI filter extractor. Extract ALL filter conditions from the query.

SCHEMA (Available Columns and their EXACT values):
{schema_desc}

USER QUERY: "{query}"

RULES:
1. Match query words to the EXACT values shown in the schema above
2. Use the EXACT case as shown in the schema (e.g. "ICU" not "icu", "Stable" not "stable")
3. Map each value to its correct column
4. For multiple values in same column return as list
5. Return confidence 0.9 if matches found, 0.0 if none

Return ONLY valid JSON like: {{"column_name": ["ExactValue"], "confidence": 0.9}}"""

    try:
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=300
        )

        response_text = response.choices[0].message.content.strip()
        logger.info(f"LLM raw response: {response_text}")

        if response_text.startswith("```"):
            response_text = response_text.split("```")[1]
            if response_text.startswith("json"):
                response_text = response_text[4:]
            response_text = response_text.strip()

        # Extract JSON even if LLM adds explanation text before/after it
        start = response_text.find("{")
        end = response_text.rfind("}") + 1
        if start != -1 and end > start:
            response_text = response_text[start:end]

        intent_data = json.loads(response_text)
        logger.info(f"Parsed intent_data: {intent_data}")

        if "intent" not in intent_data:
            extracted = {}
            confidence = intent_data.pop("confidence", 0.7)
            for key, value in intent_data.items():
                if value is not None and key not in ["time_filters"]:
                    extracted[key] = value
            intent_data = {
                "intent": "filter_data",
                "entities": {"extracted_filters": extracted, "time_filters": {}},
                "confidence": confidence
            }

        logger.info(f"Final intent_data: {intent_data}")
        return intent_data

    except json.JSONDecodeError:
        return {
            "intent": "filter_data",
            "entities": {"extracted_filters": {}, "time_filters": {}},
            "confidence": 0.0
        }
    except Exception as e:
        return {"intent": "unknown", "entities": {}, "confidence": 0.0, "error": str(e)}
