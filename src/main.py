"""
Industrial Incident Data Pipeline — Oil & Gas Mendoza
Main Orchestrator: Extracts data from PDFs, performs spatial transformations, 
and persists structured data into SQLite.
Automatically exports to Excel and GIS-ready CSV upon completion.
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

# ── Logging Configuration ──────────────────────────────────────────────────
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

# ── Column Mapping Schema ──────────────────────────────────────────────────
# Internal keys (SQLite safe) → Human-readable Excel column names
COLUMN_MAP = {
    'NUM_INC':             'INCIDENT_ID',
    'OPERADOR':            'OPERATOR',
    'AREA_CONCESION':      'CONCESSION_AREA',
    'YACIMIENTO':          'OIL_FIELD',
    'MAGNITUD':            'MAGNITUDE',
    'TIPO_INSTALACION':    'FACILITY_TYPE',
    'SUBTIPO':             'SUBTYPE',
    'FECHA':               'DATE',
    'DESC_ABREV':          'SUMMARY_DESCRIPTION',
    'LAT':                 'LATITUDE',
    'LON':                 'LONGITUDE',
    'VOL_M3':              'VOLUME_M3',
    'AGUA_PCT':            'WATER_PCT',
    'AREA_AFECT_m2':       'AFFECTED_AREA_M2',
    'RECURSOS_AFECTADOS':  'AFFECTED_RESOURCES',
}

def normalize_data(data: dict) -> dict:
    """Normalizes raw extracted data and truncates long descriptions."""
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
        'DESC_ABREV':        desc_abrev,
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
    """Identifies the appropriate operator extractor based on PDF content."""
    import unicodedata
    def normalize_text(s):
        return ''.join(
            c for c in unicodedata.normalize('NFD', s.upper())
            if unicodedata.category(c) != 'Mn'
        )
    text_norm = normalize_text(text)
    for keyword, extractor_cls in EXTRACTOR_REGISTRY:
        if normalize_text(keyword) in text_norm:
            return extractor_cls()
    return None

def init_database(db_path: str) -> None:
    """Initializes the local SQLite database with the required schema."""
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
    logger.info(f"Database initialized: {db_path}")

def process_pdf(path: str) -> dict | None:
    """Extracts text from PDF, identifies operator, and validates data integrity."""
    filename = os.path.basename(path)
    text = ""
    
    try:
        with fitz.open(path) as doc:
            # Extract text from all pages using Form Feed as separator
            text = chr(12).join(page.get_text() for page in doc)
            
        if not text.strip():
            logger.error(f"[PARSING_ERROR] {filename}: PDF is empty or missing OCR.")
            return None

    except Exception as e:
        logger.error(f"[IO_ERROR] {filename}: Could not open file. Detail: {e}")
        return None

    extractor = identify_extractor(text)
    if not extractor:
        logger.error(f"[PARSING_ERROR] {filename}: Unknown operator format.")
        return None

    logger.info(f"[{filename}] Extractor identified: {type(extractor).__name__}")

    try:
        raw = extractor.extract(text)
        
        # Data Integrity & Geospatial validation gate
        if not extractor.validate_data(raw):
            logger.error(f"[VALIDATION_ERROR] {filename}: Inconsistent data or out-of-bounds coordinates.")
            return None

    except Exception as e:
        logger.error(f"[PARSING_ERROR] {filename}: Field extraction failed: {e}")
        return None

    return normalize_data(raw)

def insert_incident(conn: sqlite3.Connection, data: dict) -> bool:
    """Inserts record into database, handling duplicates via 'INSERT OR IGNORE'."""
    try:
        columns = ', '.join(data.keys())
        placeholders = ':' + ', :'.join(data.keys())
        cursor = conn.execute(
            f"INSERT OR IGNORE INTO incidentes ({columns}) VALUES ({placeholders})",
            data
        )
        if cursor.rowcount == 0:
            logger.info(f"Duplicate ignored: {data.get('NUM_INC')}")
            return False
        return True
    except sqlite3.Error as e:
        logger.error(f"Database error for {data.get('NUM_INC')}: {e}")
        return False

def export_data(db_path: str) -> None:
    """Exports processed data to formatted Excel and GIS-optimized CSV."""
    xlsx_path = os.path.join('data', 'incidentes.xlsx')
    csv_path  = os.path.join('data', 'incidentes_qgis.csv')
    try:
        with sqlite3.connect(db_path) as conn:
            df = pd.read_sql("SELECT * FROM incidentes ORDER BY FECHA", conn)

        # Map internal keys to user-friendly column names
        df.rename(columns=COLUMN_MAP, inplace=True)

        # ── Excel Export ───────────────────────────────────────────────────
        with pd.ExcelWriter(xlsx_path, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Incidents')
            ws = writer.sheets['Incidents']
            # Auto-adjust column width
            for col in ws.columns:
                max_len = max(len(str(cell.value or '')) for cell in col)
                ws.column_dimensions[col[0].column_letter].width = min(max_len + 4, 60)
        logger.info(f"Excel exported: {xlsx_path}")

        # ── QGIS CSV Export ────────────────────────────────────────────────
        # Force '.' decimal separator to ensure GIS software compatibility
        df.to_csv(csv_path, index=False, encoding='utf-8-sig', decimal='.')
        logger.info(f"QGIS CSV exported: {csv_path}")

    except Exception as e:
        logger.error(f"Error during file export: {e}")

def main():
    raw_dir = os.path.join('data', 'raw')
    db_path  = os.path.join('data', 'database', 'incidentes.db')

    if not os.path.isdir(raw_dir):
        logger.error(f"Directory not found: {raw_dir}")
        return

    init_database(db_path)

    pdfs = sorted(f for f in os.listdir(raw_dir) if f.lower().endswith('.pdf'))
    if not pdfs:
        logger.warning(f"No PDFs found in {raw_dir}")
        return

    logger.info(f"Starting process. PDFs found: {len(pdfs)}")
    inserted = skipped = errors = 0

    with sqlite3.connect(db_path) as conn:
        for filename in pdfs:
            logger.info(f"Processing: {filename}")
            data = process_pdf(os.path.join(raw_dir, filename))
            if data is None:
                skipped += 1
                continue
            if insert_incident(conn, data):
                inserted += 1
            else:
                errors += 1
        conn.commit()

    logger.info(
        f"Process finished — "
        f"Inserted: {inserted} | Skipped: {skipped} | Errors: {errors}"
    )
    export_data(db_path)

if __name__ == "__main__":
    main()
