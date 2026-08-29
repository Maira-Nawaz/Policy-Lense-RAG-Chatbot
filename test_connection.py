"""
Verifies the Supabase connection, pgvector extension, and expected tables exist
before any ingestion code is written. Run this after completing schema.sql.

Two check modes, run whichever your .env currently supports:
  1. REST check (SUPABASE_URL + SUPABASE_ANON_KEY) -- lightweight, works once schema.sql has
     been run, does NOT require the DB password. Good first check.
  2. Direct Postgres check (DATABASE_URL) -- deeper check, confirms pgvector extension is
     enabled and lists all expected tables directly. Requires the DB password from
     Settings > Database.

Setup:
    pip install python-dotenv psycopg2-binary requests
    cp .env.example .env   # then fill in real values
    python3 test_connection.py
"""
import os
import sys

try:
    from dotenv import load_dotenv
except ImportError:
    print("Missing dependency. Run: pip install python-dotenv psycopg2-binary requests")
    sys.exit(1)

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
DATABASE_URL = os.getenv("DATABASE_URL")

EXPECTED_TABLES = ["documents", "chunks", "query_logs", "eval_runs", "eval_results"]


def rest_check():
    import requests

    if not SUPABASE_URL or not SUPABASE_ANON_KEY:
        print("SUPABASE_URL / SUPABASE_ANON_KEY not set, skipping REST check.")
        return None

    print(f"REST check against {SUPABASE_URL} ...")
    headers = {
        "apikey": SUPABASE_ANON_KEY,
        "Authorization": f"Bearer {SUPABASE_ANON_KEY}",
    }
    ok = True
    for table in EXPECTED_TABLES:
        url = f"{SUPABASE_URL}/rest/v1/{table}?select=id&limit=1"
        try:
            resp = requests.get(url, headers=headers, timeout=10)
        except Exception as e:
            print(f"  {table}: request failed ({e})")
            ok = False
            continue
        if resp.status_code == 200:
            print(f"  {table}: reachable (HTTP 200)")
        elif resp.status_code == 404 or "does not exist" in resp.text.lower():
            print(f"  {table}: NOT FOUND -- run schema.sql in the Supabase SQL Editor")
            ok = False
        else:
            print(f"  {table}: unexpected response (HTTP {resp.status_code}): {resp.text[:200]}")
            ok = False
    return ok


def postgres_check():
    if not DATABASE_URL or "YOUR_DB_PASSWORD" in DATABASE_URL:
        print("DATABASE_URL not set (or still a placeholder), skipping direct Postgres check.")
        print("  Get it from Supabase: Project Settings > Database > Connection string (URI).")
        return None

    try:
        import psycopg2
    except ImportError:
        print("Missing dependency. Run: pip install psycopg2-binary")
        return False

    try:
        conn = psycopg2.connect(DATABASE_URL)
    except Exception as e:
        print(f"FAILED to connect: {e}")
        return False

    cur = conn.cursor()

    cur.execute("select extname from pg_extension where extname = 'vector';")
    has_vector = cur.fetchone() is not None
    print(f"pgvector extension enabled: {has_vector}")
    if not has_vector:
        print("  -> pgvector is NOT enabled. Go to Database > Extensions in Supabase and enable 'vector'.")

    cur.execute("""
        select table_name from information_schema.tables
        where table_schema = 'public' and table_name = any(%s);
    """, (EXPECTED_TABLES,))
    found_tables = {row[0] for row in cur.fetchall()}
    missing = set(EXPECTED_TABLES) - found_tables

    print(f"Tables found: {sorted(found_tables)}")
    if missing:
        print(f"  -> MISSING tables: {sorted(missing)}. Run schema.sql in the Supabase SQL Editor.")
    else:
        print("  -> All expected tables present.")

    cur.close()
    conn.close()
    return has_vector and not missing


def main():
    print("=== Supabase REST check ===")
    rest_result = rest_check()
    print()
    print("=== Direct Postgres check ===")
    pg_result = postgres_check()
    print()

    if rest_result is None and pg_result is None:
        print("Neither check could run -- fill in at least SUPABASE_URL + SUPABASE_ANON_KEY in .env.")
        sys.exit(1)
    if rest_result is False or pg_result is False:
        print("One or more checks failed -- see details above. Most likely fix: run schema.sql in the Supabase SQL Editor.")
        sys.exit(1)

    print("Connection verified. Ready to build the ingestion pipeline.")


if __name__ == "__main__":
    main()
