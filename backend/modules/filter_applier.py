from typing import Dict, Any, List
import json


def convert_to_powerbi_filter(filters: Dict[str, Any], table_name: str = "data") -> List[Dict[str, Any]]:
    """Build BasicFilter-style (In operator) objects for categorical columns."""
    pbi_filters = []

    for filter_name, filter_value in filters.items():
        if filter_value is None or filter_name == "date_range":
            continue

        values = filter_value if isinstance(filter_value, list) else [filter_value]

        pbi_filters.append({
            "filterType": "basic",
            "$schema": "http://powerbi.com/product/schema#basic",
            "target": {"table": table_name, "column": filter_name},
            "operator": "In",
            "values": values
        })

    return pbi_filters


def convert_advanced_filters(advanced_filters: List[Dict[str, Any]], table_name: str = "data") -> List[Dict[str, Any]]:
    """Build AdvancedFilter-style objects for numeric/date columns."""
    pbi_filters = []

    for f in advanced_filters:
        col = f.get("target_column")
        conditions = f.get("conditions", [])
        if not col or not conditions:
            continue

        pbi_filters.append({
            "filterType": "advanced",
            "$schema": "http://powerbi.com/product/schema#advanced",
            "target": {"table": table_name, "column": col},
            "logicalOperator": f.get("logicalOperator", "And"),
            "conditions": conditions
        })

    return pbi_filters


def filter_applier(dax_query: str, filters: Dict[str, Any], table_name: str = "data",
                   advanced_filters: List[Dict[str, Any]] = None) -> Dict[str, Any]:
    pbi_filters = convert_to_powerbi_filter(filters, table_name)
    if advanced_filters:
        pbi_filters += convert_advanced_filters(advanced_filters, table_name)

    return {
        "filters": pbi_filters,
        "dax_generated": dax_query,
        "filter_count": len(pbi_filters),
        "status": "ready_to_apply"
    }

