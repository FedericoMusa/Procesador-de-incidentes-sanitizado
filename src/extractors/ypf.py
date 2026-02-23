"""
Extractor para informes de YPF S.A.
Formato: "Comunicado Incidente Nº XXXXXXXXX / Informe Preliminar Mendoza"
Sistema de coordenadas: provee DD directamente en el campo "Grados y decimales".
"""

import logging
import re
from src.extractors.base_extractor import BaseExtractor

logger = logging.getLogger(__name__)


class YPFExtractor(BaseExtractor):
    """
    Extrae datos de incidentes del formato estandarizado de YPF S.A.

    El PDF de YPF es el más completo y estructurado: incluye tres
    representaciones de coordenadas (GMS, GM y DD). Priorizamos DD
    porque viene explícita y no requiere conversión.
    """

    def extract(self, text: str) -> dict:
        data = {}

        # ── Identificación ──────────────────────────────────────────────
        data['OPERADOR'] = "YPF S.A."

        num_inc = self._find(r'Comunicado Incidente\s+N[°º]\s*([\d]+)', text)
        data['NUM_INC'] = f"YPF-{num_inc}" if num_inc else None

        # ── Área y ubicación ────────────────────────────────────────────
        data['AREA_CONCE'] = self._find(
            r'Área concesionada:\s*(.+)', text)
        data['AREA_OPERATIVA'] = self._find(
            r'Área operativa:\s*(.+)', text)
        data['YACIMIENTO'] = self._find(
            r'Yacimiento:\s*(.+)', text)
        data['CUENCA'] = self._find(
            r'Cuenca:\s*(.+)', text)

        # ── Instalación ─────────────────────────────────────────────────
        data['INSTALACION'] = self._find(
            r'Nombre de la instalación:\s*(.+)', text)
        data['TIPO_INST'] = self._find(
            r'Tipo de instalación:\s*(.+)', text)

        # ── Incidente ───────────────────────────────────────────────────
        data['SUBTIPO_INC'] = self._find(
            r'Subtipo de incidente:\s*(.+)', text)
        data['CAUSA'] = self._find(
            r'Subtipo de evento causante:\s*(.+)', text)
        data['MAGNITUD'] = self._find(
            r'Magnitud del Incidente:\s*(.+)', text)
        data['DESCRIPCION'] = self._find(
            r'Descripción:\s*(.+)', text)

        # ── Fecha ───────────────────────────────────────────────────────
        fecha_raw = self._find(r'Fecha de ocurrencia:\s*(\d{2}/\d{2}/\d{4})', text)
        data['FECHA_INC'] = self.normalize_date(fecha_raw)
        data['HORA_INC'] = self._find(r'Hora de ocurrencia:\s*(\d{2}:\d{2})', text)

        # ── Coordenadas (DD directa, campo "Grados y decimales") ────────
        # En el PDF real el label y el valor están en líneas separadas:
        # "Grados y decimales:\nLatitud (S): 37.348933° Longitud (W): 69.053400°"
        lat_dd = self._find_float(
            r'Grados y decimales:[\s\S]*?Latitud\s*\(S\):\s*([\d.]+)°', text)
        lon_dd = self._find_float(
            r'Latitud\s*\(S\):\s*[\d.]+°\s*Longitud\s*\(W\):\s*([\d.]+)°', text)

        # Aplicar signo negativo (S y W son negativos en WGS84)
        data['Y_COORD'] = -abs(lat_dd) if lat_dd is not None else None
        data['X_COORD'] = -abs(lon_dd) if lon_dd is not None else None
        data['SRID_ORIGEN'] = "WGS84-DD"

        if not self.validate_coordinates(data['Y_COORD'], data['X_COORD']):
            logger.warning(f"[YPF] Coordenadas inválidas en {data['NUM_INC']}")

        # ── Volúmenes ───────────────────────────────────────────────────
        data['VOL_D_m3'] = self._find_float(
            r'Volumen m3 derramado:\s*([\d.,]+)', text)
        data['VOL_R_m3'] = self._find_float(
            r'Volumen m3 recuperado:\s*([\d.,]+)', text)
        data['AGUA_PCT'] = self._find_float(
            r'%\s*Agua contenido:\s*([\d.,]+)', text)
        data['AREA_AFECT_m2'] = self._find_float(
            r'Área m2:\s*([\d.,]+)', text)
        data['PPM_HC'] = self._find(
            r'Concentración de hidrocarburo \(ppm\):\s*(.+)', text)

        # ── Recursos afectados ──────────────────────────────────────────
        data['RECURSOS'] = self._find(
            r'Recursos afectados:\s*(.+)', text)

        return data