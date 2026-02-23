"""
Base class para todos los extractores de incidentes ambientales.
Define la interfaz común y utilidades compartidas (regex seguro,
normalización de fechas, conversión de coordenadas DMS→DD).
"""
import re
import logging
from abc import ABC, abstractmethod
from datetime import datetime

logger = logging.getLogger(__name__)

# Rango geográfico válido para Mendoza (WGS84 grados decimales)
LAT_MIN, LAT_MAX = -39.0, -32.0 
LON_MIN, LON_MAX = -70.0, -67.0

class BaseExtractor(ABC):
    @abstractmethod
    def extract(self, text: str) -> dict:
        raise NotImplementedError

    def _find(self, pattern: str, text: str, group: int = 1, flags: int = re.IGNORECASE) -> str | None:
        match = re.search(pattern, text, flags)
        if match:
            try: return match.group(group).strip()
            except IndexError: return match.group(0).strip()
        return None

    def _find_float(self, pattern: str, text: str, group: int = 1) -> float | None:
        raw = self._find(pattern, text, group)
        if raw is None: return None
        try: return float(raw.replace(',', '.'))
        except ValueError: return None

    def normalize_date(self, raw: str | None) -> str | None:
        if not raw: return None
        for fmt in ["%d/%m/%Y", "%d/%m/%y", "%d-%m-%Y", "%d-%m-%y", "%Y-%m-%d"]:
            try: return datetime.strptime(raw.strip(), fmt).strftime("%d-%m-%Y")
            except ValueError: continue
        return None

    def dms_to_dd(self, degrees: float, minutes: float, seconds: float = 0.0, hemisphere: str = "S") -> float:
        dd = degrees + minutes / 60.0 + seconds / 3600.0
        if hemisphere.upper() in ("S", "W"): dd = -dd
        return round(dd, 6)

    def parse_dms_string(self, raw: str) -> float | None:
        if not raw: return None
        normalized = re.sub(r'\s+', ' ', raw.strip())
        m = re.match(r"(\d+)\s*°\s*(\d+)\s*'\s*([\d.]+)", normalized)
        if m: return self.dms_to_dd(float(m.group(1)), float(m.group(2)), float(m.group(3)))
        return None

    def validate_coordinates(self, lat: float | None, lon: float | None) -> bool:
        """Verifica la ubicación dentro de Mendoza."""
        if lat is None or lon is None: return False
        return LAT_MIN <= lat <= LAT_MAX and LON_MIN <= lon <= LON_MAX

    def validate_data(self, data: dict) -> bool:
        """Valida integridad técnica antes de la carga."""
        lat, lon = data.get('Y_COORD'), data.get('X_COORD')
        if not self.validate_coordinates(lat, lon):
            logger.error(f"[VALIDATION_ERROR] {data.get('NUM_INC')}: Fuera de rango (Lat:{loat}, Lon:{lon})")
            return False

        vol_d = data.get('VOL_D_m3') or 0.0
        vol_r = data.get('VOL_R_m3') or 0.0
        if vol_r > vol_d:
            logger.warning(f"[VALIDATION_ERROR] {data.get('NUM_INC')}: Recuperado > Derramado")
        
        return True
    
    # ------------------------------------------------------------------ #
    #  Helpers de regex (seguros: nunca lanzan AttributeError)            #
    # ------------------------------------------------------------------ #

    def _find(self, pattern: str, text: str, group: int = 1,
              flags: int = re.IGNORECASE) -> str | None:
        """Busca un patrón y retorna el grupo indicado, o None si no matchea."""
        match = re.search(pattern, text, flags)
        if match:
            try:
                return match.group(group).strip()
            except IndexError:
                return match.group(0).strip()
        return None

    def _find_float(self, pattern: str, text: str, group: int = 1,
                    flags: int = re.IGNORECASE) -> float | None:
        """Busca un patrón numérico y retorna float, o None si no matchea."""
        raw = self._find(pattern, text, group, flags)
        if raw is None:
            return None
        try:
            return float(raw.replace(',', '.'))
        except ValueError:
            logger.warning(f"No se pudo convertir a float: '{raw}'")
            return None

    # ------------------------------------------------------------------ #
    #  Normalización de fechas                                            #
    # ------------------------------------------------------------------ #

    DATE_FORMATS = [
        "%d/%m/%Y",   # 10/10/2025
        "%d/%m/%y",   # 10/10/25
        "%d-%m-%Y",   # 10-10-2025
        "%d-%m-%y",   # 10-10-25
        "%Y-%m-%d",   # 2025-10-10
    ]

    def normalize_date(self, raw: str | None) -> str | None:
        """
        Convierte cualquier formato de fecha soportado a dd-mm-yyyy.
        Retorna None si el valor es None o no puede parsearse.
        """
        if raw is None:
            return None
        raw = raw.strip()
        for fmt in self.DATE_FORMATS:
            try:
                return datetime.strptime(raw, fmt).strftime("%d-%m-%Y")
            except ValueError:
                continue
        logger.warning(f"Formato de fecha no reconocido: '{raw}'")
        return None

    # ------------------------------------------------------------------ #
    #  Conversión de coordenadas                                          #
    # ------------------------------------------------------------------ #

    def dms_to_dd(self, degrees: float, minutes: float,
                  seconds: float = 0.0, hemisphere: str = "S") -> float:
        """
        Convierte Grados° Minutos' Segundos'' a grados decimales.
        Aplica signo negativo automáticamente para S y W.
        """
        dd = degrees + minutes / 60.0 + seconds / 3600.0
        if hemisphere.upper() in ("S", "W"):
            dd = -dd
        return round(dd, 6)

    @staticmethod
    def _normalize_dms_symbols(text: str) -> str:
        """
        Normaliza todos los símbolos Unicode de DMS a sus equivalentes ASCII:
          - Cualquier variante de minutos (´ ′ ' ') → '
          - Cualquier variante de segundos (" " ″ '' ´´) → "
          - Coma decimal → punto

        Esto permite que los regex posteriores sean simples y mantenibles.
        Caracteres cubiertos observados en PDFs de PetSud:
          ´  U+00B4  ACUTE ACCENT         → minutos
          ′  U+2032  PRIME                → minutos
          '  U+2018  LEFT SINGLE QUOTE    → minutos
          '  U+2019  RIGHT SINGLE QUOTE   → minutos
          ″  U+2033  DOUBLE PRIME         → segundos
          "  U+201C  LEFT DOUBLE QUOTE    → segundos
          "  U+201D  RIGHT DOUBLE QUOTE   → segundos
          '' dos apóstrofos consecutivos  → segundos (caso 468)
        """
        # Normalizar símbolo de minutos
        text = re.sub(r"[´′\u00B4\u2018\u2019\u02BC]", "'", text)
        # Normalizar símbolo de segundos (comillas dobles y double prime)
        text = re.sub(r'[″\u201C\u201D]', '"', text)
        # Dos apóstrofos/primes/acentos consecutivos → "
        text = re.sub(r"'{2}|′{2}|´{2}", '"', text)
        # Coma decimal → punto (para float())
        text = re.sub(r'(\d),(\d)', r'\1.\2', text)
        return text

    def parse_dms_string(self, raw: str) -> float | None:
        """
        Parsea strings de coordenadas en distintos formatos DMS,
        tolerando saltos de línea, espacios y variantes Unicode de símbolos.

        Formatos soportados (antes de normalización):
          - '33°34'39,63"'          → compacto con coma decimal
          - '33° 35´15,04'''        → acento agudo + dos apóstrofos (PetSud Informe Final)
          - '33°\n34'\n39,63"'      → fragmentado en múltiples líneas
          - '37°20.936''            → grados y minutos decimales
          - '37 ° / 20 ' / 56.2'   → con separadores /
        """
        if raw is None:
            return None

        # 1. Normalizar saltos de línea y espacios múltiples
        normalized = re.sub(r'\s+', ' ', raw.strip())

        # 2. Normalizar todos los símbolos DMS a ASCII estándar
        normalized = self._normalize_dms_symbols(normalized)

        # 3. Grados°, minutos', segundos"
        m = re.match(
            r"(\d+)\s*°\s*(\d+)\s*'\s*([\d.]+)\s*\"?",
            normalized
        )
        if m:
            deg  = float(m.group(1))
            mins = float(m.group(2))
            secs = float(m.group(3))
            return self.dms_to_dd(deg, mins, secs)

        # 4. Solo grados y minutos decimales: 37°20.936'
        m = re.match(
            r"(\d+)\s*°\s*([\d.]+)\s*'",
            normalized
        )
        if m:
            deg  = float(m.group(1))
            mins = float(m.group(2))
            return self.dms_to_dd(deg, mins)

        # 5. Formato con separadores /: 37 ° / 20 ' / 56.2
        m = re.match(
            r"(\d+)\s*°\s*/?\s*(\d+\.?\d*)\s*'\s*/?\s*([\d.]+)",
            normalized
        )
        if m:
            deg  = float(m.group(1))
            mins = float(m.group(2))
            secs = float(m.group(3))
            return self.dms_to_dd(deg, mins, secs)

        logger.warning(f"No se pudo parsear coordenada DMS: '{raw}'")
        return None

    # ------------------------------------------------------------------ #
    #  Validación geográfica                                              #
    # ------------------------------------------------------------------ #

    def inferir_magnitud(self, vol_m3: float | None, ppm: float | None = None) -> str:
        """
        Infiere la magnitud del incidente a partir del volumen y PPM
        según la normativa Res. 24-04 / Dec. 437-93.

        Reglas (en orden de prioridad):
          - HC > 50 PPM y vol > 5 m3  → "Mayor"
          - HC < 50 PPM y vol > 10 m3 → "Mayor"
          - vol <= 5 m3 (con HC > 50)  → "Menor"
          - vol <= 10 m3 (con HC < 50) → "Menor"
          - Sin datos suficientes       → "No determinado"

        IMPORTANTE: este es un fallback cuando el PDF no informa magnitud.
        El valor real puede diferir si el incidente involucra cauces de agua
        u otros factores cualitativos que la normativa también considera.
        """
        if vol_m3 is None:
            return "No determinado"

        # PPM desconocida: usar umbral más conservador (HC > 50 asumido)
        if ppm is None:
            return "Mayor" if vol_m3 > 5 else "Menor"

        if ppm > 50:
            return "Mayor" if vol_m3 > 5 else "Menor"
        else:
            return "Mayor" if vol_m3 > 10 else "Menor"

   # En src/extractors/base_extractor.py

def validate_data(self, data: dict) -> bool:
    """Valida la integridad técnica de los datos extraídos."""
    # Validación de Coordenadas (Mendoza Bounding Box)
    lat, lon = data.get('Y_COORD'), data.get('X_COORD')
    if not self.validate_coordinates(lat, lon):
        logger.error(f"[VALIDATION_ERROR] {data.get('NUM_INC')}: Coordenadas fuera de rango (Lat:{lat}, Lon:{lon})")
        return False

    # Validación de Volúmenes (Lógica física)
    vol_d = data.get('VOL_D_m3') or 0.0
    vol_r = data.get('VOL_R_m3') or 0.0
    if vol_r > vol_d:
        logger.warning(f"[VALIDATION_ERROR] {data.get('NUM_INC')}: Vol. recuperado ({vol_r}) mayor al derramado ({vol_d})")
    
    return True
