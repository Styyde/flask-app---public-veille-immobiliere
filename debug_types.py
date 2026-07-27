# debug_all_types.py
import sqlite3
from config import DB_PATH
from services.type_mapping import get_normalized_type

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

tables = [
    ('projets', 'type_bien'),
    ('annonces_sarouty', 'type_bien'),
    ('annonces_mubawab', 'type_bien')
]

for table, col in tables:
    cursor.execute(f"SELECT DISTINCT {col} FROM {table} WHERE {col} IS NOT NULL AND {col} != ''")
    types = cursor.fetchall()
    print(f"\n--- {table} ---")
    for (t,) in types:
        norm = get_normalized_type(t)
        print(f"  {t}  ->  {norm}")

conn.close()