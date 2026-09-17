import os
import json
import psycopg2
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

RAW_DATA_FOLDER = "raw_data/serpapi"

DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "port": os.getenv("DB_PORT"),
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD")
}


def get_db_connection():
    return psycopg2.connect(**DB_CONFIG)


def insert_raw_job(conn, job: dict, search_query: str):
    """Insert one raw job into raw.jobs table."""
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO raw.jobs (raw_json, data_source, search_query)
            VALUES (%s, %s, %s)
        """, (
            json.dumps(job),
            "serpapi",
            search_query
        ))
    conn.commit()


def extract_query_from_filename(filename: str) -> str:
    """Extract search query from filename like data_analyst_Malaysia_20260917.json"""
    name = filename.replace(".json", "")
    parts = name.split("_")
    query_parts = parts[:-2]
    return " ".join(query_parts).replace("_", " ")


def run_uploader():
    print("=" * 60)
    print("SerpApi Uploader Starting")
    print("=" * 60)

    files = [f for f in os.listdir(RAW_DATA_FOLDER) if f.endswith(".json")]

    if not files:
        print(f"No JSON files found in {RAW_DATA_FOLDER}")
        return

    print(f"Found {len(files)} JSON files to process.")

    conn = get_db_connection()
    total_inserted = 0
    total_skipped = 0

    for filename in sorted(files):
        filepath = os.path.join(RAW_DATA_FOLDER, filename)
        search_query = extract_query_from_filename(filename)

        print(f"\nProcessing: {filename}")
        print(f"  Search query: {search_query}")

        with open(filepath, "r", encoding="utf-8") as f:
            jobs = json.load(f)

        if not jobs:
            print(f"  File is empty, skipping.")
            continue

        inserted = 0
        skipped = 0

        for job in jobs:
            try:
                insert_raw_job(conn, job, search_query)
                inserted += 1
            except Exception as e:
                skipped += 1

        print(f"  Inserted: {inserted} | Skipped: {skipped}")
        total_inserted += inserted
        total_skipped += skipped

    conn.close()

    print("\n" + "=" * 60)
    print(f"Upload complete.")
    print(f"Total inserted: {total_inserted}")
    print(f"Total skipped:  {total_skipped}")
    print("=" * 60)


if __name__ == "__main__":
    run_uploader()