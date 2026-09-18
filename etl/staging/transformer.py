import os
import psycopg2
from dotenv import load_dotenv

from transformer_jsearch import run_jsearch_transformer
from transformer_serpapi import run_serpapi_transformer

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


def run_transformer():
    print("=" * 60)
    print("Transformer Starting  (raw -> staging)")
    print("=" * 60)

    conn = get_db_connection()

    print("\nRunning JSearch transformer...")
    j_inserted, j_skipped, j_errors = run_jsearch_transformer(conn)

    print("\nRunning SerpApi transformer...")
    s_inserted, s_skipped, s_errors = run_serpapi_transformer(conn)

    conn.close()

    print("\n" + "=" * 60)
    print("Transformer complete.")
    print(f"  JSearch  -> Inserted: {j_inserted} | Skipped: {j_skipped} | Errors: {j_errors}")
    print(f"  SerpApi  -> Inserted: {s_inserted} | Skipped: {s_skipped} | Errors: {s_errors}")
    print(f"  Total    -> Inserted: {j_inserted + s_inserted}")
    print("=" * 60)


if __name__ == "__main__":
    run_transformer()