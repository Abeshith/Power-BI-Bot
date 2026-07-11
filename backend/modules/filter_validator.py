import json
from typing import Dict, Any

schema = None


def set_schema(dashboard_schema: dict):
    global schema
    schema = dashboard_schema


def validate_filter(filter_name: str, filter_value: Any) -> bool:
    if not schema:
        return True
    
    column_info = schema.get("columns", {}).get(filter_name)
    
    if not column_info:
        return True
    
    # Support both valid_values and distinct_values
    valid_values = column_info.get("valid_values") or column_info.get("distinct_values", [])
    
    if not valid_values:
        return True
    
    if isinstance(filter_value, list):
        return all(v in valid_values for v in filter_value)
    else:
        return filter_value in valid_values


def filter_validator(dax_query: str, filters: Dict[str, Any], dashboard_schema: dict = None) -> Dict[str, Any]:
    if dashboard_schema:
        set_schema(dashboard_schema)
    
    errors = []
    warnings = []
    
    for filter_name, filter_value in filters.items():
        if filter_value is None or filter_name == "date_range":
            continue
        
        if not validate_filter(filter_name, filter_value):
            errors.append(f"Invalid value for {filter_name}: {filter_value}")
    
    if filters.get("date_range"):
        date_range = filters["date_range"]
        if isinstance(date_range, dict):
            start = date_range.get("start_date")
            end = date_range.get("end_date")
            if start and end and start > end:
                errors.append("Start date must be before end date")
    
    result = {
        "valid": len(errors) == 0,
        "dax_query": dax_query,
        "errors": errors,
        "warnings": warnings,
        "status": "valid" if len(errors) == 0 else "invalid"
    }
    
    return result
