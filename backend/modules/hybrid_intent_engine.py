def classify_query_complexity(query: str) -> str:
    simple_keywords = ["show", "filter", "display", "get", "find"]
    complex_keywords = ["compare", "trending", "average", "total", "calculate", "group", "sum", "count", "growing", "increasing"]
    
    query_lower = query.lower()
    
    complex_score = sum(1 for kw in complex_keywords if kw in query_lower)
    simple_score = sum(1 for kw in simple_keywords if kw in query_lower)
    
    if complex_score >= 2:
        return "complex"
    elif complex_score >= 1 or len(query.split()) > 10:
        return "medium"
    else:
        return "simple"

def extract_simple_filters(query: str, schema: dict) -> dict:
    filters = {}
    query_lower = query.lower()
    
    for col_name, col_info in schema.get("columns", {}).items():
        col_lower = col_name.lower()
        distinct_values = col_info.get("distinct_values", [])
        aliases = col_info.get("aliases", [])
        
        for val in distinct_values:
            val_lower = str(val).lower()
            if val_lower in query_lower:
                if col_name not in filters:
                    filters[col_name] = []
                filters[col_name].append(val)
        
        for alias in aliases:
            if alias.lower() in query_lower:
                for val in distinct_values:
                    if val not in filters.get(col_name, []):
                        if col_name not in filters:
                            filters[col_name] = []
                        filters[col_name].append(val)
                        break
    
    return filters

def format_simple_response(filters: dict) -> dict:
    response_filters = []
    for col, values in filters.items():
        response_filters.append({
            "target": {"table": "data", "column": col},
            "conditions": [{"operator": "In", "values": values}]
        })
    
    return {
        "intent": "filter_data",
        "entities": {col: {"type": "filter", "values": values} for col, values in filters.items()},
        "confidence": 0.9,
        "filters": response_filters,
        "source": "rule_engine"
    }
