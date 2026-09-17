import os
import json
import time
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# ── API config ───────────────────────────────────────────────
SERPAPI_KEY = os.getenv("SERPAPI_KEY")
API_URL = "https://serpapi.com/search.json"

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
    """Save raw JSON response to raw_data/serpapi/ as backup."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_query = query.replace(" ", "_")
    filename = f"raw_data/serpapi/{safe_query}_{timestamp}.json"

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"  Saved: {filename}")
    return filename


def fetch_page(params):
    """Fetch one page from SerpApi with retry on timeout."""
    try:
        response = requests.get(
            API_URL,
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
    next_page_token = None
    page = 1

    while page <= PAGES_PER_QUERY:
        print(f"  Page {page}...")

        params = {
            "engine": "google_jobs",
            "q": query,
            "gl": "my",
            "hl": "en",
            "api_key": SERPAPI_KEY
        }

        if next_page_token:
            params["next_page_token"] = next_page_token

        response = fetch_page(params)

        if response is None:
            print(f"  Skipping page {page} due to failed request.")
            break

        if response.status_code != 200:
            print(f"  API error: {response.status_code} {response.text}")
            break

        data = response.json()
        jobs = data.get("jobs_results", [])
        pagination = data.get("serpapi_pagination", {})
        next_page_token = pagination.get("next_page_token")

        if not jobs:
            print(f"  No jobs returned on page {page}, stopping.")
            break

        print(f"  Got {len(jobs)} jobs")
        all_jobs.extend(jobs)

        if not next_page_token:
            print(f"  No more pages available.")
            break

        page += 1
        time.sleep(DELAY_BETWEEN_CALLS)

    save_json_backup(all_jobs, query)
    print(f"  Total jobs saved for this query: {len(all_jobs)}")
    return len(all_jobs)


def run_collector():
    print("=" * 60)
    print("SerpApi Collector Starting")
    print("=" * 60)

    total = 0
    for query in SEARCH_QUERIES:
        count = collect_query(query)
        total += count
        time.sleep(DELAY_BETWEEN_CALLS)

    print("\n" + "=" * 60)
    print(f"Collection complete. Total jobs saved to JSON: {total}")
    print(f"Files saved to: raw_data/serpapi/")
    print(f"Run uploader_serpapi.py to load into database.")
    print("=" * 60)


if __name__ == "__main__":
    run_collector()