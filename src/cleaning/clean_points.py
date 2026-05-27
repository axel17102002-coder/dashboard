"""
Limpieza: euroleague_points.csv
Problemas: 'zone' con 138k nulos (tiros libres), 
           'fastbreak/second_chance/points_off_turnover' con 263k nulos (dato no registrado).
"""
import pandas as pd

df = pd.read_csv("data/euroleague_points.csv")
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
if len(fuera_cancha) > 0:
    fuera_cancha.to_csv("data/clean/points_coords_anomalas.csv", index=False)

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

# ── 7. Resultado ────────────────────────────────────────────────────────────
print(f"\nNulos restantes:\n{df.isnull().sum()[df.isnull().sum() > 0]}")
print(f"Duplicados: {df.duplicated().sum()}")
df.to_csv("data/clean/euroleague_points_clean.csv", index=False)
print("✅ Guardado en data/clean/euroleague_points_clean.csv")
