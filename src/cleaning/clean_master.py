"""
Pipeline master de limpieza — euroleague y eurocup
Automatizado: Elimina tablas, recrea el esquema desde schema.sql
e inserta datos de forma masiva ultra veloz mediante COPY.

Ejecutar desde cualquier directorio:
    docker compose exec web python src/cleaning/clean_master.py
    docker compose exec web python src/cleaning/clean_master.py --skip-drop
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
DATASETS = ["header", "box_score", "players", "teams", "points", "comparison", "play_by_play"]
# ── Credenciales de conexión a Base de Datos ─────────────────────────────────
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
print(f"  Output en:   {DIR_CLEAN}")
print(f"  Total scripts: {len(LIGAS) * len(DATASETS)}")
print("=" * 55)

parser = argparse.ArgumentParser()
parser.add_argument("--skip-drop", action="store_true", help="Omitir el DROP de tablas")
args = parser.parse_args()

engine = create_engine(DATABASE_URL)

if args.skip_drop:
    print("\n⏩  --skip-drop activo: se omite el DROP y la recreación del esquema\n")
else:
    # ── 1. DROP de tablas anteriores para limpiar a cero ─────────────────────
    print("\n🗑️  Limpiando tablas anteriores...")
    try:
        with engine.begin() as conn:
            for tabla in TABLAS:
                conn.execute(text(f"DROP TABLE IF EXISTS {tabla} CASCADE"))
                print(f"  DROP TABLE IF EXISTS {tabla}")
        print("  ✅ Tablas viejas eliminadas.")
    except Exception as e:
        print(f"  ❌ Error al limpiar tablas: {e}")
        sys.exit(1)

    # ── 2. Recreación del esquema automático desde schema.sql ────────────────
    print("🏗️  Recreando esquema limpio desde schema.sql...")
    try:
        # Intentamos leer la ruta del schema montado en Docker
        ruta_schema = Path("/docker-entrypoint-initdb.d/schema.sql")
        if not ruta_schema.exists():
            # Ruta de respaldo por si se llegara a ejecutar local fuera de Docker
            ruta_schema = DIR_PROYECTO / "schema.sql" 
        
        with open(ruta_schema, "r", encoding="utf-8") as f:
            sql_schema = f.read()
            
        with engine.begin() as conn:
            # Ejecutamos el archivo SQL entero para levantar las estructuras vacías
            conn.execute(text(sql_schema))
        print("  ✅ Estructura de tablas vacías recreada con éxito.\n")
    except Exception as e:
        print(f"  ❌ Error crítico al recrear el esquema SQL: {e}")
        sys.exit(1)

# ── 3. Ejecución iterativa de los scripts de limpieza ─────────────────────────
resultados = []
t_inicio = time.time()

for liga in LIGAS:
    print(f"\nLiga: {liga.upper()}")
    for dataset in DATASETS:
        # El script maestro asume que tus archivos se llaman clean_teams.py, etc.
        # Si tenías 'teams.py', recordá renombrarlo a 'clean_teams.py'
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
                # Le inyectamos la variable LIGA en el entorno de ejecución
                env={**os.environ, "LIGA": liga},
            )
            elapsed = round(time.time() - t0, 1)

            if result.returncode == 0:
                print(f"  ✅ {liga} / {dataset} ({elapsed}s)")
                resultados.append((liga, dataset, True, ""))
            else:
                # Si un script falla (ej. por error de COPY), extrae la última línea de error
                error_lines = result.stderr.strip().splitlines()
                error_msg   = error_lines[-1] if error_lines else "error desconocido"
                print(f"  ❌ {liga} / {dataset} ({elapsed}s)")
                print(f"      {error_msg}")
                resultados.append((liga, dataset, False, error_msg))

        except Exception as e:
            print(f"  ❌ {liga} / {dataset} — excepción: {e}")
            resultados.append((liga, dataset, False, str(e)))

# ── Resumen final en consola ──────────────────────────────────────────────────
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