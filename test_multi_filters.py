import requests
import json

BACKEND_URL = "http://localhost:8000"

# Test schema (hospital data)
test_schema = {
    "tables": ["Hospital"],
    "columns": {
        "department": {
            "type": "text",
            "distinct_values": ["ICU", "Emergency", "Cardiology", "Surgery"]
        },
        "patient_condition": {
            "type": "text",
            "distinct_values": ["Stable", "Critical", "Recovering"]
        },
        "admission_status": {
            "type": "text",
            "distinct_values": ["Admitted", "Discharged", "Pending"]
        }
    },
    "categorical_columns": ["department", "patient_condition", "admission_status"],
    "numeric_columns": [],
    "date_columns": [],
    "table_name": "Hospital"
}

# Register schema
print("=" * 60)
print("REGISTERING SCHEMA")
print("=" * 60)
response = requests.post(f"{BACKEND_URL}/api/schema/register", json=test_schema)
print(f"Status: {response.status_code}")
print(f"Response: {response.json()}\n")

# Test cases
test_queries = [
    "stable patients",
    "stable patients in ICU",
    "ICU",
    "ICU and Emergency",
    "critical patients",
    "ICU critical",
    "Emergency department",
    "stable in cardiology"
]

print("=" * 60)
print("TESTING QUERIES")
print("=" * 60)

for query in test_queries:
    print(f"\n📝 Query: '{query}'")
    print("-" * 60)
    
    response = requests.post(
        f"{BACKEND_URL}/api/parse",
        json={"query": query, "apply_filters": True}
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"✓ Status: {data.get('status')}")
        print(f"✓ Intent: {data.get('intent')}")
        print(f"✓ Filters Count: {len(data.get('filters', []))}")
        
        if data.get('filters'):
            for i, f in enumerate(data['filters'], 1):
                col = f.get('target', {}).get('column', 'unknown')
                vals = f.get('conditions', [{}])[0].get('values', [])
                print(f"  Filter {i}: {col} = {vals}")
        else:
            print("  No filters applied")
    else:
        print(f"✗ Error: {response.status_code}")
        print(f"  {response.text}")

print("\n" + "=" * 60)
print("TEST COMPLETE")
print("=" * 60)
