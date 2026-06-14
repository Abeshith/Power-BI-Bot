import json
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from typing import Dict, Any

column_mappings = None
TODAY = datetime.strptime("2026-06-13", "%Y-%m-%d")
CURRENT_YEAR = 2026
CURRENT_QUARTER = "Q2"


def set_mappings(mappings: dict):
    global column_mappings
    column_mappings = mappings or {}


def parse_time_period(time_period: str) -> Dict[str, Any]:
    if not time_period:
        return None
    
    time_period_lower = time_period.lower()
    
    if not column_mappings:
        return None
    
    mapping = column_mappings.get("time_period_mappings", {})
    
    if time_period_lower in mapping:
        period_info = mapping[time_period_lower]
        return convert_time_offset(period_info)
    
    return None


def convert_time_offset(period_info: Dict) -> Dict[str, Any]:
    period_type = period_info.get("type")
    value = period_info.get("value", 0)
    
    if period_type == "year_offset":
        target_year = CURRENT_YEAR + value
        return {
            "type": "year",
            "start_date": f"{target_year}-01-01",
            "end_date": f"{target_year}-12-31"
        }
    
    elif period_type == "quarter_offset":
        quarters = {"Q1": (1, 3), "Q2": (4, 6), "Q3": (7, 9), "Q4": (10, 12)}
        if value == -1:
            quarter_num = list(quarters.keys()).index(CURRENT_QUARTER)
            target_quarter = list(quarters.keys())[max(0, quarter_num - 1)]
        else:
            target_quarter = CURRENT_QUARTER
        
        month_range = quarters[target_quarter]
        
        return {
            "type": "quarter",
            "start_date": f"{CURRENT_YEAR}-{month_range[0]:02d}-01",
            "end_date": f"{CURRENT_YEAR}-{month_range[1]:02d}-28"
        }
    
    elif period_type == "month_offset":
        if value == -1:
            target_date = TODAY - relativedelta(months=1)
        else:
            target_date = TODAY
        
        first_day = target_date.replace(day=1)
        if target_date.month == 12:
            last_day = first_day.replace(year=first_day.year+1, month=1) - timedelta(days=1)
        else:
            last_day = first_day.replace(month=first_day.month+1) - timedelta(days=1)
        
        return {
            "type": "month",
            "start_date": first_day.strftime("%Y-%m-%d"),
            "end_date": last_day.strftime("%Y-%m-%d")
        }
    
    elif period_type == "week_offset":
        if value == -1:
            target_date = TODAY - timedelta(days=7)
        else:
            target_date = TODAY
        
        return {
            "type": "week",
            "start_date": (target_date - timedelta(days=target_date.weekday())).strftime("%Y-%m-%d"),
            "end_date": target_date.strftime("%Y-%m-%d")
        }
    
    return None


def reasoning_engine(resolved_entities: Dict[str, Any], mappings: dict = None) -> Dict[str, Any]:
    if mappings:
        set_mappings(mappings)
    
    result = {
        "filters": {},
        "validations": [],
        "errors": []
    }
    
    for key, value in resolved_entities.items():
        if value is None:
            continue
        
        if "date" in key.lower() or "time" in key.lower() or "period" in key.lower():
            time_parsed = parse_time_period(str(value))
            if time_parsed:
                result["filters"]["date_range"] = time_parsed
        else:
            result["filters"][key] = value
    
    result["status"] = "validated"
    
    return result
