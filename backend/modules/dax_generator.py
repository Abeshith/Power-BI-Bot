import json
from typing import Dict, Any


def build_dax_filters(filters: Dict[str, Any]) -> str:
    dax_parts = []
    
    for filter_key, filter_value in filters.items():
        if filter_value is None:
            continue
        
        if filter_key == "date_range":
            date_range = filter_value
            if isinstance(date_range, dict) and "start_date" in date_range and "end_date" in date_range:
                start = date_range["start_date"]
                end = date_range["end_date"]
                start_parts = start.split("-")
                end_parts = end.split("-")
                
                dax_date = f"[DateColumn] >= DATE({start_parts[0]},{start_parts[1]},{start_parts[2]}) AND [DateColumn] <= DATE({end_parts[0]},{end_parts[1]},{end_parts[2]})"
                dax_parts.append(dax_date)
        else:
            column_name = filter_key.replace("_", " ").title()
            if isinstance(filter_value, str):
                dax_parts.append(f"[{column_name}] = '{filter_value}'")
            elif isinstance(filter_value, (int, float)):
                dax_parts.append(f"[{column_name}] = {filter_value}")
            elif isinstance(filter_value, list):
                values_str = "', '".join([str(v) for v in filter_value])
                dax_parts.append(f"[{column_name}] IN ('{values_str}')")
    
    dax_filter = " AND ".join(dax_parts) if dax_parts else ""
    
    return dax_filter


def dax_generator(filters: Dict[str, Any]) -> Dict[str, Any]:
    dax_query = build_dax_filters(filters)
    
    result = {
        "dax_where_clause": dax_query,
        "filters": filters,
        "status": "generated"
    }
    
    return result
