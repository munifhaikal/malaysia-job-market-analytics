import os
import json
import time
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# ── API config ───────────────────────────────────────────────
JSEARCH_API_KEY = os.getenv("JSEARCH_API_KEY")
API_URL = "https://api.openwebninja.com/jsearch/search-v2"
HEADERS = {"X-API-Key": JSEARCH_API_KEY}

# ── Search queries ───────────────────────────────────────────
SEARCH_QUERIES = [
    "data analyst Malaysia",
    "data scientist Malaysia",
    "data engineer Malaysia",
    "machine learning engineer Malaysia",
    "business intelligence Malaysia",
    "AI engineer Malaysia"
]

PAGES_PER_QUERY = 5
DELAY_BETWEEN_CALLS = 7


def save_json_backup(data: list, query: str):
    """Save raw JSON response to raw_data/jsearch/ as backup."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_query = query.replace(" ", "_")
    filename = f"raw_data/jsearch/{safe_query}_{timestamp}.json"

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"  Saved: {filename}")
    return filename


def fetch_page(params):
    """Fetch one page from JSearch API with retry on timeout."""
    try:
        response = requests.get(
            API_URL,
            headers=HEADERS,
            params=params,
            timeout=60
        )
        return response

    except requests.exceptions.Timeout:
        print(f"  Request timed out, retrying in 10 seconds...")
        time.sleep(10)
        try:
            response = requests.get(
                API_URL,
                headers=HEADERS,
                params=params,
                timeout=60
            )
            print(f"  Retry succeeded.")
            return response
        except requests.exceptions.Timeout:
            print(f"  Retry also timed out, skipping this page.")
            return None
        except Exception as e:
            print(f"  Retry failed: {e}")
            return None

    except Exception as e:
        print(f"  Unexpected error: {e}")
        return None


def collect_query(query: str) -> int:
    """Collect all pages for one search query. Returns total jobs saved."""
    print(f"\nCollecting: {query}")
    all_jobs = []
    cursor = None
    page = 1

    while page <= PAGES_PER_QUERY:
        print(f"  Page {page}...")

        params = {
            "query": query,
            "num_pages": 1,
            "country": "my"
        }

        if cursor:
            params["cursor"] = cursor

        response = fetch_page(params)

        if response is None:
            print(f"  Skipping page {page} due to failed request.")
            break

        if response.status_code != 200:
            print(f"  API error: {response.status_code} {response.text}")
            break

        data = response.json()
        jobs = data.get("data", {}).get("jobs", [])
        next_cursor = data.get("data", {}).get("cursor")

        if not jobs:
            print(f"  No jobs returned on page {page}, stopping.")
            break

        print(f"  Got {len(jobs)} jobs")
        all_jobs.extend(jobs)
        cursor = next_cursor

        if not cursor:
            print(f"  No more pages available.")
            break

        page += 1
        time.sleep(DELAY_BETWEEN_CALLS)

    save_json_backup(all_jobs, query)
    print(f"  Total jobs saved for this query: {len(all_jobs)}")
    return len(all_jobs)


def run_collector():
    print("=" * 60)
    print("JSearch Collector Starting")
    print("=" * 60)

    total = 0
    for query in SEARCH_QUERIES:
        count = collect_query(query)
        total += count
        time.sleep(DELAY_BETWEEN_CALLS)

    print("\n" + "=" * 60)
    print(f"Collection complete. Total jobs saved to JSON: {total}")
    print(f"Files saved to: raw_data/jsearch/")
    print(f"Run uploader_jsearch.py to load into database.")
    print("=" * 60)


if __name__ == "__main__":
    run_collector()