"""
Extractor para informes de Petróleos Sudamericanos.
Formato: tabla estructurada "Informe Preliminar Mendoza" con N° de Comunicado.
Sistema de coordenadas: DMS compacto (ej. 33°30'57,62").

Variantes de símbolos DMS observadas en PDFs de PetSud:
  ´ (U+00B4 acento agudo) como símbolo de minutos
  '' (dos apóstrofos) como símbolo de segundos
"""

import logging
import re
from src.extractors.base_extractor import BaseExtractor

logger = logging.getLogger(__name__)


class PetSudExtractor(BaseExtractor):

    # Patrones que indican inicio de un nuevo campo — detienen la captura de coord
    _STOP_FIELD = re.compile(
        r'Coordenadas|Concentraci|Volumen|rea|Medidas|Suelo|Fecha|Hora|' +
        r'Operador|Tipo|Subtipo|Magnitud|Descripci',
        re.IGNORECASE
    )

    def extract(self, text: str) -> dict:
        data = {}

        data['OPERADOR'] = "Petróleos Sudamericanos"

        num_inc = self._find(r'N[°º]\s*DE\s*COMUNICADO\s+(\d+)', text)
        data['NUM_INC'] = f"PETSUD-{num_inc}" if num_inc else None

        data['AREA_CONCE'] = self._find(r'Área operativa\s*/\s*concesión\s+(.+)', text)
        data['YACIMIENTO'] = self._find(r'Yacimiento\s+(.+)', text)
        data['CUENCA']     = self._find(r'Cuenca\s+(.+)', text)

        data['INSTALACION'] = self._find(r'Instalación asociada\s+(.+)', text)
        data['TIPO_INST']   = self._find(r'Tipo de instalación\s+(.+)', text)

        data['SUBTIPO_INC'] = self._find(r'Subtipo de incidente\s+(.+)', text)
        data['CAUSA']       = self._find(r'Tipo de evento causante\s+(.+)', text)
        data['MAGNITUD']    = self._find(r'Magnitud del Incidente\s+(.+)', text)
        data['DESCRIPCION'] = self._find(r'Descripción de la rotura y afectación\s*\n(.+)', text)

        fecha_raw = self._find(r'Fecha de ocurrencia\s+(\d{1,2}/\d{1,2}/\d{4})', text)
        data['FECHA_INC'] = self.normalize_date(fecha_raw)
        data['HORA_INC']  = self._find(r'Hora de ocurrencia\s+(\d{1,2}:\d{2})', text)

        lat_raw = self._extract_coord_raw(r'Coordenadas x\s*\(latitud\s*-\s*S\)', text)
        lon_raw = self._extract_coord_raw(r'Coordenadas y\s*\(Longitud\s*-\s*O\)', text)

        lat_dd = self._parse_and_negate(lat_raw, "Latitud")
        lon_dd = self._parse_and_negate(lon_raw, "Longitud")

        data['Y_COORD']     = lat_dd
        data['X_COORD']     = lon_dd
        data['SRID_ORIGEN'] = "WGS84-DMS→DD"

        if not self.validate_coordinates(data['Y_COORD'], data['X_COORD']):
            logger.warning(
                f"[PetSud] Coordenadas inválidas en {data['NUM_INC']}. "
                "Verificar si hay error de tipeo en el informe original."
            )

        data['VOL_D_m3']     = self._find_float(r'Volumen\s+m3?\s+derramado\s+([\d.,]+)', text)
        data['VOL_R_m3']     = self._find_float(r'Volumen\s+m3?\s+recuperado\s+([\d.,]+)', text)
        data['AGUA_PCT']     = self._find_float(r'%\s*AGUA\s+DERRAMADO\s+([\d.,]+)', text)
        data['AREA_AFECT_m2'] = self._find_float(r'Área\s+m2\s+([\d.,]+)', text)
        data['PPM_HC']       = self._find(r'Concentración de hidrocarburo\s*\(ppm\)\s+(.+)', text)

        recursos = []
        for recurso in ["Suelo", "Cauce aluvional", "Agua superficial", "Vegetacion", "Otros"]:
            if re.search(rf'{recurso}\s+x', text, re.IGNORECASE):
                recursos.append(recurso)
        data['RECURSOS'] = ", ".join(recursos) if recursos else None

        data['MEDIDAS'] = self._find(
            r'Medidas adoptadas\s+(.+?)(?:\n\n|\Z)', text, flags=re.DOTALL)

        return data

    @staticmethod
    def _is_dms_complete(s: str) -> bool:
        """True si el string ya contiene grados, minutos Y segundos normalizados."""
        from src.extractors.base_extractor import BaseExtractor as _B
        n = re.sub(r'\s+', ' ', s)
        n = _B._normalize_dms_symbols(n)
        return bool(re.search(r'\d+\s*°\s*\d+\s*\'\s*[\d.]+\s*"?', n))

    def _extract_coord_raw(self, label_pattern: str, text: str) -> str | None:
        """
        Extrae el texto crudo de una coordenada de forma tolerante al formato.

        Recorre líneas tras el label acumulando hasta tener un valor DMS completo
        (grados + minutos + segundos), deteniéndose si aparece el label de otro
        campo. Esto cubre tres variantes observadas en PDFs de PetSud:
          - Una línea:   "33°34'39,63\""
          - Una línea:   "33° 03' 54''"   (espacios, dos apóstrofos)
          - Una línea:   "33° 35´15,04''" (acento agudo)
          - Dos líneas:  "33°\n34'39,63\""
        """
        m = re.search(label_pattern, text, re.IGNORECASE)
        if not m:
            return None

        window = text[m.end(): m.end() + 150]
        lines = [l.strip() for l in window.splitlines() if l.strip()]

        collected = []
        for line in lines:
            # Parar si la línea es el label de otro campo (no contiene °)
            if self._STOP_FIELD.search(line) and not re.search(r'\d+\s*[°º]', line):
                break
            collected.append(line)
            # Parar solo cuando DMS está completo (grados+minutos+segundos)
            if self._is_dms_complete(' '.join(collected)):
                break

        combined = ' '.join(collected)

        # Filtrar solo caracteres DMS válidos
        # Incluye ´ (U+00B4) y ′ (U+2032) usados por PetSud como símbolo de minutos
        clean = re.sub(r'[^\d°º\'\".,′″´\u00B4\u2032\s]', '', combined)
        result = clean.strip()

        if not re.search(r'\d+\s*[°º]', result):
            return None

        return result or None

    def _parse_and_negate(self, raw: str | None, label: str) -> float | None:
        """Parsea DMS y aplica signo negativo (S/W siempre negativos en Mendoza)."""
        if raw is None:
            logger.warning(f"[PetSud] {label} no encontrada en el texto.")
            return None
        dd = self.parse_dms_string(raw)
        if dd is None:
            return None
        return -abs(dd)
