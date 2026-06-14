import requests
import json
import time
from datetime import datetime

BACKEND_URL = "http://localhost:8000"

class TestHarness:
    def __init__(self, backend_url=BACKEND_URL):
        self.backend_url = backend_url
        self.session = requests.Session()
        self.test_results = []

    def test_health(self):
        print("\n=== Testing Health Check ===")
        try:
            response = self.session.get(f"{self.backend_url}/health")
            if response.status_code == 200:
                print("✓ Backend is healthy")
                print(f"Response: {response.json()}")
                self.test_results.append(("Health Check", True, None))
                return True
            else:
                print("✗ Backend returned error")
                self.test_results.append(("Health Check", False, response.status_code))
                return False
        except Exception as e:
            print(f"✗ Error: {str(e)}")
            self.test_results.append(("Health Check", False, str(e)))
            return False

    def register_test_schema(self):
        print("\n=== Registering Test Schema ===")
        schema = {
            "tables": ["Sales", "Product"],
            "columns": {
                "sentiment": {
                    "data_type": "string",
                    "table": "Sales",
                    "valid_values": ["Positive", "Negative", "Neutral"]
                },
                "country": {
                    "data_type": "string",
                    "table": "Sales",
                    "valid_values": ["USA", "Germany", "India", "Brazil"]
                },
                "region": {
                    "data_type": "string",
                    "table": "Sales",
                    "valid_values": ["North", "South", "East", "West"]
                },
                "product_category": {
                    "data_type": "string",
                    "table": "Product",
                    "valid_values": ["Electronics", "Home", "Clothing"]
                },
                "revenue": {
                    "data_type": "numeric",
                    "table": "Sales"
                },
                "order_date": {
                    "data_type": "date",
                    "table": "Sales"
                }
            },
            "date_columns": ["order_date"],
            "categorical_columns": ["sentiment", "country", "region", "product_category"],
            "numeric_columns": ["revenue"]
        }

        try:
            response = self.session.post(
                f"{self.backend_url}/api/schema/register",
                json=schema,
                headers={"Content-Type": "application/json"}
            )
            if response.status_code == 200:
                print("✓ Schema registered successfully")
                print(f"Response: {response.json()}")
                self.test_results.append(("Register Schema", True, None))
                return True
            else:
                print(f"✗ Failed to register schema: {response.status_code}")
                print(f"Response: {response.text}")
                self.test_results.append(("Register Schema", False, response.status_code))
                return False
        except Exception as e:
            print(f"✗ Error: {str(e)}")
            self.test_results.append(("Register Schema", False, str(e)))
            return False

    def test_query(self, query_text):
        print(f"\n=== Testing Query: '{query_text}' ===")
        try:
            response = self.session.post(
                f"{self.backend_url}/api/parse",
                json={"query": query_text, "apply_filters": True},
                headers={"Content-Type": "application/json"}
            )

            if response.status_code == 200:
                result = response.json()
                print("✓ Query processed successfully")
                print(f"Intent: {result.get('intent')}")
                print(f"Entities: {json.dumps(result.get('entities'), indent=2)}")
                print(f"Filter Count: {len(result.get('filters', []))}")
                print(f"DAX Query: {result.get('dax_query')}")
                print(f"Filters: {json.dumps(result.get('filters'), indent=2)}")
                self.test_results.append(("Query: " + query_text[:30], True, None))
                return True
            else:
                print(f"✗ Query failed: {response.status_code}")
                print(f"Response: {response.text}")
                self.test_results.append(("Query: " + query_text[:30], False, response.status_code))
                return False
        except Exception as e:
            print(f"✗ Error: {str(e)}")
            self.test_results.append(("Query: " + query_text[:30], False, str(e)))
            return False

    def test_intent_extraction(self, query_text):
        print(f"\n=== Testing Intent Extraction: '{query_text}' ===")
        try:
            response = self.session.post(
                f"{self.backend_url}/api/intent",
                json={"query": query_text},
                headers={"Content-Type": "application/json"}
            )

            if response.status_code == 200:
                result = response.json()
                print("✓ Intent extracted successfully")
                print(f"Intent: {result.get('intent')}")
                print(f"Confidence: {result.get('confidence')}")
                print(f"Entities: {json.dumps(result.get('entities'), indent=2)}")
                self.test_results.append(("Intent: " + query_text[:30], True, None))
                return True
            else:
                print(f"✗ Intent extraction failed: {response.status_code}")
                self.test_results.append(("Intent: " + query_text[:30], False, response.status_code))
                return False
        except Exception as e:
            print(f"✗ Error: {str(e)}")
            self.test_results.append(("Intent: " + query_text[:30], False, str(e)))
            return False

    def get_schema(self):
        print("\n=== Fetching Current Schema ===")
        try:
            response = self.session.get(f"{self.backend_url}/api/schema")
            if response.status_code == 200:
                schema = response.json()
                print("✓ Schema retrieved successfully")
                print(f"Tables: {schema.get('tables')}")
                print(f"Columns: {list(schema.get('columns', {}).keys())}")
                self.test_results.append(("Get Schema", True, None))
                return schema
            else:
                print(f"✗ Failed to get schema: {response.status_code}")
                self.test_results.append(("Get Schema", False, response.status_code))
                return None
        except Exception as e:
            print(f"✗ Error: {str(e)}")
            self.test_results.append(("Get Schema", False, str(e)))
            return None

    def run_all_tests(self):
        print("\n" + "="*60)
        print("POWER BI BOT - TEST SUITE")
        print("="*60)
        print(f"Backend URL: {self.backend_url}")
        print(f"Test Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        if not self.test_health():
            print("\n✗ Backend not reachable. Stopping tests.")
            return False

        self.register_test_schema()
        time.sleep(1)

        test_queries = [
            "Show positive sentiment",
            "Filter by USA",
            "Display data from last quarter",
            "Show positive sentiment from USA",
            "Negative feedback from Germany last month",
            "Revenue from Electronics category in North region",
            "Last year's data for all countries",
        ]

        for query in test_queries:
            self.test_query(query)
            time.sleep(0.5)

        print("\n" + "="*60)
        print("TEST SUMMARY")
        print("="*60)

        passed = sum(1 for _, result, _ in self.test_results if result)
        failed = sum(1 for _, result, _ in self.test_results if not result)

        for test_name, result, error in self.test_results:
            status = "✓ PASS" if result else "✗ FAIL"
            print(f"{status}: {test_name}")
            if error:
                print(f"     Error: {error}")

        print("="*60)
        print(f"Total: {len(self.test_results)} | Passed: {passed} | Failed: {failed}")
        print(f"Success Rate: {(passed/len(self.test_results)*100):.1f}%")
        print("="*60)

        return failed == 0


if __name__ == "__main__":
    harness = TestHarness()
    harness.run_all_tests()
