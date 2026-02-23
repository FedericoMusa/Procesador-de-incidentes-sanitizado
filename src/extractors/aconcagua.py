"""
Extractor para informes de Aconcagua Energía S.A.
Formato: "Informe de Incidente" — tabla dos columnas, sin número de comunicado explícito.
Sistema de coordenadas: WGS84 grados decimales directos (los más simples de todos).

Particularidad: el NUM_INC se construye desde el subtipo de instalación (ej. "CH-28"),
ya que Aconcagua no incluye un número de comunicado en el cuerpo del informe.
"""

import logging
from src.extractors.base_extractor import BaseExtractor

logger = logging.getLogger(__name__)


class AconcaguaExtractor(BaseExtractor):
    """
    Extrae datos de incidentes del formato de Aconcagua Energía S.A.

    Este es el formato más limpio: coordenadas DD directas, campos bien
    etiquetados y sin ambigüedad. El mayor riesgo es que varios campos
    opcionales (Tipo de Incidente, Tipo de evento causante) pueden venir vacíos.
    """

    AREA = "Chañares Herrados"
    OPERADOR = "Aconcagua Energía S.A."

    def extract(self, text: str) -> dict:
        data = {}

        # ── Identificación ──────────────────────────────────────────────
        data['OPERADOR'] = self.OPERADOR

        # El identificador único es el subtipo de instalación (ej. "CH-28")
        subtipo_inst = self._find(
            r'Subtipo de instalación involucrada\s+(\S+)', text)
        data['NUM_INC'] = f"ACO-{subtipo_inst}" if subtipo_inst else None

        # ── Área y ubicación ────────────────────────────────────────────
        data['AREA_CONCE'] = self._find(
            r'Nombre del área en recepción o\s+(.+)', text) or self.AREA
        data['YACIMIENTO'] = self._find(
            r'Nombre del yacimiento\s+(.+)', text)

        # ── Instalación ─────────────────────────────────────────────────
        data['TIPO_INST'] = self._find(
            r'Tipo de instalación involucrada\s+(.+)', text)
        data['INSTALACION'] = subtipo_inst  # ej. "CH-28"

        # ── Incidente ───────────────────────────────────────────────────
        # Tipo de Incidente puede venir vacío en el PDF
        data['SUBTIPO_INC'] = self._find(
            r'Tipo de Incidente\s+(.+?)(?=\n)', text) or "No especificado"
        data['DESCRIPCION'] = self._find(
            r'Detalle del incidente\s+(.+?)(?=Tipo de instalación)', text,
            flags=0x10 | 0x02)  # DOTALL | IGNORECASE
        data['CAUSA'] = self._find(
            r'Subtipo del evento causante\s+(.+?)(?=\n)', text) or "No especificado"
        # Magnitud no viene en el PDF — se infiere por volumen al final del método
        data['RESPONSABLE'] = self._find(
            r'Reponsable de la Instalación\s+(.+)', text)

        # ── Fecha ───────────────────────────────────────────────────────
        fecha_raw = self._find(
            r'Fecha de Ocurrencia\s+(\d{2}/\d{2}/\d{4})', text)
        data['FECHA_INC'] = self.normalize_date(fecha_raw)
        data['HORA_INC'] = self._find(
            r'Hora de Ocurrencia\s+(\d{2}:\d{2})', text)

        # ── Coordenadas DD directas ──────────────────────────────────────
        # Formato: "Latitud Decimal  -33.3465" / "Longitud Decimal  -68.9873"
        # Ya vienen con signo negativo en el PDF
        lat_dd = self._find_float(r'Latitud Decimal\s+(-?[\d.]+)', text)
        lon_dd = self._find_float(r'Longitud Decimal\s+(-?[\d.]+)', text)

        data['Y_COORD'] = lat_dd
        data['X_COORD'] = lon_dd
        data['SRID_ORIGEN'] = "WGS84-DD"

        if not self.validate_coordinates(data['Y_COORD'], data['X_COORD']):
            logger.warning(
                f"[Aconcagua] Coordenadas inválidas en {data['NUM_INC']}"
            )

        # ── Volúmenes ───────────────────────────────────────────────────
        data['VOL_D_m3'] = self._find_float(
            r'Volumen\s+de\s+líquido\s+derramado\s+([\d.,]+)', text)
        data['VOL_R_m3'] = self._find_float(
            r'Volumen\s+de\s+fluido\s+recuperado\s+([\d.,]+)', text)
        data['AGUA_PCT'] = self._find_float(
            r'%\s+de\s+Agua\s+([\d.,]+)', text)
        data['AREA_AFECT_m2'] = self._find_float(
            r'Superficie aprox\.\s+afectada\s+([\d.,]+)', text)
        data['PPM_HC'] = self._find_float(
            r'PPM\s+([\d.,]+)', text)
        data['VOL_GAS_m3'] = self._find_float(
            r'Volumen de gas\s+([\d.,]+)', text)

        # ── Medidas ─────────────────────────────────────────────────────
        data['MEDIDAS'] = self._find(
            r'Medidas adoptadas\s+(.+?)(?=Dirección de e-mail|$)',
            text, flags=0x10 | 0x02)

        # ── Magnitud inferida por volumen (fallback — PDF no la informa) ─
        data['MAGNITUD'] = self.inferir_magnitud(
            data.get('VOL_D_m3'), data.get('PPM_HC')
        )
        logger.info(
            f"[Aconcagua] Magnitud inferida por volumen: {data['MAGNITUD']} "
            f"(vol={data.get('VOL_D_m3')} m3, ppm={data.get('PPM_HC')})"
        )

        return data