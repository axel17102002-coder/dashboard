"""
Utilidades de ingesta compartidas por los scripts de limpieza.

Dos modos de carga, controlados por la variable de entorno MODO:

  - MODO=full    → COPY directo (rápido). Asume que la tabla viene vacía
                   (clean_master hace DROP + recrea el esquema antes).
  - MODO=upsert  → No borra nada. Inserta filas nuevas y actualiza las
                   existentes (INSERT ... ON CONFLICT DO UPDATE) usando la
                   clave primaria de cada tabla.

Para game_comparisons no hay clave natural en el CSV (su PK es un SERIAL),
así que en modo upsert se reemplaza por competición (DELETE + COPY).
"""
import os
import csv
from io import StringIO

# Clave de conflicto (PK natural) por tabla. None = sin clave natural.
CONFLICT_KEYS = {
    "game_headers":    "game_id",
    "game_box_scores": "game_player_id",
    "season_players":  "season_player_id",
    "season_teams":    "season_team_id",
    "game_points":     "game_point_id",
    "play_by_play":    "game_play_id",
    "game_comparisons": None,
}


def _copy_to(df, table_name, cursor):
    """COPY masivo de un DataFrame a una tabla/temp existente."""
    buffer = StringIO()
    df.to_csv(buffer, index=False, header=False, na_rep="NULL", quoting=csv.QUOTE_MINIMAL)
    buffer.seek(0)
    columnas = ", ".join([f'"{c}"' for c in df.columns])
    sql = f'COPY "{table_name}" ({columnas}) FROM STDIN WITH CSV NULL AS \'NULL\''
    cursor.copy_expert(sql, buffer)


def _full_insert(df, table_name, raw_conn):
    """COPY directo a la tabla (comportamiento clásico, tabla vacía)."""
    with raw_conn.cursor() as cur:
        _copy_to(df, table_name, cur)
    raw_conn.commit()


def _upsert_insert(df, table_name, conflict_key, raw_conn):
    """COPY a una tabla temporal y luego INSERT ... ON CONFLICT DO UPDATE."""
    cols = list(df.columns)
    columnas = ", ".join([f'"{c}"' for c in cols])
    # Columnas a actualizar = todas menos la clave de conflicto
    set_clause = ", ".join(
        [f'"{c}" = EXCLUDED."{c}"' for c in cols if c != conflict_key]
    )
    temp = f"_staging_{table_name}"
    with raw_conn.cursor() as cur:
        cur.execute(f'CREATE TEMP TABLE "{temp}" (LIKE "{table_name}" INCLUDING DEFAULTS) ON COMMIT DROP')
        _copy_to(df, temp, cur)
        if set_clause:
            cur.execute(f'''
                INSERT INTO "{table_name}" ({columnas})
                SELECT {columnas} FROM "{temp}"
                ON CONFLICT ("{conflict_key}") DO UPDATE SET {set_clause}
            ''')
        else:
            cur.execute(f'''
                INSERT INTO "{table_name}" ({columnas})
                SELECT {columnas} FROM "{temp}"
                ON CONFLICT ("{conflict_key}") DO NOTHING
            ''')
    raw_conn.commit()


def _replace_by_competition(df, table_name, raw_conn):
    """Sin clave natural: borra la competición actual y reinserta."""
    comp = df["competition"].iloc[0] if "competition" in df.columns and len(df) else None
    with raw_conn.cursor() as cur:
        if comp is not None:
            cur.execute(f'DELETE FROM "{table_name}" WHERE competition = %s', (comp,))
        _copy_to(df, table_name, cur)
    raw_conn.commit()


def pg_load(df, table_name, engine):
    """Carga el DataFrame según MODO (full | upsert)."""
    modo = os.environ.get("MODO", "full").lower()
    raw_conn = engine.raw_connection()
    try:
        if modo == "upsert":
            conflict_key = CONFLICT_KEYS.get(table_name)
            if conflict_key:
                _upsert_insert(df, table_name, conflict_key, raw_conn)
            else:
                _replace_by_competition(df, table_name, raw_conn)
        else:
            _full_insert(df, table_name, raw_conn)
    finally:
        raw_conn.close()
