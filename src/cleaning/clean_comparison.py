"""
Limpieza e ingesta: comparison (EuroLeague / EuroCup)
Dataset de estadísticas comparativas por partido (team_a vs team_b).
Sin nulos reportados, foco en tipos y columnas auxiliares.
"""
import os
import pandas as pd
from sqlalchemy import create_engine

LIGA        = os.environ.get("LIGA", "euroleague")
DB_USER     = os.environ.get("POSTGRES_USER", "usuario_basket")
DB_PASSWORD = os.environ.get("POSTGRES_PASSWORD", "bskt26")
DB_DB       = os.environ.get("POSTGRES_DB", "basket_db")

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@db:5432/{DB_DB}"
engine = create_engine(DATABASE_URL)

print(f"🔄 Procesando Comparison para: {LIGA.upper()}")
df = pd.read_csv(f"data/{LIGA}_comparison.csv")
print(f"Original: {df.shape}")

# ── 1. Valores negativos en columnas que deben ser >= 0 ─────────────────────
cols_no_negativas = [
    "fast_break_points_a", "fast_break_points_b",
    "turnover_points_a",   "turnover_points_b",
    "second_chance_points_a", "second_chance_points_b",
    "points_starters_a", "points_bench_a",
    "points_starters_b", "points_bench_b",
]
for col in cols_no_negativas:
    if col in df.columns:
        negativos = (df[col] < 0).sum()
        if negativos > 0:
            print(f"  ⚠️  {col}: {negativos} valores negativos → se reemplazan por 0")
            df[col] = df[col].clip(lower=0)

# ── 2. Columnas de racha (str = streak): rellenar si están vacías ────────────
str_cols = [c for c in df.columns if c.startswith("str_") or c.startswith("minute_str_")]
df[str_cols] = df[str_cols].fillna(0)

prev_cols = [c for c in df.columns if "prev" in c]
df[prev_cols] = df[prev_cols].fillna(0)

# ── 3. Columnas auxiliares: ventaja y margen del partido ─────────────────────
if "max_lead_a" in df.columns and "max_lead_b" in df.columns:
    df["mayor_ventaja"] = df[["max_lead_a","max_lead_b"]].max(axis=1)
    df["equipo_con_mayor_ventaja"] = df.apply(
        lambda r: "a" if r["max_lead_a"] >= r["max_lead_b"] else "b", axis=1
    )

# ── 4. Columna auxiliar: dominancia ofensiva del banco ──────────────────────
if all(c in df.columns for c in ["points_bench_a","points_starters_a"]):
    df["bench_contribution_a"] = (
        df["points_bench_a"] /
        (df["points_starters_a"] + df["points_bench_a"] + 1e-9)
    ).round(3)
    df["bench_contribution_b"] = (
        df["points_bench_b"] /
        (df["points_starters_b"] + df["points_bench_b"] + 1e-9)
    ).round(3)

# ── 5. Ingesta a PostgreSQL ──────────────────────────────────────────────────
df["competition"] = "EuroLeague" if LIGA == "euroleague" else "EuroCup"
df.to_sql("game_comparisons", con=engine, if_exists="append", index=False)
print(f"✅ Inyectadas {len(df)} filas en 'game_comparisons' ({LIGA})")
