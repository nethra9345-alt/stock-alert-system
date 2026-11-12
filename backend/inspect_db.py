import os
import sys
import sqlite3

# Add root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app.core.config import settings

def inspect():
    db_file = settings.DATABASE_URL.replace("sqlite:///", "")
    print(f"Inspecting database: {db_file}")
    print(f"File exists: {os.path.exists(db_file)}")
    print(f"File size: {os.path.getsize(db_file)} bytes")

    conn = sqlite3.connect(db_file)
    cur = conn.cursor()

    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cur.fetchall()]
    print("\nExisting Tables:")
    for t in tables:
        cur.execute(f"PRAGMA table_info({t})")
        cols = cur.fetchall()
        cur.execute(f"SELECT COUNT(*) FROM {t}")
        count = cur.fetchone()[0]
        print(f"\n Table: {t} (row count: {count})")
        print("  Columns:")
        for col in cols:
            cid, name, col_type, notnull, dflt, pk = col
            pk_str = " [PRIMARY KEY]" if pk else ""
            print(f"    - {name} ({col_type}){pk_str}")

        cur.execute(f"PRAGMA foreign_key_list({t})")
        fks = cur.fetchall()
        if fks:
            print("  Foreign Keys:")
            for fk in fks:
                _, _, ref_table, from_col, to_col, _, _, _ = fk
                print(f"    - {from_col} -> {ref_table}({to_col})")

    conn.close()

if __name__ == "__main__":
    inspect()
