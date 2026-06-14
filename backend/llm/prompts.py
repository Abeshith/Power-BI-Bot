import json

with open("schemas/dashboard_schema.json", "r") as f:
    schema = json.load(f)

schema_str = json.dumps(schema, indent=2)

INTENT_PARSER_PROMPT = f"""You are a business intelligence query parser for Power BI dashboards.

Available data schema:
{schema_str}

User Query: "{{query}}"

Extract the intent and entities from the query. Return ONLY valid JSON with this structure:
{{
    "intent": "filter_data",
    "entities": {{
        "sentiment": "value or null",
        "country": "value or null",
        "region": "value or null",
        "product_category": "value or null",
        "time_period": "value or null",
        "year": "value or null",
        "quarter": "value or null",
        "month": "value or null"
    }},
    "confidence": 0.0-1.0
}}

Only include entities mentioned in the query. Return null for others.
Do not include any other text, only JSON.
"""

SEMANTIC_RESOLVER_PROMPT = """Map extracted entities to valid Power BI column values.
If a value exists in the schema, return it. Otherwise, return null.

Entities: {entities_str}

Return ONLY valid JSON with resolved entities."""

REASONING_PROMPT = """Apply business logic and time calculations to filters.
Entities: {entities_str}

Calculate:
- Time periods (last month, quarter, year)
- Date ranges
- Validate business rules

Return ONLY valid JSON with calculated filters."""

FILTER_FORMAT_PROMPT = """Convert calculated filters to Power BI REST API format.
Filters: {filters_str}

Return ONLY valid JSON with Power BI filter format."""
