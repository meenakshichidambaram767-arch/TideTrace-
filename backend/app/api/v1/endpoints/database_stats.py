from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from sqlalchemy import text

from backend.app.db.session import get_db

router = APIRouter(prefix="/database", tags=["Database Schema"])


@router.get("/stats", status_code=status.HTTP_200_OK)
def get_database_stats(db: Session = Depends(get_db)):
    """
    Returns relational schema statistics, table sizes, row counts,
    and PostgreSQL constraints for academic and evaluation review.
    """
    db_size = db.execute(text("SELECT pg_size_pretty(pg_database_size(current_database()));")).scalar()
    pg_version = db.execute(text("SELECT version();")).scalar()

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
    tables = [
        {
            "table_name": row[0],
            "row_count": row[1],
            "table_size": row[2],
            "index_size": row[3],
        }
        for row in db.execute(text(table_stats_query)).fetchall()
    ]

    constraint_query = """
        SELECT
            conrelid::regclass::text AS table_name,
            conname AS constraint_name,
            contype AS type,
            pg_get_constraintdef(c.oid) AS definition
        FROM pg_constraint c
        JOIN pg_namespace n ON n.oid = c.connamespace
        WHERE n.nspname = 'public'
        ORDER BY conrelid::regclass::text, contype;
    """
    constraints = [
        {
            "table_name": row[0],
            "constraint_name": row[1],
            "type": "CHECK" if row[2] == 'c' else "FOREIGN KEY" if row[2] == 'f' else "UNIQUE" if row[2] == 'u' else "PRIMARY KEY",
            "definition": row[3],
        }
        for row in db.execute(text(constraint_query)).fetchall()
        if row[2] in ('c', 'f')
    ]

    index_query = """
        SELECT
            tablename,
            indexname,
            indexdef
        FROM pg_indexes
        WHERE schemaname = 'public'
        ORDER BY tablename, indexname;
    """
    indexes = [
        {
            "table_name": row[0],
            "index_name": row[1],
            "definition": row[2],
        }
        for row in db.execute(text(index_query)).fetchall()
    ]

    return {
        "database_name": "tidetrace",
        "database_size": db_size,
        "engine": pg_version.split(",")[0],
        "connection_info": {
            "host": "127.0.0.1",
            "port": 5433,
            "database": "tidetrace",
            "user": "postgres",
        },
        "tables": tables,
        "constraints": constraints,
        "indexes": indexes,
    }
