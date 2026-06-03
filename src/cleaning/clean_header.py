"""
Limpieza e ingesta: header (EuroLeague / EuroCup)
Problemas: coaches faltantes (~37%), columnas de tiempo extra casi vacías,
           date como string, score_extra_time con nulos legítimos.
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

print(f"🔄 Procesando Header para: {LIGA.upper()}")
df = pd.read_csv(f"data/{LIGA}_header.csv")
print(f"Original: {df.shape}")

# ── 1. Fecha y hora ─────────────────────────────────────────────────────────
df["date"] = pd.to_datetime(df["date"], errors="coerce")
df["season_year"] = df["date"].dt.year   # columna útil para filtrar

# ── 2. Coaches faltantes ────────────────────────────────────────────────────
# 37% de nulos — dato no registrado en temporadas antiguas. Se rellena con
# "Unknown" para no perder esas filas al hacer análisis de entrenadores.
df["coach_a"] = df["coach_a"].fillna("Unknown")
df["coach_b"] = df["coach_b"].fillna("Unknown")

# ── 3. Tiempos extra ────────────────────────────────────────────────────────
# Nulo = el partido no llegó a esa prórroga. Es correcto rellenar con 0.
extra_cols = [c for c in df.columns if "extra_time" in c]
df[extra_cols] = df[extra_cols].fillna(0).astype(int)

# Columna auxiliar: ¿el partido tuvo prórroga?
df["had_overtime"] = (df["score_extra_time_1_a"] + df["score_extra_time_1_b"]) > 0

# ── 4. Validación: quarters deben sumar el score final ──────────────────────
quarter_cols_a = ["score_quarter_1_a","score_quarter_2_a","score_quarter_3_a","score_quarter_4_a"]
quarter_cols_b = ["score_quarter_1_b","score_quarter_2_b","score_quarter_3_b","score_quarter_4_b"]

df["check_score_a"] = df[quarter_cols_a].sum(axis=1) + df[extra_cols[:4]].sum(axis=1)
df["check_score_b"] = df[quarter_cols_b].sum(axis=1) + df[extra_cols[4:8]].sum(axis=1)

inconsistentes = df[
    (df["check_score_a"] != df["score_a"]) |
    (df["check_score_b"] != df["score_b"])
]
print(f"Partidos con score inconsistente: {len(inconsistentes)}")

# Eliminar columnas auxiliares de verificación
df = df.drop(columns=["check_score_a", "check_score_b"])

# ── 5. Capacidad: estadio ────────────────────────────────────────────────────
# Reemplazar valores 0 o negativos por NaN (dato no disponible)
df["capacity"] = df["capacity"].where(df["capacity"] > 0, other=pd.NA)

# ── 6. Ingesta a PostgreSQL ──────────────────────────────────────────────────
df["competition"] = "EuroLeague" if LIGA == "euroleague" else "EuroCup"
df.to_sql("game_headers", con=engine, if_exists="append", index=False)
print(f"✅ Inyectadas {len(df)} filas en 'game_headers' ({LIGA})")
