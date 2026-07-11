from typing import Dict, Any, List
import json


def convert_to_powerbi_filter(filters: Dict[str, Any], table_name: str = "data") -> List[Dict[str, Any]]:
    """
    Convert backend filters to Power BI Advanced Filter format.
    Each column gets its own filter object, and Power BI applies them with AND logic.
    
    Example output:
    [
        {
            "$schema": "http://powerbi.com/product/schema#advanced",
            "target": {"table": "data", "column": "department"},
            "logicalOperator": "And",
            "conditions": [{"operator": "In", "values": ["ICU"]}]
        },
        {
            "$schema": "http://powerbi.com/product/schema#advanced",
            "target": {"table": "data", "column": "patient_condition"},
            "logicalOperator": "And",
            "conditions": [{"operator": "In", "values": ["Critical"]}]
        }
    ]
    """
    pbi_filters = []
    
    for filter_name, filter_value in filters.items():
        if filter_value is None or filter_name == "date_range":
            continue
        
        column_name = filter_name
        
        if isinstance(filter_value, list):
            values = filter_value
        else:
            values = [filter_value]
        
        pbi_filters.append({
            "$schema": "http://powerbi.com/product/schema#advanced",
            "target": {
                "table": table_name,
                "column": column_name
            },
            "logicalOperator": "And",
            "conditions": [
                {
                    "operator": "In",
                    "values": values
                }
            ]
        })
    
    return pbi_filters


def filter_applier(dax_query: str, filters: Dict[str, Any], table_name: str = "data") -> Dict[str, Any]:
    pbi_filters = convert_to_powerbi_filter(filters, table_name)
    
    result = {
        "filters": pbi_filters,
        "dax_generated": dax_query,
        "filter_count": len(pbi_filters),
        "status": "ready_to_apply"
    }
    
    return result

