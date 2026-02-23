"""
Extractor para informes de Petroquímica Comodoro Rivadavia S.A. (PCR).
Formato: "Informe Preliminar de Incidente Ambiental" — planilla tipo Pluspetrol.
Sistema de coordenadas: DMS con formato mixto (°, ´, ").
  Ej: "Lat. S= 34°57´51,5" S" — el apóstrofo invertido (´) es distinto al estándar (').

NUM_INC: PCR usa formato "MDZ-XX-YYYY-Descripcion" en el encabezado.
"""

import logging
import re
from src.extractors.base_extractor import BaseExtractor

logger = logging.getLogger(__name__)


class PCRExtractor(BaseExtractor):
    """
    Extrae datos de incidentes del formato de PCR.

    Muy similar al formato de Pluspetrol: tabla de tipo/magnitud con
    marcas ■, volúmenes en texto narrativo, y coordenadas DMS.
    Diferencia clave: las coordenadas usan el acento agudo (´) como
    separador de minutos, lo que requiere un patrón más permisivo.
    """

    def extract(self, text: str) -> dict:
        data = {}

        # ── Identificación ──────────────────────────────────────────────
        data['OPERADOR'] = "Petroquímica Comodoro Rivadavia S.A."

        # Formato: "Comunicado MDZ-21-2025- Batería 216"
        num_inc = self._find(
            r'Comunicado\s+(MDZ-[\w-]+)', text)
        data['NUM_INC'] = f"PCR-{num_inc}" if num_inc else None

        # ── Área y ubicación ────────────────────────────────────────────
        data['AREA_CONCE'] = self._find(
            r'Concesión[:\s]+(.+)', text)
        data['INSTALACION'] = self._find(
            r'Zona[:\s]+(.+)', text)
        data['UBICACION'] = self._find(
            r'Ubicación específica[:\s]+(.+)', text)

        # ── Incidente ───────────────────────────────────────────────────
        data['SUBTIPO_INC'] = self._extract_tipo_incidente(text)
        data['MAGNITUD'] = self._extract_magnitud(text)
        data['DESCRIPCION'] = self._find(
            r'Descripción del accidente.*?\n(.+?)(?=Superficie Afectada|Necesidad)',
            text, flags=re.DOTALL | re.IGNORECASE)

        # ── Fecha ───────────────────────────────────────────────────────
        # Formato: "Fecha: 18-02-2026"
        fecha_raw = self._find(
            r'Fecha[:\s]+(\d{2}[-/]\d{2}[-/]\d{4})', text)
        data['FECHA_INC'] = self.normalize_date(fecha_raw)

        # PCR a veces reporta dos horas: estimada y de detección
        data['HORA_INC'] = self._find(
            r'Hora de Detección[:\s]+(\d{1,2}:\d{2})', text)
        data['HORA_ESTIMADA'] = self._find(
            r'Hora Estimada[:\s]+(\d{1,2}:\d{2})', text)

        # ── Coordenadas DMS con acento agudo (´) ────────────────────────
        # Formato real: "Lat. S= 34°57´51,5" S" y "Long. O= 69°31´59,52" O"
        # Nota: el valor termina con espacio + letra hemisferio (S/O)
        lat_raw = self._find(
            r'Lat\.\s*S=\s*([\d°º´\'\u00b4".,]+)', text)
        lon_raw = self._find(
            r'Long\.\s*O=\s*([\d°º´\'\u00b4".,]+)', text)

        lat_dd = self._parse_pcr_dms(lat_raw, "Latitud") if lat_raw else None
        lon_dd = self._parse_pcr_dms(lon_raw, "Longitud") if lon_raw else None

        # Aplicar signo negativo (S y O/W son negativos)
        data['Y_COORD'] = -abs(lat_dd) if lat_dd is not None else None
        data['X_COORD'] = -abs(lon_dd) if lon_dd is not None else None
        data['SRID_ORIGEN'] = "WGS84-DMS→DD"

        if not self.validate_coordinates(data['Y_COORD'], data['X_COORD']):
            logger.warning(
                f"[PCR] Coordenadas inválidas en {data['NUM_INC']}"
            )

        # ── Volúmenes (en texto narrativo) ───────────────────────────────
        # "Volumen derramado neto de hidrocarburo: 1,1 m3"
        data['VOL_D_m3'] = self._find_float(
            r'Volumen derramado neto.*?[:\s]+([\d.,]+)\s*m3', text)
        data['VOL_R_m3'] = self._find_float(
            r'Volumen recuperado neto.*?[:\s]+([\d.,]+)\s*m3', text)
        # "Con un 40 % de agua"
        data['AGUA_PCT'] = self._find_float(
            r'(\d+)\s*%\s*de\s*agua', text)
        data['AREA_AFECT_m2'] = self._find_float(
            r'unos\s+([\d.,]+)\s*m2', text)
        data['PPM_HC'] = None  # PCR no suele reportar PPM en este formato

        # ── Responsable ─────────────────────────────────────────────────
        data['RESPONSABLE'] = self._find(
            r'Responsable del comunicado[:\s]+(.+)', text)

        # ── Medidas ─────────────────────────────────────────────────────
        data['MEDIDAS'] = self._find(
            r'Medidas adoptadas[:\s]+(.+?)(?=El tiempo estimado|$)',
            text, flags=re.DOTALL | re.IGNORECASE)

        # ── Magnitud: intentar desde tabla, sino inferir por volumen ────
        magnitud_tabla = self._extract_magnitud(text)
        if magnitud_tabla:
            data['MAGNITUD'] = magnitud_tabla
        else:
            data['MAGNITUD'] = self.inferir_magnitud(
                data.get('VOL_D_m3'), data.get('PPM_HC')
            )
            logger.info(
                f"[PCR] Magnitud inferida por volumen: {data['MAGNITUD']} "
                f"(vol={data.get('VOL_D_m3')} m3)"
            )

        return data

    # ------------------------------------------------------------------ #
    #  Helpers privados                                                   #
    # ------------------------------------------------------------------ #

    def _parse_pcr_dms(self, raw: str, label: str) -> float | None:
        """
        Parsea el formato DMS específico de PCR que usa acento agudo (´)
        como separador de minutos: "34°57´51,5""
        Delega al parse_dms_string de BaseExtractor normalizando el carácter.
        """
        if not raw:
            return None
        # Normalizar: reemplazar ´ (acento agudo U+00B4) por ' estándar
        normalized = raw.replace('\u00b4', "'").strip()
        result = self.parse_dms_string(normalized)
        if result is None:
            logger.warning(f"[PCR] No se pudo parsear {label}: '{raw}'")
        return result

    def _extract_tipo_incidente(self, text: str) -> str | None:
        """Detecta el tipo de incidente marcado en la tabla PCR."""
        tipos = [
            ("Derrames de agua de producción", r'Derrames de agua.*?[■✓X█]'),
            ("Derrames de hidrocarburos",       r'Derrames de hidrocarburo.*?[■✓X█]'),
            ("Incendio y/o explosiones",        r'Incendio.*?[■✓X█]'),
            ("Escapes de gases",                r'Escapes de gas.*?[■✓X█]'),
            ("Descontrol de pozos",             r'Descontrol.*?[■✓X█]'),
            ("Material radioactivo",            r'material radioactivo.*?[■✓X█]'),
        ]
        for nombre, pattern in tipos:
            if re.search(pattern, text, re.IGNORECASE):
                return nombre
        return None

    def _extract_magnitud(self, text: str) -> str | None:
        """Determina la magnitud según la columna marcada (BAJO/MEDIO/GRAVE)."""
        # Buscar marca ■ en proximidad de cada columna de magnitud
        # PCR usa columnas: BAJO | MEDIO | GRAVE (>10m3)
        if re.search(r'BAJO\s*\n[^\n]*[■█]', text, re.IGNORECASE):
            return "Bajo"
        if re.search(r'MEDIO\s*\n[^\n]*[■█]', text, re.IGNORECASE):
            return "Medio"
        if re.search(r'GRAVE\s*\n[^\n]*[■█]', text, re.IGNORECASE):
            return "Grave"
        return None