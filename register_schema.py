#!/usr/bin/env python3
"""
Register Hospital Dashboard schema with the backend.
CORRECTED: Using actual column names from Power BI data model
"""
import requests
import json

BACKEND_URL = "http://localhost:8000"

# CORRECTED schema based on actual Power BI columns visible in Data pane
schema = {
    "tables": ["hospital_data"],
    "columns": {
        "department": {
            "table": "hospital_data",
            "data_type": "string",
            "valid_values": ["Cardiology", "ICU", "Surgery", "Pediatrics", "Emergency"]
        },
        "patient_condition": {
            "table": "hospital_data",
            "data_type": "string",
            "valid_values": ["Stable", "Critical", "Recovering"]
        },
        "admission_status": {
            "table": "hospital_data",
            "data_type": "string",
            "valid_values": ["Admitted", "Discharged", "Transferred"]
        },
        "hospital_cost": {
            "table": "hospital_data",
            "data_type": "numeric",
            "valid_values": []
        },
        "length_of_stay": {
            "table": "hospital_data",
            "data_type": "numeric",
            "valid_values": []
        },
        "admission_date": {
            "table": "hospital_data",
            "data_type": "date",
            "valid_values": []
        },
        "discharge_date": {
            "table": "hospital_data",
            "data_type": "date",
            "valid_values": []
        },
        "Year": {
            "table": "hospital_data",
            "data_type": "numeric",
            "valid_values": []
        },
        "Quarter": {
            "table": "hospital_data",
            "data_type": "string",
            "valid_values": ["Q1", "Q2", "Q3", "Q4"]
        },
        "Month": {
            "table": "hospital_data",
            "data_type": "string",
            "valid_values": ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
        },
        "Day": {
            "table": "hospital_data",
            "data_type": "numeric",
            "valid_values": []
        }
    },
    "date_columns": ["admission_date", "discharge_date"],
    "categorical_columns": ["department", "patient_condition", "admission_status", "Quarter", "Month"],
    "numeric_columns": ["hospital_cost", "length_of_stay", "Year", "Day"]
}

def register_schema():
    """Send schema to backend"""
    try:
        response = requests.post(
            f"{BACKEND_URL}/api/schema/register",
            json=schema,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            print("✅ Schema registered successfully!")
            print(f"Response: {response.json()}")
            
            # Test multiple queries
            test_queries = [
                "Show ICU critical patients",
                "Emergency department",
                "Surgery patients"
            ]
            
            for test_query in test_queries:
                print(f"\n🔍 Testing query: '{test_query}'")
                test_request = {
                    "query": test_query,
                    "apply_filters": True
                }
                
                test_response = requests.post(
                    f"{BACKEND_URL}/api/parse",
                    json=test_request,
                    headers={"Content-Type": "application/json"}
                )
                
                if test_response.status_code == 200:
                    result = test_response.json()
                    print(f"✅ Filters: {json.dumps(result.get('filters', []), indent=2)}")
                else:
                    print(f"❌ Failed: {test_response.text}")
        else:
            print(f"❌ Schema registration failed: {response.text}")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    register_schema()

