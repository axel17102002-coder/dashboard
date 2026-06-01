"""
Limpieza: euroleague_header.csv
Problemas: coaches faltantes (~37%), columnas de tiempo extra casi vacías,
           date como string, score_extra_time con nulos legítimos.
"""
import pandas as pd
import os

liga = os.environ.get("LIGA", "euroleague")
df = pd.read_csv(f"data/{liga}_header.csv")
print(f"Original: {df.shape}")

# ── 1. Fecha y hora ──────────────────────────────────────────────────────────
df["date"] = pd.to_datetime(df["date"], errors="coerce")
df["season_year"] = df["date"].dt.year

# ── 2. Coaches faltantes — imputación lógica ─────────────────────────────────
# Estrategia en 3 pasos, de más a menos precisa:
#
#   Paso 1 — mismo equipo, misma temporada (caso más común: dato no registrado
#             en algunos partidos pero sí en otros de la misma campaña)
#
#   Paso 2 — mismo equipo, temporada anterior (cambio de entrenador entre años;
#             es una aproximación pero mejor que "Unknown")
#
#   Paso 3 — si no hay ningún dato histórico del equipo → "Unknown"

def imputar_coaches(df, col_coach, col_team):
    """
    Rellena nulos en col_coach buscando el entrenador más frecuente
    del mismo equipo en la misma temporada. Si no alcanza, usa
    la temporada más cercana disponible.
    """
    nulos_antes = df[col_coach].isna().sum()
    if nulos_antes == 0:
        print(f"  {col_coach}: sin nulos, nada que imputar")
        return df

    # Paso 1: moda por equipo + temporada
    moda_temporada = (
        df.dropna(subset=[col_coach])
        .groupby(["season_code", col_team])[col_coach]
        .agg(lambda x: x.mode().iloc[0] if len(x) > 0 else None)
        .rename("coach_imputado")
        .reset_index()
    )
    df = df.merge(moda_temporada, on=["season_code", col_team], how="left")
    mask_nulo = df[col_coach].isna()
    df.loc[mask_nulo, col_coach] = df.loc[mask_nulo, "coach_imputado"]
    df = df.drop(columns=["coach_imputado"])

    nulos_paso1 = df[col_coach].isna().sum()
    imputados_p1 = nulos_antes - nulos_paso1
    print(f"  {col_coach}: {imputados_p1} imputados por temporada+equipo")

    # Paso 2: moda global por equipo (usa cualquier temporada disponible)
    if nulos_paso1 > 0:
        moda_equipo = (
            df.dropna(subset=[col_coach])
            .groupby(col_team)[col_coach]
            .agg(lambda x: x.mode().iloc[0] if len(x) > 0 else None)
            .rename("coach_imputado")
            .reset_index()
        )
        df = df.merge(moda_equipo, on=col_team, how="left")
        mask_nulo = df[col_coach].isna()
        df.loc[mask_nulo, col_coach] = df.loc[mask_nulo, "coach_imputado"]
        df = df.drop(columns=["coach_imputado"])

        nulos_paso2 = df[col_coach].isna().sum()
        imputados_p2 = nulos_paso1 - nulos_paso2
        print(f"  {col_coach}: {imputados_p2} imputados por historial del equipo")

    # Paso 3: lo que quede sin datos históricos → "Unknown"
    nulos_finales = df[col_coach].isna().sum()
    if nulos_finales > 0:
        df[col_coach] = df[col_coach].fillna("Unknown")
        print(f"  {col_coach}: {nulos_finales} sin historial → 'Unknown'")

    return df

print("\nImputando coaches...")
df = imputar_coaches(df, "coach_a", "team_id_a")
df = imputar_coaches(df, "coach_b", "team_id_b")

# ── 3. Tiempos extra ─────────────────────────────────────────────────────────
extra_cols = [c for c in df.columns if "extra_time" in c]
df[extra_cols] = df[extra_cols].fillna(0).astype(int)
df["had_overtime"] = (df["score_extra_time_1_a"] + df["score_extra_time_1_b"]) > 0

# ── 4. Validación: quarters deben sumar el score final ───────────────────────
quarter_cols_a = ["score_quarter_1_a","score_quarter_2_a","score_quarter_3_a","score_quarter_4_a"]
quarter_cols_b = ["score_quarter_1_b","score_quarter_2_b","score_quarter_3_b","score_quarter_4_b"]

df["check_score_a"] = df[quarter_cols_a].sum(axis=1) + df[[c for c in extra_cols if c.endswith("_a")]].sum(axis=1)
df["check_score_b"] = df[quarter_cols_b].sum(axis=1) + df[[c for c in extra_cols if c.endswith("_b")]].sum(axis=1)

inconsistentes = df[
    (df["check_score_a"] != df["score_a"]) |
    (df["check_score_b"] != df["score_b"])
]
print(f"\nPartidos con score inconsistente: {len(inconsistentes)}")
if len(inconsistentes) > 0:
    inconsistentes[["game_id","score_a","check_score_a","score_b","check_score_b"]].to_csv(
        f"data/clean/{liga}_header_inconsistencias.csv", index=False
    )
    print(f"  → Guardados en data/clean/{liga}_header_inconsistencias.csv")

df = df.drop(columns=["check_score_a","check_score_b"])

# ── 5. Capacidad: estadio ─────────────────────────────────────────────────────
df["capacity"] = df["capacity"].where(df["capacity"] > 0, other=pd.NA)

# ── 6. Resultado ─────────────────────────────────────────────────────────────
nulos = df.isnull().sum()
nulos = nulos[nulos > 0]
print(f"\nNulos restantes:\n{nulos if len(nulos) else 'ninguno'}")
print(f"Duplicados: {df.duplicated().sum()}")
df.to_csv(f"data/clean/{liga}_header_clean.csv", index=False)
print(f"✅ Guardado en data/clean/{liga}_header_clean.csv")