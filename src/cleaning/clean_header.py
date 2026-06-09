"""
Limpieza e ingesta: header (EuroLeague / EuroCup)
Optimizado con comando COPY y blindado contra flotantes en campos enteros.
"""
import os
import csv
from io import StringIO
import pandas as pd
from sqlalchemy import create_engine

LIGA        = os.environ.get("LIGA", "euroleague")
DB_USER     = os.environ.get("POSTGRES_USER", "usuario_basket")
DB_PASSWORD = os.environ.get("POSTGRES_PASSWORD", "bskt26")
DB_DB       = os.environ.get("POSTGRES_DB", "basket_db")

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@db:5432/{DB_DB}"
engine = create_engine(DATABASE_URL)

def pg_bulk_insert(df, table_name, engine):
    buffer = StringIO()
    df.to_csv(buffer, index=False, header=False, na_rep='NULL', quoting=csv.QUOTE_MINIMAL)
    buffer.seek(0)
    raw_conn = engine.raw_connection()
    try:
        with raw_conn.cursor() as cursor:
            columnas = ', '.join([f'"{col}"' for col in df.columns])
            sql = f'COPY "{table_name}" ({columnas}) FROM STDIN WITH CSV NULL AS \'NULL\''
            cursor.copy_expert(sql, buffer)
        raw_conn.commit()
    finally:
        raw_conn.close()

print(f"🔄 [BULK COPY] Header: {LIGA.upper()}")
df = pd.read_csv(f"data/{LIGA}_header.csv")

df["date"] = pd.to_datetime(df["date"], errors="coerce")
df["season_year"] = df["date"].dt.year
df["coach_a"] = df["coach_a"].fillna("Unknown")
df["coach_b"] = df["coach_b"].fillna("Unknown")

extra_cols = [c for c in df.columns if "extra_time" in c]
df[extra_cols] = df[extra_cols].fillna(0).astype(int)
df["had_overtime"] = (df["score_extra_time_1_a"] + df["score_extra_time_1_b"]) > 0

# ── BLINDAJE DE ENTEROS EN CAPACIDAD ───────────────────────────────────────
df["capacity"] = pd.to_numeric(df["capacity"], errors='coerce').fillna(0).astype(int)

df["competition"] = "EuroLeague" if LIGA == "euroleague" else "EuroCup"

# Auto-alineación con las columnas físicas de Postgres
with engine.connect() as conn:
    cols_db = pd.read_sql(f"SELECT * FROM game_headers LIMIT 0", conn).columns
df = df[[col for col in df.columns if col in cols_db]]

pg_bulk_insert(df, "game_headers", engine)
print(f"✅ Inyectadas {len(df)} filas en 'game_headers' ({LIGA})")