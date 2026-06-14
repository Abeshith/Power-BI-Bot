import json
from typing import Dict, Any

schema = None
column_mappings = None


def set_schema(dashboard_schema: dict, mappings: dict = None):
    global schema, column_mappings
    schema = dashboard_schema
    column_mappings = mappings or {}


def resolve_entity_to_column(entity_key: str) -> str:
    if not column_mappings:
        return entity_key
    
    return column_mappings.get("alias_mappings", {}).get(entity_key.lower(), entity_key)


def resolve_entities(entities: Dict[str, Any]) -> Dict[str, Any]:
    if not schema:
        return entities
    
    resolved = {}
    extracted = entities.get("extracted_filters", {})
    time_filters = entities.get("time_filters", {})
    
    for entity_key, entity_value in extracted.items():
        if entity_value:
            resolved[entity_key] = entity_value
    
    for time_key, time_value in time_filters.items():
        if time_value:
            resolved[time_key] = time_value
    
    return resolved


def semantic_resolver(entities: Dict[str, Any], dashboard_schema: dict = None, mappings: dict = None) -> Dict[str, Any]:
    if dashboard_schema:
        set_schema(dashboard_schema, mappings)
    
    resolved = resolve_entities(entities)
    
    result = {
        "resolved_entities": resolved,
        "status": "resolved",
        "total_filters": len(resolved)
    }
    
    return result
