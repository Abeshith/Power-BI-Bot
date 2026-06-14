from typing import Dict, Any, List
import json


def convert_to_powerbi_filter(filters: Dict[str, Any]) -> List[Dict[str, Any]]:
    pbi_filters = []
    
    for filter_name, filter_value in filters.items():
        if filter_value is None:
            continue
        
        if filter_name == "date_range":
            date_range = filter_value
            if isinstance(date_range, dict):
                pbi_filters.append({
                    "$schema": "http://powerbi.com/product/schema#advanced",
                    "target": {
                        "table": "hospital_data",
                        "column": "admission_date"
                    },
                    "logicalOperator": "And",
                    "conditions": [
                        {
                            "operator": "GreaterThanOrEqual",
                            "value": date_range.get("start_date")
                        },
                        {
                            "operator": "LessThanOrEqual",
                            "value": date_range.get("end_date")
                        }
                    ]
                })
        else:
            column_name = filter_name
            table_name = "hospital_data"
            
            if isinstance(filter_value, list):
                values = filter_value
            else:
                values = [filter_value]
            
            # Use proper Power BI Advanced Filter format
            pbi_filters.append({
                "$schema": "http://powerbi.com/product/schema#advanced",
                "target": {
                    "table": table_name,
                    "column": column_name
                },
                "logicalOperator": "Or",  # Use OR for multiple values (department IN (ICU, Surgery))
                "conditions": [
                    {
                        "operator": "In",
                        "values": values
                    }
                ]
            })
    
    return pbi_filters


def filter_applier(dax_query: str, filters: Dict[str, Any]) -> Dict[str, Any]:
    pbi_filters = convert_to_powerbi_filter(filters)
    
    result = {
        "filters": pbi_filters,
        "dax_generated": dax_query,
        "filter_count": len(pbi_filters),
        "status": "ready_to_apply"
    }
    
    return result

