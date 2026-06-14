#!/usr/bin/env python3
"""
Test the fixed intent parser WITHOUT running the backend
"""
import json
from groq import Groq
from config import GROQ_API_KEY, GROQ_MODEL

client = Groq(api_key=GROQ_API_KEY)

schema = {
    "tables": ["hospital_data"],
    "columns": {
        "department": {
            "table": "hospital_data",
            "data_type": "string",
            "valid_values": ["Cardiology", "ICU", "Surgery", "Pediatrics", "Emergency"]
        },
        "patient_condition": {
            "table": "hospital_data",
            "data_type": "string",
            "valid_values": ["Stable", "Critical", "Recovering"]
        },
        "admission_status": {
            "table": "hospital_data",
            "data_type": "string",
            "valid_values": ["Admitted", "Discharged", "Transferred"]
        }
    }
}


def get_schema_description() -> str:
    columns_info = []
    for col_name, col_info in schema.get("columns", {}).items():
        data_type = col_info.get("data_type", "string")
        valid_values = col_info.get("valid_values", [])
        
        if valid_values:
            values_str = ", ".join(str(v) for v in valid_values)
            columns_info.append(f"- {col_name} ({data_type}): valid values are [{values_str}]")
        else:
            columns_info.append(f"- {col_name} ({data_type}): numeric or date field")
    
    return "\n".join(columns_info)


def parse_intent(query: str) -> dict:
    schema_desc = get_schema_description()
    
    prompt = f"""You are a Power BI filter extractor. Your task is to analyze a user query and extract filter conditions that match columns in the schema.

SCHEMA (Available Columns):
{schema_desc}

USER QUERY: "{query}"

INSTRUCTIONS:
1. Find all filter conditions in the query
2. Match query terms to EXACT column names and valid values from schema
3. For each match, create a filter entry: "column_name": "value"
4. If multiple values match one column, use a list: "column_name": ["value1", "value2"]
5. Return ONLY valid JSON, no markdown or explanations

EXAMPLES:
- Query: "Show ICU critical patients"
  Extract: department=ICU, patient_condition=Critical
  JSON: {{"intent":"filter_data","entities":{{"extracted_filters":{{"department":"ICU","patient_condition":"Critical"}},"time_filters":{{}}}},"confidence":0.95}}

- Query: "Emergency department"
  Extract: department=Emergency
  JSON: {{"intent":"filter_data","entities":{{"extracted_filters":{{"department":"Emergency"}},"time_filters":{{}}}},"confidence":0.9}}

- Query: "Admitted patients in Surgery"
  Extract: admission_status=Admitted, department=Surgery
  JSON: {{"intent":"filter_data","entities":{{"extracted_filters":{{"admission_status":"Admitted","department":"Surgery"}},"time_filters":{{}}}},"confidence":0.9}}

NOW extract filters from the query above. Return ONLY the JSON object."""

    try:
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=500
        )
        
        response_text = response.choices[0].message.content.strip()
        print(f"\n📝 LLM Response:\n{response_text}\n")
        
        intent_data = json.loads(response_text)
        return intent_data
    except json.JSONDecodeError as e:
        print(f"❌ JSON Parse Error: {e}")
        print(f"Raw response: {response_text}")
        return {"error": str(e)}
    except Exception as e:
        print(f"❌ Error: {e}")
        return {"error": str(e)}


if __name__ == "__main__":
    test_queries = [
        "Show ICU critical patients",
        "Emergency department",
        "Surgery patients"
    ]
    
    for query in test_queries:
        print(f"\n{'='*60}")
        print(f"🔍 Query: {query}")
        print(f"{'='*60}")
        result = parse_intent(query)
        print(json.dumps(result, indent=2))
