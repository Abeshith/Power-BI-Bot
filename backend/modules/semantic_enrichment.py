from groq import Groq
import json

client = Groq()

def generate_aliases(column_name: str, column_type: str, sample_values: list) -> dict:
    prompt = f"""Generate 3-5 alternative names for this column. Return JSON only.
{{"aliases": ["alias1", "alias2"], "description": "brief"}}"""
    try:
        message = client.messages.create(
            model="mixtral-8x7b-32768",
            max_tokens=100,
            messages=[{"role": "user", "content": prompt}]
        )
        result = json.loads(message.content[0].text.strip())
        return {"aliases": result.get("aliases", []), "description": result.get("description", "")}
    except:
        return {"aliases": [], "description": ""}

def enrich_schema(schema: dict) -> dict:
    for col_name, col_info in schema.get("columns", {}).items():
        semantic = generate_aliases(col_name, col_info.get("type", "unknown"), col_info.get("distinct_values", []))
        col_info["aliases"] = semantic.get("aliases", [])
        col_info["description"] = semantic.get("description", "")
    return schema
