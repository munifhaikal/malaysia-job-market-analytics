import os
import re
import psycopg2
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
    """Pull standardised fields from a SerpApi raw record."""
    detected = raw.get("detected_extensions", {}) or {}
    apply_options = raw.get("apply_options", []) or []

    min_sal, max_sal, sal_period = parse_serpapi_salary(
        detected.get("salary")
    )

    return {
        "job_id":                     raw.get("job_id"),
        "job_title":                  raw.get("title") or raw.get("job_title"),
        "employer_name":              raw.get("company_name"),
        "job_location":               raw.get("location"),
        "job_city":                   parse_serpapi_city(raw.get("location")),
        "job_country":                "MY",
        "job_employment_type":        detected.get("schedule_type"),
        "job_is_remote":              None,
        "job_description":            raw.get("description"),
        "job_min_salary":             min_sal,
        "job_max_salary":             max_sal,
        "job_salary_period":          sal_period,
        "job_posted_at_datetime_utc": None,
        "job_apply_link":             apply_options[0].get("link") if apply_options else None,
        "job_publisher":              raw.get("via"),
    }


# ── Helper parsers ────────────────────────────────────────────────────────────

def parse_serpapi_city(location: str):
    """
    Extract city from SerpApi location string.
    Examples:
      "Kuala Lumpur, Malaysia" -> "Kuala Lumpur"
      "Malaysia"               -> None
    """
    if not location:
        return None
    parts = [p.strip() for p in location.split(",")]
    if len(parts) >= 2:
        return parts[0]
    return None


def parse_serpapi_salary(salary_str: str):
    """
    Parse SerpApi salary string into (min, max, period).
    Examples:
      "RM 82K-RM 115K a year"     -> (82000, 115000, "YEAR")
      "RM 5,000-RM 8,000 a month" -> (5000, 8000, "MONTH")
      None                         -> (None, None, None)
    """
    if not salary_str:
        return None, None, None

    salary_str = salary_str.upper().replace(",", "")

    # Determine period
    if "YEAR" in salary_str or "ANNUAL" in salary_str:
        period = "YEAR"
    elif "MONTH" in salary_str:
        period = "MONTH"
    elif "HOUR" in salary_str:
        period = "HOUR"
    else:
        period = None

    # Extract numbers (handles K suffix)
    numbers = re.findall(r"[\d]+\.?[\d]*K?", salary_str)
    parsed = []
    for n in numbers:
        if n.endswith("K"):
            parsed.append(float(n[:-1]) * 1000)
        else:
            parsed.append(float(n))

    if len(parsed) >= 2:
        return parsed[0], parsed[1], period
    elif len(parsed) == 1:
        return parsed[0], parsed[0], period
    return None, None, None


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
        """, {**fields, "search_query": search_query, "data_source": "serpapi"})
    conn.commit()


# ── Main ──────────────────────────────────────────────────────────────────────

def run_serpapi_transformer(conn=None):
    """
    Transform all SerpApi records from raw.jobs into staging.jobs.
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
            WHERE data_source = 'serpapi'
            ORDER BY id
        """)
        rows = cur.fetchall()

    print(f"  [SerpApi] Found {len(rows)} raw records.")

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
            print(f"  [SerpApi] Error on raw id {raw_id}: {e}")
            errors += 1
            conn.rollback()

    if close_conn:
        conn.close()

    print(f"  [SerpApi] Inserted: {inserted} | Skipped: {skipped} | Errors: {errors}")
    return inserted, skipped, errors


if __name__ == "__main__":
    print("=" * 60)
    print("SerpApi Transformer  (raw -> staging)")
    print("=" * 60)
    run_serpapi_transformer()
    print("=" * 60)
    print("Done.")
    print("=" * 60)

