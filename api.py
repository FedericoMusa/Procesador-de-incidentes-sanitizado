"""
Servidor Flask — API local para integración con N8N.
Expone endpoints para procesar PDFs y consultar la base de datos.
"""

from flask import Flask, jsonify, request
import sqlite3
import subprocess
import sys
import os

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH  = os.path.join(BASE_DIR, 'data', 'database', 'incidentes.db')
PYTHON   = sys.executable


@app.route('/procesar', methods=['POST'])
def procesar():
    """Corre el procesador principal sobre data/raw/"""
    try:
        result = subprocess.run(
            [PYTHON, '-m', 'src.main'],
            cwd=BASE_DIR,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            timeout=120
        )
        return jsonify({
            'ok': result.returncode == 0,
            'stdout': result.stdout,
            'stderr': result.stderr
        })
    except subprocess.TimeoutExpired:
        return jsonify({'ok': False, 'error': 'Timeout'}), 408
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@app.route('/incidentes', methods=['GET'])
def listar_incidentes():
    """Devuelve todos los incidentes de la base de datos."""
    if not os.path.exists(DB_PATH):
        return jsonify({'ok': False, 'error': 'Base de datos no encontrada'}), 404
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM incidentes ORDER BY FECHA DESC"
            ).fetchall()
        return jsonify({
            'ok': True,
            'total': len(rows),
            'incidentes': [dict(r) for r in rows]
        })
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@app.route('/incidente/<num_inc>', methods=['GET'])
def get_incidente(num_inc):
    """Devuelve un incidente específico por número."""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM incidentes WHERE NUM_INC = ?", (num_inc,)
            ).fetchone()
        if not row:
            return jsonify({'ok': False, 'error': 'No encontrado'}), 404
        return jsonify({'ok': True, 'incidente': dict(row)})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@app.route('/actualizar_coords', methods=['POST'])
def actualizar_coords():
    """
    Actualiza las coordenadas de un incidente.
    Body JSON: { "num_inc": "PETSUD-574", "lat": -33.19, "lon": -68.780833 }
    """
    data = request.get_json()
    num_inc = data.get('num_inc')
    lat     = data.get('lat')
    lon     = data.get('lon')

    if not all([num_inc, lat, lon]):
        return jsonify({'ok': False, 'error': 'Faltan campos'}), 400

    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                "UPDATE incidentes SET LAT=?, LON=? WHERE NUM_INC=?",
                (lat, lon, num_inc)
            )
            conn.commit()
        return jsonify({'ok': True, 'updated': num_inc})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@app.route('/errores', methods=['GET'])
def listar_errores():
    """Devuelve incidentes con campos críticos vacíos o coordenadas inválidas."""
    if not os.path.exists(DB_PATH):
        return jsonify({'ok': False, 'error': 'Base de datos no encontrada'}), 404

    LAT_MIN, LAT_MAX = -39.0, -32.0
    LON_MIN, LON_MAX = -70.0, -67.0
    CAMPOS = ['FECHA', 'MAGNITUD', 'TIPO_INSTALACION', 'LAT', 'LON', 'VOL_M3']

    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM incidentes").fetchall()

        errores = []
        for row in rows:
            row = dict(row)
            problemas = []
            for campo in CAMPOS:
                if row.get(campo) is None or str(row.get(campo, '')).strip() == '':
                    problemas.append(f'{campo} vacío')
            lat, lon = row.get('LAT'), row.get('LON')
            if lat and not (LAT_MIN <= lat <= LAT_MAX):
                problemas.append(f'LAT {lat} fuera de Mendoza')
            if lon and not (LON_MIN <= lon <= LON_MAX):
                problemas.append(f'LON {lon} fuera de Mendoza')
            if problemas:
                errores.append({
                    'num_inc':   row.get('NUM_INC'),
                    'operador':  row.get('OPERADOR'),
                    'problemas': problemas
                })

        return jsonify({'ok': True, 'total': len(errores), 'errores': errores})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@app.route('/status', methods=['GET'])
def status():
    """Health check — verifica que la API está viva."""
    total = 0
    if os.path.exists(DB_PATH):
        with sqlite3.connect(DB_PATH) as conn:
            total = conn.execute(
                "SELECT COUNT(*) FROM incidentes"
            ).fetchone()[0]
    return jsonify({'ok': True, 'registros': total})


if __name__ == '__main__':
    print("API corriendo en http://localhost:5000")
    app.run(host='0.0.0.0', port=5000, debug=False)