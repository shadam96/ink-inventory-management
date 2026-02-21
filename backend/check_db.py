import sqlite3

conn = sqlite3.connect('test.db')
cursor = conn.cursor()

# Get all tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()

print(f"Tables in test.db ({len(tables)} total):")
for table in tables:
    print(f"\n  TABLE: {table[0]}")
    # Count rows
    try:
        cursor.execute(f"SELECT COUNT(*) FROM {table[0]}")
        count = cursor.fetchone()[0]
        print(f"    Rows: {count}")
    except Exception as e:
        print(f"    Error: {e}")

conn.close()
