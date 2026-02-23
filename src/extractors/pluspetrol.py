"""
Extractor para comunicados de Pluspetrol S.A.
Formato: "Planilla de Comunicación de Accidentes en la Actividad Petrolera"
Sistema de coordenadas: doble — Gauss-Krüger Faja 2 (metros) Y WGS84 DD.
  Priorizamos las coordenadas WGS84 DD que vienen explícitas en el PDF.
  Las coordenadas GK se guardan como referencia en campos separados.
"""

import logging
import re
from src.extractors.base_extractor import BaseExtractor

logger = logging.getLogger(__name__)


class PluspetrolExtractor(BaseExtractor):
    """
    Extrae datos de incidentes del formato de comunicado de Pluspetrol S.A.

    Este formato es más libre (no es una tabla rígida), por lo que los
    patrones regex son más permisivos. El campo DESCRIPCION contiene
    varios datos cuantitativos embebidos en el texto narrativo.
    """

    def extract(self, text: str) -> dict:
        data = {}

        # ── Identificación ──────────────────────────────────────────────
        data['OPERADOR'] = "Pluspetrol S.A."

        num_inc = self._find(r'COMUNICADO\s+N[°º]?[:\s]+(\S+)', text)
        data['NUM_INC'] = f"PP-{num_inc}" if num_inc else None

        data['CODIGO'] = self._find(r'CÓDIGO[:\s]+(\S+)', text)

        # ── Área y ubicación ────────────────────────────────────────────
        data['AREA_CONCE'] = self._find(r'CONCESION[:\s]+(\S+)', text)
        data['YACIMIENTO'] = self._find(r'YACIMIENTO[:\s]+(\S+)', text)
        data['INSTALACION'] = self._find(r'OTROS[:\s]+(.+)', text)
        data['UBICACION'] = self._find(
            r'UBICACIÓN ESPECÍFICA[:\s]+(.+)', text)

        # ── Incidente (en Pluspetrol, el tipo se infiere de la tabla de magnitudes)
        data['SUBTIPO_INC'] = self._extract_tipo_incidente(text)
        data['MAGNITUD'] = self._extract_magnitud(text)
        data['DESCRIPCION'] = self._find(
            r'DESCRIPCIÓN[:\s]*\n(.+?)(?:\n\n|\Z)', text, flags=re.DOTALL)

        # ── Fecha ───────────────────────────────────────────────────────
        fecha_raw = self._find(r'FECHA[:\s]+(\d{2}/\d{2}/\d{4})', text)
        data['FECHA_INC'] = self.normalize_date(fecha_raw)
        data['HORA_INC'] = self._find(r'HORA[:\s]+(\d{2}:\d{2})', text)

        # ── Coordenadas ─────────────────────────────────────────────────
        # Gauss-Krüger (metros) — se guardan como referencia
        gk_x = self._find_float(r'X[:\s]+([\d.,]+)\s+Y[:\s]', text)
        gk_y = self._find_float(r'Y[:\s]+([\d.,]+)\s+\(Gauss', text)
        data['GK_X_M'] = gk_x
        data['GK_Y_M'] = gk_y
        data['SRID_GK'] = "Gauss-Krüger Faja 2 Campo Inchauspe 69'"

        # WGS84 DD — formato: "Long.: -68.4049142 Lat.: -37.4246588"
        lon_dd = self._find_float(r'Long\.\s*:\s*(-?[\d.,]+)', text)
        lat_dd = self._find_float(r'Lat\.\s*:\s*(-?[\d.,]+)', text)

        # Las coordenadas ya vienen con signo negativo en el PDF
        data['Y_COORD'] = lat_dd
        data['X_COORD'] = lon_dd
        data['SRID_ORIGEN'] = "WGS84-DD"

        if not self.validate_coordinates(data['Y_COORD'], data['X_COORD']):
            logger.warning(
                f"[Pluspetrol] Coordenadas inválidas en {data['NUM_INC']}"
            )

        # ── Volúmenes (embebidos en texto narrativo de DESCRIPCIÓN) ─────
        # "Vol. derramado: 0,015 m3"
        data['VOL_D_m3'] = self._find_float(
            r'Vol\.?\s*derramado[:\s]+([\d.,]+)\s*m3', text)
        # "Volumen recuperado: 0 m3"
        data['VOL_R_m3'] = self._find_float(
            r'Volumen\s+recuperado[:\s]+([\d.,]+)\s*m3', text)
        # "97 % agua de producción"
        data['AGUA_PCT'] = self._find_float(
            r'\((\d+)\s*%\s*agua', text)
        # "Sup. Afectada: 0,5 m2"
        data['AREA_AFECT_m2'] = self._find_float(
            r'Sup\.?\s*Afectada[:\s]+([\d.,]+)\s*m2', text)

        # Pluspetrol no siempre informa PPM
        data['PPM_HC'] = None

        return data

    # ------------------------------------------------------------------ #
    #  Helpers privados                                                   #
    # ------------------------------------------------------------------ #

    def _extract_tipo_incidente(self, text: str) -> str | None:
        """
        En Pluspetrol, el tipo de incidente se infiere de las filas marcadas
        con ■ o X en la tabla de contingencias (BAJA / MEDIA / ALTA).
        Retorna el primer tipo marcado encontrado.
        """
        tipos = {
            "Derrame de agua de producción": r'Derrame de agua de producción.*?[■✓X]',
            "Derrame de hidrocarburos": r'Derrame de hidrocarburos.*?[■✓X]',
            "Incendio / explosión": r'Incendio.*?[■✓X]',
            "Escape de gases": r'Escape de gases.*?[■✓X]',
            "Descontrol de pozos": r'Descontrol.*?[■✓X]',
        }
        for nombre, pattern in tipos.items():
            if re.search(pattern, text, re.IGNORECASE):
                return nombre
        return None

    def _extract_magnitud(self, text: str) -> str | None:
        """
        Determina la magnitud según la columna marcada en la tabla.
        BAJA (col 1), MEDIA (col 2), ALTA (col 3).
        """
        # En el PDF, la marca ■ aparece bajo BAJA, MEDIA o ALTA
        # Buscamos el patrón: Derrame ... ■ y vemos en qué columna cae
        if re.search(r'BAJA\s*\n.*?[■✓]', text, re.DOTALL):
            return "Baja"
        if re.search(r'MEDIA\s*\n.*?[■✓]', text, re.DOTALL):
            return "Media"
        if re.search(r'ALTA\s*\n.*?[■✓]', text, re.DOTALL):
            return "Alta"
        # Fallback: buscar explícito en texto narrativo
        return self._find(r'Magnitud[:\s]+(\w+)', text)