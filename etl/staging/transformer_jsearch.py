import os
import re
import psycopg2
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "port": os.getenv("DB_PORT"),
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD")
}


def get_db_connection():
    return psycopg2.connect(**DB_CONFIG)


# ── Field extractor ───────────────────────────────────────────────────────────

def extract_fields(raw: dict) -> dict:
    """Pull standardised fields from a JSearch raw record."""
    return {
        "job_id":                     raw.get("job_id"),
        "job_title":                  raw.get("job_title"),
        "employer_name":              raw.get("employer_name"),
        "job_location":               raw.get("job_location"),
        "job_city":                   raw.get("job_city"),
        "job_country":                raw.get("job_country"),
        "job_employment_type":        raw.get("job_employment_type"),
        "job_is_remote":              raw.get("job_is_remote"),
        "job_description":            raw.get("job_description"),
        "job_min_salary":             raw.get("job_min_salary"),
        "job_max_salary":             raw.get("job_max_salary"),
        "job_salary_period":          raw.get("job_salary_period"),
        "job_posted_at_datetime_utc": parse_datetime(raw.get("job_posted_at_datetime_utc")),
        "job_apply_link":             raw.get("job_apply_link"),
        "job_publisher":              raw.get("job_publisher"),
    }


# ── Helper parsers ────────────────────────────────────────────────────────────

def parse_datetime(value: str):
    """Parse ISO 8601 datetime string into a Python datetime. Returns None on failure."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return None


# ── Cleaning ──────────────────────────────────────────────────────────────────

def clean_fields(fields: dict) -> dict:
    """Apply cleaning rules to extracted fields."""

    # Strip whitespace from all string fields
    for key, val in fields.items():
        if isinstance(val, str):
            fields[key] = val.strip() or None

    # Normalise employment type
    if fields.get("job_employment_type"):
        raw_type = fields["job_employment_type"].upper()
        if "FULL" in raw_type:
            fields["job_employment_type"] = "Full-time"
        elif "PART" in raw_type:
            fields["job_employment_type"] = "Part-time"
        elif "CONTRACT" in raw_type:
            fields["job_employment_type"] = "Contract"
        elif "INTERN" in raw_type:
            fields["job_employment_type"] = "Internship"
        elif "FREELANCE" in raw_type or "TEMPORARY" in raw_type:
            fields["job_employment_type"] = "Freelance"

    # Normalise country code
    if fields.get("job_country"):
        fields["job_country"] = fields["job_country"].upper()

    return fields


# ── Insert ────────────────────────────────────────────────────────────────────

def insert_staging_job(conn, fields: dict, search_query: str):
    """Insert one cleaned job into staging.jobs. Skips duplicates silently."""
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO staging.jobs (
                job_id, job_title, employer_name, job_location,
                job_city, job_country, job_employment_type,
                job_is_remote, job_description,
                job_min_salary, job_max_salary, job_salary_period,
                job_posted_at_datetime_utc, job_apply_link,
                job_publisher, search_query, data_source
            ) VALUES (
                %(job_id)s, %(job_title)s, %(employer_name)s, %(job_location)s,
                %(job_city)s, %(job_country)s, %(job_employment_type)s,
                %(job_is_remote)s, %(job_description)s,
                %(job_min_salary)s, %(job_max_salary)s, %(job_salary_period)s,
                %(job_posted_at_datetime_utc)s, %(job_apply_link)s,
                %(job_publisher)s, %(search_query)s, %(data_source)s
            )
            ON CONFLICT (job_id) DO NOTHING
        """, {**fields, "search_query": search_query, "data_source": "jsearch"})
    conn.commit()


# ── Main ──────────────────────────────────────────────────────────────────────

def run_jsearch_transformer(conn=None):
    """
    Transform all JSearch records from raw.jobs into staging.jobs.
    Accepts an optional existing connection (used when called from transformer.py).
    Returns (inserted, skipped, errors) counts.
    """
    close_conn = False
    if conn is None:
        conn = get_db_connection()
        close_conn = True

    with conn.cursor() as cur:
        cur.execute("""
            SELECT id, raw_json, search_query
            FROM raw.jobs
            WHERE data_source = 'jsearch'
            ORDER BY id
        """)
        rows = cur.fetchall()

    print(f"  [JSearch] Found {len(rows)} raw records.")

    inserted = 0
    skipped = 0
    errors = 0

    for row in rows:
        raw_id, raw_json, search_query = row

        try:
            fields = extract_fields(raw_json)

            if not fields.get("job_id"):
                skipped += 1
                continue

            fields = clean_fields(fields)
            insert_staging_job(conn, fields, search_query)
            inserted += 1

        except Exception as e:
            print(f"  [JSearch] Error on raw id {raw_id}: {e}")
            errors += 1
            conn.rollback()

    if close_conn:
        conn.close()

    print(f"  [JSearch] Inserted: {inserted} | Skipped: {skipped} | Errors: {errors}")
    return inserted, skipped, errors


if __name__ == "__main__":
    print("=" * 60)
    print("JSearch Transformer  (raw -> staging)")
    print("=" * 60)
    run_jsearch_transformer()
    print("=" * 60)
    print("Done.")
    print("=" * 60)

