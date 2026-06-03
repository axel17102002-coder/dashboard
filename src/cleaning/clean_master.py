"""
Pipeline master de limpieza — euroleague y eurocup
Ejecutar desde cualquier directorio:
    python src/cleaning/clean_master.py
    python src/cleaning/clean_master.py --skip-drop
"""
import os
import subprocess
import sys
import time
import argparse
from pathlib import Path
from sqlalchemy import create_engine, text

# ── Rutas base ───────────────────────────────────────────────────────────────
DIR_SCRIPTS  = Path(__file__).parent
DIR_PROYECTO = DIR_SCRIPTS.parent.parent
DIR_CLEAN    = DIR_PROYECTO / "data" / "clean"
DIR_CLEAN.mkdir(parents=True, exist_ok=True)

LIGAS    = ["euroleague", "eurocup"]
DATASETS = ["box_score", "header", "players", "teams", "points", "comparison", "play_by_play"]

# ── DROP de tablas para evitar duplicados en re-ejecuciones ─────────────────
DB_USER     = os.environ.get("POSTGRES_USER", "usuario_basket")
DB_PASSWORD = os.environ.get("POSTGRES_PASSWORD", "bskt26")
DB_DB       = os.environ.get("POSTGRES_DB", "basket_db")
DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@db:5432/{DB_DB}"

TABLAS = [
    "game_box_scores",
    "game_comparisons",
    "game_headers",
    "play_by_play",
    "season_players",
    "game_points",
    "season_teams",
    "audit_anomalias",
]

print("=" * 55)
print("  🏀 Pipeline de limpieza")
print(f"  Scripts en: {DIR_SCRIPTS}")
print(f"  Output en:  {DIR_CLEAN}")
print(f"  Total scripts: {len(LIGAS) * len(DATASETS)}")
print("=" * 55)

parser = argparse.ArgumentParser()
parser.add_argument("--skip-drop", action="store_true", help="Omitir el DROP de tablas")
args = parser.parse_args()

if args.skip_drop:
    print("\n⏩  --skip-drop activo: se omite el DROP de tablas\n")
else:
    print("\n🗑️  Limpiando tablas anteriores...")
    try:
        engine = create_engine(DATABASE_URL)
        with engine.begin() as conn:
            for tabla in TABLAS:
                conn.execute(text(f"DROP TABLE IF EXISTS {tabla}"))
                print(f"  DROP TABLE IF EXISTS {tabla}")
        print("  ✅ Tablas eliminadas\n")
    except Exception as e:
        print(f"  ❌ Error al limpiar tablas: {e}")
        sys.exit(1)

resultados = []
t_inicio = time.time()

for liga in LIGAS:
    print(f"\nLiga: {liga.upper()}")
    for dataset in DATASETS:
        script = DIR_SCRIPTS / f"clean_{dataset}.py"

        if not script.exists():
            print(f"  ⚠️  {liga} / {dataset} — script no encontrado: {script}")
            resultados.append((liga, dataset, False, "script no encontrado"))
            continue

        t0 = time.time()
        try:
            result = subprocess.run(
                [sys.executable, str(script)],
                capture_output=True,
                text=True,
                # Pasar la liga como variable de entorno para que el script sepa qué CSV usar
                env={**os.environ, "LIGA": liga},
            )
            elapsed = round(time.time() - t0, 1)

            if result.returncode == 0:
                print(f"  ✅ {liga} / {dataset} ({elapsed}s)")
                resultados.append((liga, dataset, True, ""))
            else:
                # Mostrar solo la última línea del error (más informativa)
                error_lines = result.stderr.strip().splitlines()
                error_msg   = error_lines[-1] if error_lines else "error desconocido"
                print(f"  ❌ {liga} / {dataset} ({elapsed}s)")
                print(f"      {error_msg}")
                resultados.append((liga, dataset, False, error_msg))

        except Exception as e:
            print(f"  ❌ {liga} / {dataset} — excepción: {e}")
            resultados.append((liga, dataset, False, str(e)))

# ── Resumen final ────────────────────────────────────────────────────────────
t_total  = round(time.time() - t_inicio, 1)
exitosos = [r for r in resultados if r[2]]
fallidos = [r for r in resultados if not r[2]]

print("\n" + "=" * 55)
print(f"  Resumen  ({t_total}s total)")
print(f"  ✅ Exitosos: {len(exitosos)}/{len(resultados)}")
if fallidos:
    print(f"  ❌ Fallidos: {len(fallidos)}/{len(resultados)}")
    for liga, ds, _, msg in fallidos:
        print(f"     • {liga} / {ds}: {msg}")
print(f"  Archivos en: {DIR_CLEAN}")
print("=" * 55)
