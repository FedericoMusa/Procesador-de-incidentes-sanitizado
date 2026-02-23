"""
Procesador de Incidentes Ambientales — Oil & Gas Mendoza
Ejecutor principal: extrae PDFs, transforma coordenadas y carga en SQLite.
Exporta automáticamente a Excel al finalizar.
"""

import os
import logging
import sqlite3
import fitz       # PyMuPDF
import pandas as pd

from src.extractors.ypf import YPFExtractor
from src.extractors.pluspetrol import PluspetrolExtractor
from src.extractors.petsud import PetSudExtractor
from src.extractors.aconcagua import AconcaguaExtractor
from src.extractors.pcr import PCRExtractor
from src.transformation.coordinates import transform_to_cartesian

# ── Configuración de logging ────────────────────────────────────────────────
os.makedirs('logs', exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s — %(message)s',
    handlers=[
        logging.FileHandler('logs/processor.log', encoding='utf-8'),
        logging.StreamHandler(),
    ]
)
logger = logging.getLogger(__name__)

# ── Esquema de columnas ──────────────────────────────────────────────────────
# Clave interna (sin espacios, válida en SQLite) → nombre de columna en Excel
COLUMNAS_MAPA = {
    'NUM_INC':             'NUM_INC',
    'OPERADOR':            'OPERADOR',
    'AREA_CONCESION':      'AREA_CONCESION',
    'YACIMIENTO':          'YACIMIENTO',
    'MAGNITUD':            'MAGNITUD',
    'TIPO_INSTALACION':    'TIPO_INSTALACION',
    'SUBTIPO':             'SUBTIPO',
    'FECHA':               'FECHA',
    'DESC_ABREV':          'DESCRIPCION RESUMIDA',   # ← nombre visible en Excel
    'LAT':                 'LAT',
    'LON':                 'LON',
    'VOL_M3':              'VOL_M3',
    'AGUA_PCT':            'AGUA_PCT',
    'AREA_AFECT_m2':       'AREA_AFECT_m2',
    'RECURSOS_AFECTADOS':  'RECURSOS_AFECTADOS',
}

def normalizar(data: dict) -> dict:
    desc = data.get('DESCRIPCION') or data.get('DETALLE') or None
    desc_abrev = (desc[:120] + '...') if desc and len(desc) > 120 else desc

    return {
        'NUM_INC':           data.get('NUM_INC'),
        'OPERADOR':          data.get('OPERADOR'),
        'AREA_CONCESION':    data.get('AREA_CONCE'),
        'YACIMIENTO':        data.get('YACIMIENTO'),
        'MAGNITUD':          data.get('MAGNITUD'),
        'TIPO_INSTALACION':  data.get('TIPO_INST'),
        'SUBTIPO':           data.get('SUBTIPO_INC'),
        'FECHA':             data.get('FECHA_INC'),
        'DESC_ABREV':        desc_abrev,          # clave interna sin espacio
        'LAT':               data.get('Y_COORD'),
        'LON':               data.get('X_COORD'),
        'VOL_M3':            data.get('VOL_D_m3'),
        'AGUA_PCT':          data.get('AGUA_PCT'),
        'AREA_AFECT_m2':     data.get('AREA_AFECT_m2'),
        'RECURSOS_AFECTADOS': data.get('RECURSOS'),
    }

EXTRACTOR_REGISTRY: list[tuple[str, type]] = [
    ("YPF S.A.",                YPFExtractor),
    ("PLUSPETROL",              PluspetrolExtractor),
    ("PETROLEOS SUDAMERICANOS",  PetSudExtractor),
    ("PETRÓLEOS SUDAMERICANOS",  PetSudExtractor),
    ("ACONCAGUA ENERGIA",       AconcaguaExtractor),
    ("PCR",                     PCRExtractor),
    ("COMODORO RIVADAVIA",      PCRExtractor),
]

def identify_extractor(text: str):
    import unicodedata
    def normalizar_texto(s):
        return ''.join(
            c for c in unicodedata.normalize('NFD', s.upper())
            if unicodedata.category(c) != 'Mn'
        )
    text_norm = normalizar_texto(text)
    for keyword, extractor_cls in EXTRACTOR_REGISTRY:
        if normalizar_texto(keyword) in text_norm:
            return extractor_cls()
    return None

def init_database(db_path: str) -> None:
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS incidentes (
                NUM_INC            TEXT PRIMARY KEY,
                OPERADOR           TEXT,
                AREA_CONCESION     TEXT,
                YACIMIENTO         TEXT,
                MAGNITUD           TEXT,
                TIPO_INSTALACION   TEXT,
                SUBTIPO            TEXT,
                FECHA              TEXT,
                DESC_ABREV         TEXT,
                LAT                REAL,
                LON                REAL,
                VOL_M3             REAL,
                AGUA_PCT           REAL,
                AREA_AFECT_m2      REAL,
                RECURSOS_AFECTADOS TEXT
            )
        ''')
        conn.commit()
    logger.info(f"Base de datos lista: {db_path}")

# En src/main.py

# En src/main.py

def process_pdf(path: str) -> dict | None:
    filename = os.path.basename(path)
    text = ""  # Inicializamos para evitar el NameError
    
    try:
        with fitz.open(path) as doc:
            # Extraemos el texto de todas las páginas
            text = chr(12).join(page.get_text() for page in doc)
            
        if not text.strip():
            logger.error(f"[PARSING_ERROR] {filename}: El PDF parece estar vacío o ser una imagen sin OCR.")
            return None

    except Exception as e:
        logger.error(f"[IO_ERROR] {filename}: No se pudo abrir el archivo. Detalle: {e}")
        return None

    # Ahora 'text' ya existe y tiene contenido para identificar al extractor
    extractor = identify_extractor(text)
    if not extractor:
        logger.error(f"[PARSING_ERROR] {filename}: No se reconoce el formato de la operadora.")
        return None

    logger.info(f"[{filename}] Extractor identificado: {type(extractor).__name__}")

    try:
        raw = extractor.extract(text)
        
        # Integración del validador de integridad técnica
        if not extractor.validate_data(raw):
            logger.error(f"[VALIDATION_ERROR] {filename}: Datos inconsistentes o fuera de rango (Mendoza).")
            return None

    except Exception as e:
        logger.error(f"[PARSING_ERROR] {filename}: Falló la extracción de campos: {e}")
        return None

    # ... resto del código (transformación UTM y normalización)
    return normalizar(raw)

def insert_incident(conn: sqlite3.Connection, data: dict) -> bool:
    try:
        columns = ', '.join(data.keys())
        placeholders = ':' + ', :'.join(data.keys())
        cursor = conn.execute(
            f"INSERT OR IGNORE INTO incidentes ({columns}) VALUES ({placeholders})",
            data
        )
        if cursor.rowcount == 0:
            logger.info(f"Duplicado ignorado: {data.get('NUM_INC')}")
            return False
        return True
    except sqlite3.IntegrityError as e:
        logger.error(f"Error de integridad para {data.get('NUM_INC')}: {e}")
        return False
    except sqlite3.OperationalError as e:
        logger.error(f"Error de base de datos para {data.get('NUM_INC')}: {e}")
        return False

def exportar_excel(db_path: str) -> None:
    xlsx_path = os.path.join('data', 'incidentes.xlsx')
    csv_path  = os.path.join('data', 'incidentes_qgis.csv')
    try:
        with sqlite3.connect(db_path) as conn:
            df = pd.read_sql("SELECT * FROM incidentes ORDER BY FECHA", conn)

        # Renombrar columnas internas a nombres legibles para el usuario
        df.rename(columns=COLUMNAS_MAPA, inplace=True)

        # ── Excel ────────────────────────────────────────────────────────
        with pd.ExcelWriter(xlsx_path, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Incidentes')
            ws = writer.sheets['Incidentes']
            for col in ws.columns:
                max_len = max(len(str(cell.value or '')) for cell in col)
                ws.column_dimensions[col[0].column_letter].width = min(max_len + 4, 60)
        logger.info(f"Excel exportado: {xlsx_path}")

        # ── CSV para QGIS ────────────────────────────────────────────────
        # decimal='.' fuerza punto decimal independientemente de la
        # configuración regional de Windows, lo que evita que QGIS
        # interprete las coordenadas como texto.
        # encoding='utf-8-sig' agrega BOM para que Excel lo abra bien
        # si se necesita revisar el archivo antes de cargar en QGIS.
        df.to_csv(csv_path, index=False, encoding='utf-8-sig', decimal='.')
        logger.info(f"CSV QGIS exportado: {csv_path}")

    except Exception as e:
        logger.error(f"Error exportando archivos: {e}")

def main():
    raw_dir = os.path.join('data', 'raw')
    db_path  = os.path.join('data', 'database', 'incidentes.db')

    if not os.path.isdir(raw_dir):
        logger.error(f"Directorio no encontrado: {raw_dir}")
        return

    init_database(db_path)

    pdfs = sorted(f for f in os.listdir(raw_dir) if f.lower().endswith('.pdf'))
    if not pdfs:
        logger.warning(f"No se encontraron PDFs en {raw_dir}")
        return

    logger.info(f"Iniciando proceso. PDFs encontrados: {len(pdfs)}")
    insertados = omitidos = errores = 0

    with sqlite3.connect(db_path) as conn:
        for filename in pdfs:
            logger.info(f"Procesando: {filename}")
            data = process_pdf(os.path.join(raw_dir, filename))
            if data is None:
                omitidos += 1
                continue
            if insert_incident(conn, data):
                insertados += 1
            else:
                errores += 1
        conn.commit()

    logger.info(
        f"Proceso finalizado — "
        f"Insertados: {insertados} | Omitidos: {omitidos} | Errores: {errores}"
    )
    exportar_excel(db_path)

if __name__ == "__main__":
    main()