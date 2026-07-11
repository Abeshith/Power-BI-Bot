def enrich_schema(schema: dict) -> dict:
    """Preserve distinct_values and ensure all columns have the field set."""
    for col_name, col_info in schema.get("columns", {}).items():
        col_info.setdefault("aliases", [])
        col_info.setdefault("distinct_values", [])
    return schema
