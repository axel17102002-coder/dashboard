"""
Limpieza e ingesta: comparison (EuroLeague / EuroCup)
Optimizado con comando COPY para carga instantánea.
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

print(f"🔄 [BULK COPY] Comparison: {LIGA.upper()}")
df = pd.read_csv(f"data/{LIGA}_comparison.csv")

cols_no_negativas = ["fast_break_points_a", "fast_break_points_b", "turnover_points_a", "turnover_points_b", "second_chance_points_a", "second_chance_points_b", "points_starters_a", "points_bench_a", "points_starters_b", "points_bench_b"]
for col in cols_no_negativas:
    if col in df.columns:
        df[col] = df[col].clip(lower=0)

str_cols = [c for c in df.columns if c.startswith("str_") or c.startswith("minute_str_")]
df[str_cols] = df[str_cols].fillna(0)
prev_cols = [c for c in df.columns if "prev" in c]
df[prev_cols] = df[prev_cols].fillna(0)

if "max_lead_a" in df.columns and "max_lead_b" in df.columns:
    df["mayor_ventaja"] = df[["max_lead_a","max_lead_b"]].max(axis=1)
    df["equipo_con_mayor_ventaja"] = df.apply(lambda r: "a" if r["max_lead_a"] >= r["max_lead_b"] else "b", axis=1)

if all(c in df.columns for c in ["points_bench_a","points_starters_a"]):
    df["bench_contribution_a"] = (df["points_bench_a"] / (df["points_starters_a"] + df["points_bench_a"] + 1e-9)).round(3)
    df["bench_contribution_b"] = (df["points_bench_b"] / (df["points_starters_b"] + df["points_bench_b"] + 1e-9)).round(3)

df["competition"] = "EuroLeague" if LIGA == "euroleague" else "EuroCup"

pg_bulk_insert(df, "game_comparisons", engine)
print(f"✅ Inyectadas {len(df)} filas en 'game_comparisons' ({LIGA})")