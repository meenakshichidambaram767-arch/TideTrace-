"""
Verify the database schema, constraints, and indexes.
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import inspect
from backend.app.db.session import engine


def verify():
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    print(f"Total Tables Verified: {len(tables)}")
    for t in sorted(tables):
        pk = inspector.get_pk_constraint(t)
        fks = inspector.get_foreign_keys(t)
        indexes = inspector.get_indexes(t)
        checks = inspector.get_check_constraints(t)
        uniques = inspector.get_unique_constraints(t)
        cols = inspector.get_columns(t)
        print(f"\n[TABLE: {t}] ({len(cols)} columns)")
        print(f"  Primary Key : {pk.get('constrained_columns')}")
        print(f"  Foreign Keys: {[f.get('constrained_columns') for f in fks]}")
        print(f"  Indexes     : {[i.get('name') for i in indexes]}")
        print(f"  Check Constr: {[c.get('name') for c in checks]}")
        print(f"  Unique Constr: {[u.get('name') for u in uniques]}")


if __name__ == "__main__":
    verify()
