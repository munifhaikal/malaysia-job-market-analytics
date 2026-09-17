import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()

url = "https://api.openwebninja.com/jsearch/search-v2"

params = {
    "query": "data analyst Malaysia",
    "num_pages": 1,
    "country": "my"
}

headers = {
    "X-API-Key": os.getenv("JSEARCH_API_KEY")
}

response = requests.get(url, headers=headers, params=params)
print(f"Status code: {response.status_code}")
print(json.dumps(response.json(), indent=2))