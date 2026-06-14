def clean_query(query: str) -> str:
    return query.strip().lower()


def parse_date_string(date_str: str):
    from datetime import datetime
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        return None


def dict_to_json(data: dict) -> str:
    import json
    return json.dumps(data, indent=2)
