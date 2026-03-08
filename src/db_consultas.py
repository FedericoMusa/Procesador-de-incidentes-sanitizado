import sqlite3
import os

def _conectar(db_path, dict_format=False):
    if not os.path.exists(db_path): return None
    conn = sqlite3.connect(db_path)
    if dict_format: conn.row_factory = sqlite3.Row
    return conn

def init_database(db_path):
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS incidentes (
            NUM_INC TEXT PRIMARY KEY, OPERADOR TEXT, FECHA TEXT, 
            LAT REAL, LON REAL, VOL_M3 REAL, MAGNITUD TEXT, 
            TIPO_INSTALACION TEXT, RECURSOS_AFECTADOS TEXT, DESC_ABREV TEXT)''')
        conn.execute('CREATE TABLE IF NOT EXISTS maestro_operadoras (ALIAS_PDF TEXT PRIMARY KEY, NOMBRE_OFICIAL TEXT NOT NULL)')

def get_stats(db_path):
    conn = _conectar(db_path)
    if not conn: return 0, 0, 0
    t = conn.execute("SELECT COUNT(*) FROM incidentes").fetchone()[0]
    o = conn.execute("SELECT COUNT(DISTINCT OPERADOR) FROM incidentes").fetchone()[0]
    e = conn.execute("SELECT COUNT(*) FROM incidentes WHERE LAT IS NULL").fetchone()[0]
    return t, o, e

def get_operadores(db_path):
    conn = _conectar(db_path)
    if not conn: return []
    return [r[0] for r in conn.execute("SELECT DISTINCT OPERADOR FROM incidentes ORDER BY OPERADOR").fetchall() if r[0]]

def get_incidentes_filtrados(db_path, search="", operador="Todos"):
    conn = _conectar(db_path)
    if not conn: return []
    q = "SELECT NUM_INC, OPERADOR, FECHA, MAGNITUD, TIPO_INSTALACION, VOL_M3, LAT, LON, RECURSOS_AFECTADOS FROM incidentes WHERE 1=1"
    params = []
    if search:
        q += " AND (NUM_INC LIKE ? OR OPERADOR LIKE ?)"
        params.extend([f'%{search}%', f'%{search}%'])
    if operador != "Todos":
        q += " AND OPERADOR = ?"
        params.append(operador)
    return conn.execute(q, params).fetchall()

def get_incidente_detalle(db_path, num_inc):
    conn = _conectar(db_path, True)
    return conn.execute("SELECT * FROM incidentes WHERE NUM_INC=?", (num_inc,)).fetchone() if conn else None

def get_todos_incidentes(db_path):
    conn = _conectar(db_path, True)
    return conn.execute("SELECT * FROM incidentes").fetchall() if conn else []

def get_operador_counts(db_path):
    conn = _conectar(db_path)
    return conn.execute("SELECT OPERADOR, COUNT(*) FROM incidentes GROUP BY OPERADOR").fetchall() if conn else []

def guardar_maestro_operadora(db_path, alias, oficial):
    conn = _conectar(db_path)
    with conn:
        conn.execute("INSERT OR REPLACE INTO maestro_operadoras VALUES (?, ?)", (alias.upper(), oficial.upper()))
    return True