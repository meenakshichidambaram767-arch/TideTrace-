"""
Ensure the target PostgreSQL database exists.
"""
import sys
import psycopg

def init_postgres_database(host="127.0.0.1", port=5433, user="postgres", dbname="tidetrace"):
    print(f"Connecting to PostgreSQL default database at {host}:{port}...")
    try:
        with psycopg.connect(f"host={host} port={port} user={user} dbname=postgres", autocommit=True) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (dbname,))
                if cur.fetchone():
                    print(f"Database '{dbname}' already exists.")
                else:
                    cur.execute(f'CREATE DATABASE "{dbname}";')
                    print(f"Database '{dbname}' successfully created!")
        return 0
    except Exception as e:
        print(f"Error initializing database: {e}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(init_postgres_database())
