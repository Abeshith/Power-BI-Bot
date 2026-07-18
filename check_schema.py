import requests
import json

BACKEND_URL = "http://localhost:8000"

# Get current schema
print("=" * 60)
print("CHECKING CURRENT SCHEMA")
print("=" * 60)

response = requests.get(f"{BACKEND_URL}/api/schema")
if response.status_code == 200:
    schema = response.json()
    print(f"\nTable: {schema.get('table_name')}")
    print(f"Total Columns: {len(schema.get('columns', {}))}\n")
    
    for col_name, col_info in schema.get("columns", {}).items():
        distinct_vals = col_info.get("distinct_values", [])
        print(f"Column: {col_name}")
        print(f"  Type: {col_info.get('type', 'unknown')}")
        print(f"  Distinct Values: {distinct_vals}")
        print(f"  Count: {len(distinct_vals)}")
        print()
else:
    print(f"Error: {response.status_code}")
    print(response.text)
