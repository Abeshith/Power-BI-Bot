from typing import Dict, Any

schema = None
column_mappings = None


def set_schema(dashboard_schema: dict, mappings: dict = None):
    global schema, column_mappings
    schema = dashboard_schema
    column_mappings = mappings or {}


def find_value_in_schema(value: str) -> Dict[str, Any]:
    """Search all categorical columns for a value (case-insensitive). Returns {col: exact_value}."""
    if not schema:
        return {}
    
    value_lower = value.lower()
    matches = {}
    
    for col_name, col_info in schema.get("columns", {}).items():
        for v in col_info.get("distinct_values", []):
            if str(v).lower() == value_lower:
                matches[col_name] = v  # Return exact case from schema
                break
    
    return matches


def resolve_entities(entities: Dict[str, Any]) -> Dict[str, Any]:
    if not schema:
        return entities

    resolved = {}
    extracted = entities.get("extracted_filters", {})
    time_filters = entities.get("time_filters", {})

    for entity_key, entity_value in extracted.items():
        if not entity_value:
            continue

        values = entity_value if isinstance(entity_value, list) else [entity_value]
        validated_values = []

        for val in values:
            val_lower = str(val).lower()

            # Check if entity_key is a valid column in schema
            col_info = schema.get("columns", {}).get(entity_key, {})
            distinct = col_info.get("distinct_values", [])

            if distinct:
                # Column exists and has values - find exact case match
                match = next((v for v in distinct if str(v).lower() == val_lower), None)
                if match:
                    validated_values.append(match)
                else:
                    # Value not in this column - search all columns
                    found = find_value_in_schema(val)
                    for correct_col, exact_val in found.items():
                        if correct_col not in resolved:
                            resolved[correct_col] = []
                        if exact_val not in resolved[correct_col]:
                            resolved[correct_col].append(exact_val)
            else:
                # Column has no distinct_values - search all columns for the value
                found = find_value_in_schema(val)
                if found:
                    for correct_col, exact_val in found.items():
                        if correct_col not in resolved:
                            resolved[correct_col] = []
                        if exact_val not in resolved[correct_col]:
                            resolved[correct_col].append(exact_val)
                else:
                    # No schema match - keep as-is (LLM best guess)
                    validated_values.append(val)

        if validated_values:
            if entity_key not in resolved:
                resolved[entity_key] = []
            resolved[entity_key].extend(validated_values)

    for time_key, time_value in time_filters.items():
        if time_value:
            resolved[time_key] = time_value

    # Flatten single-item lists to strings for consistency
    for k, v in resolved.items():
        if isinstance(v, list) and len(v) == 1:
            resolved[k] = v[0]

    return resolved


def semantic_resolver(entities: Dict[str, Any], dashboard_schema: dict = None, mappings: dict = None) -> Dict[str, Any]:
    if dashboard_schema:
        set_schema(dashboard_schema, mappings)

    resolved = resolve_entities(entities)

    return {
        "resolved_entities": resolved,
        "status": "resolved",
        "total_filters": len(resolved)
    }
