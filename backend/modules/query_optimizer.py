from difflib import SequenceMatcher

def extract_query_keywords(query: str) -> list:
    keywords = query.lower().split()
    return [w for w in keywords if len(w) > 2]

def match_keyword_to_columns(keyword: str, schema: dict) -> list:
    matches = []
    threshold = 0.6
    
    for col_name, col_info in schema.get("columns", {}).items():
        col_lower = col_name.lower()
        aliases = col_info.get("aliases", [])
        distinct_values = col_info.get("distinct_values", [])
        
        if SequenceMatcher(None, keyword, col_lower).ratio() > threshold:
            matches.append(col_name)
            continue
        
        for alias in aliases:
            if SequenceMatcher(None, keyword, alias.lower()).ratio() > threshold:
                matches.append(col_name)
                break
        
        if col_name not in matches:
            for val in distinct_values[:10]:
                if str(val).lower() == keyword or SequenceMatcher(None, keyword, str(val).lower()).ratio() > 0.8:
                    matches.append(col_name)
                    break
    
    return list(set(matches))

def get_relevant_columns(query: str, schema: dict) -> dict:
    keywords = extract_query_keywords(query)
    relevant_cols = set()
    
    for keyword in keywords:
       matches = match_keyword_to_columns(keyword, schema)
       relevant_cols.update(matches)
    
    # If no matches found, return ALL columns (don't filter)
    # This way the LLM can see all available data to extract from
    filtered_schema = {
       "tables": schema.get("tables", []),
       "columns": schema.get("columns", {}),
       "categorical_columns": schema.get("categorical_columns", []),
       "numeric_columns": schema.get("numeric_columns", []),
       "date_columns": schema.get("date_columns", [])
    }
    
    return filtered_schema
