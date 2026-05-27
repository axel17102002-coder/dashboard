import pandas as pd
import json
from pathlib import Path

ARCHIVOS = {
    "l_box_score":    ("data/euroleague_box_score.csv",   "euroleague"),
    "l_comparison":   ("data/euroleague_comparison.csv",  "euroleague"),
    "l_header":       ("data/euroleague_header.csv",      "euroleague"),
    "l_play_by_play": ("data/euroleague_play_by_play.csv","euroleague"),
    "l_players":      ("data/euroleague_players.csv",     "euroleague"),
    "l_points":       ("data/euroleague_points.csv",      "euroleague"),
    "l_teams":        ("data/euroleague_teams.csv",       "euroleague"),
    "l_comparasion":  ("data/euroleague_comparasion.csv",       "euroleague"),
    
    "c_box_score":    ("data/eurocup_box_score.csv",   "eurocup"),
    "c_comparison":   ("data/eurocup_comparison.csv",  "eurocup"),
    "c_header":       ("data/eurocup_header.csv",      "eurocup"),
    "c_play_by_play": ("data/eurocup_play_by_play.csv","eurocup"),
    "c_players":      ("data/eurocup_players.csv",     "eurocup"),
    "c_points":       ("data/eurocup_points.csv",      "eurocup"),
    "c_teams":        ("data/eurocup_teams.csv",       "eurocup"),
    "c_comparasion":  ("data/euroleague_comparasion.csv","eurocup")
}

def analizar_columna(serie):
    info = {
        "tipo":       str(serie.dtype),
        "nulos":      int(serie.isna().sum()),
        "pct_nulos":  round(serie.isna().mean() * 100, 1),
        "unicos":     int(serie.nunique()),
    }
    if pd.api.types.is_numeric_dtype(serie):
        desc = serie.describe()
        info.update({
            "min":    round(float(desc["min"]), 2),
            "max":    round(float(desc["max"]), 2),
            "media":  round(float(desc["mean"]), 2),
            "mediana":round(float(serie.median()), 2),
            "std":    round(float(desc["std"]), 2),
        })
    else:
        top = serie.value_counts().head(3)
        info["top_valores"] = {str(k): int(v) for k, v in top.items()}
    return info

def analizar_dataframe(ruta):
    df = pd.read_csv(ruta)
    resultado = {
        "filas":       int(df.shape[0]),
        "columnas":    int(df.shape[1]),
        "duplicados":  int(df.duplicated().sum()),
        "total_nulos": int(df.isna().sum().sum()),
        "pct_completo":round((1 - df.isna().mean().mean()) * 100, 1),
        "columnas_detalle": {}
    }
    for col in df.columns:
        resultado["columnas_detalle"][col] = analizar_columna(df[col])
    return resultado

# ── Generar reporte ──────────────────────────────────────────────────────────
print("Analizando archivos...")
reporte = {}

for nombre, (ruta, liga) in ARCHIVOS.items():
    path = Path(ruta)
    if not path.exists():
        print(f"  [SKIP] {ruta} — archivo no encontrado")
        continue
    print(f"  Procesando {nombre}...")
    reporte[nombre] = {
        "liga":  liga,
        "ruta":  ruta,
        **analizar_dataframe(ruta)
    }

# Guardar JSON para el visualizador
with open("reporte_datos.json", "w", encoding="utf-8") as f:
    json.dump(reporte, f, ensure_ascii=False, indent=2)

# ── Resumen en consola ───────────────────────────────────────────────────────
print("\n" + "="*60)
print("RESUMEN GENERAL")
print("="*60)

for nombre, datos in reporte.items():
    estado = "✅" if datos["pct_completo"] >= 95 else "⚠️" if datos["pct_completo"] >= 80 else "❌"
    print(f"\n{estado} {nombre.upper()}")
    print(f"   Filas: {datos['filas']:,}  |  Columnas: {datos['columnas']}")
    print(f"   Duplicados: {datos['duplicados']}  |  Completitud: {datos['pct_completo']}%")
    
    cols_con_nulos = {
        col: info for col, info in datos["columnas_detalle"].items()
        if info["nulos"] > 0
    }
    if cols_con_nulos:
        print("   Columnas con nulos:")
        for col, info in cols_con_nulos.items():
            print(f"     • {col}: {info['nulos']:,} nulos ({info['pct_nulos']}%)")

print("\n✅ Reporte guardado en reporte_datos.json")
print("   Abrí el archivo reporte_datos.html para la visualización interactiva.")
