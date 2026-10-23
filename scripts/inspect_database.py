import os
import sys
from sqlalchemy import text

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from backend.app.db.session import engine


def inspect_database():
    print("=" * 80)
    print("TIDETRACE — RELATIONAL DATABASE & PHYSICAL SCHEMA INSPECTOR")
    print("=" * 80)

    with engine.connect() as conn:
        # Version and database metadata
        db_name = conn.execute(text("SELECT current_database();")).scalar()
        db_user = conn.execute(text("SELECT current_user;")).scalar()
        pg_version = conn.execute(text("SELECT version();")).scalar()
        db_size = conn.execute(text("SELECT pg_size_pretty(pg_database_size(current_database()));")).scalar()

        print(f"Database Name: {db_name}")
        print(f"Current User:  {db_user}")
        print(f"Database Size: {db_size}")
        print(f"Engine:        {pg_version.split(',')[0]}")
        print("-" * 80)

        # 1. Tables & Row Counts
        print("\n[1] PHYSICAL TABLES & ROW COUNTS:")
        print(f"{'Table Name':<30} | {'Estimated Rows':<15} | {'Table Size':<12} | {'Index Size':<12}")
        print("-" * 75)

        table_stats_query = """
            SELECT
                s.relname AS table_name,
                s.n_live_tup AS row_count,
                pg_size_pretty(pg_relation_size(c.oid)) AS table_size,
                pg_size_pretty(pg_indexes_size(c.oid)) AS index_size
            FROM pg_stat_user_tables s
            JOIN pg_class c ON c.relname = s.relname
            JOIN pg_namespace n ON n.oid = c.relnamespace AND n.nspname = 'public'
            ORDER BY s.n_live_tup DESC;
        """
        tables = conn.execute(text(table_stats_query)).fetchall()
        for t in tables:
            print(f"{t[0]:<30} | {t[1]:<15,d} | {t[2]:<12} | {t[3]:<12}")

        # 2. Key Foreign Keys & Constraints
        print("\n[2] RELATIONAL INTEGRITY CONSTRAINTS (FOREIGN KEYS & CHECKS):")
        fk_query = """
            SELECT
                conrelid::regclass AS table_name,
                conname AS constraint_name,
                contype AS type,
                pg_get_constraintdef(c.oid) AS definition
            FROM pg_constraint c
            JOIN pg_namespace n ON n.oid = c.connamespace
            WHERE n.nspname = 'public'
            ORDER BY conrelid::regclass::text, contype;
        """
        constraints = conn.execute(text(fk_query)).fetchall()
        for c in constraints:
            ctype = "CHECK" if c[2] == 'c' else "FOREIGN KEY" if c[2] == 'f' else "UNIQUE" if c[2] == 'u' else "PRIMARY KEY"
            if ctype in ("CHECK", "FOREIGN KEY"):
                print(f"  [{ctype:<11}] {c[0]}.{c[1]}")
                print(f"               -> {c[3]}")

        # 3. Performance Indexes
        print("\n[3] PERFORMANCE INDEXES:")
        index_query = """
            SELECT
                tablename,
                indexname,
                indexdef
            FROM pg_indexes
            WHERE schemaname = 'public'
            ORDER BY tablename, indexname;
        """
        indexes = conn.execute(text(index_query)).fetchall()
        for idx in indexes:
            print(f"  * {idx[0]}.{idx[1]}")
            print(f"    Def: {idx[2]}")

    print("\n" + "=" * 80)
    print("CONNECTION STRING FOR EVALUATORS / PGADMIN / DBEAVER:")
    print("Host:     127.0.0.1")
    print("Port:     5433")
    print("Database: tidetrace")
    print("User:     postgres")
    print("Password: (none / trust auth)")
    print("=" * 80)


if __name__ == "__main__":
    inspect_database()
