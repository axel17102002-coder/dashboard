"""
Limpieza e ingesta: points (EuroLeague / EuroCup)
Problemas: 'zone' con 138k nulos (tiros libres),
           'fastbreak/second_chance/points_off_turnover' con 263k nulos (dato no registrado).
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

print(f"🔄 Procesando Points para: {LIGA.upper()}")
df = pd.read_csv(f"data/{LIGA}_points.csv")
print(f"Original: {df.shape}")

# ── 1. Zone: los tiros libres no tienen zona asignada ───────────────────────
# Acciones de tiro libre: FTM (made), FTA (attempted)
tiro_libre_mask = df["action_id"].isin(["FTM", "FTA"])

df.loc[tiro_libre_mask & df["zone"].isna(), "zone"] = "Free Throw"
df["zone"] = df["zone"].fillna("Unknown")   # restantes sin zona conocida

print(f"Zonas después de limpiar: {df['zone'].value_counts().to_dict()}")

# ── 2. Flags booleanos: nulos = dato no registrado en temporadas antiguas ───
# Rellenar con 0 (asumir que no aplica si no hay dato)
bool_cols = ["fastbreak", "second_chance", "points_off_turnover"]
df[bool_cols] = df[bool_cols].fillna(0).astype(int)

# ── 3. Validación de coordenadas ────────────────────────────────────────────
# Cancha estándar EuroLeague: X ∈ [-750, 750], Y ∈ [-200, 900] (aprox.)
fuera_cancha = df[
    (df["coord_x"].abs() > 800) |
    (df["coord_y"] < -250) |
    (df["coord_y"] > 1000)
]
print(f"Tiros con coordenadas fuera de rango: {len(fuera_cancha)}")

# ── 4. Validación: puntos solo pueden ser 1, 2 o 3 ─────────────────────────
invalidos = df[~df["points"].isin([1, 2, 3])]
print(f"Registros con puntos inválidos: {len(invalidos)}")

# ── 5. Columna auxiliar: tipo de tiro ───────────────────────────────────────
def tipo_tiro(action_id):
    if action_id in ["FTM", "FTA"]:
        return "free_throw"
    elif action_id in ["2FGM", "2FGA"]:
        return "two_point"
    elif action_id in ["3FGM", "3FGA"]:
        return "three_point"
    else:
        return "other"

df["shot_type"] = df["action_id"].apply(tipo_tiro)

# ── 6. Columna auxiliar: solo tiros que entraron ─────────────────────────────
df["made"] = df["action_id"].str.endswith("M").astype(int)

# ── 7. Ingesta a PostgreSQL ──────────────────────────────────────────────────
df["competition"] = "EuroLeague" if LIGA == "euroleague" else "EuroCup"
df.to_sql("game_points", con=engine, if_exists="append", index=False, chunksize=5000, method="multi")
print(f"✅ Inyectadas {len(df)} filas en 'game_points' ({LIGA})")
