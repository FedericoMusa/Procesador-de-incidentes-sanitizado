"""
Tests para BaseExtractor.
Verifica los helpers compartidos: _find, _find_float, normalize_date,
dms_to_dd, parse_dms_string y validate_coordinates.
"""

import pytest
import logging
from src.extractors.base_extractor import BaseExtractor, LAT_MIN, LAT_MAX, LON_MIN, LON_MAX

logger = logging.getLogger(__name__)

class ConcreteExtractor(BaseExtractor):
    def extract(self, text):
        return {}

@pytest.fixture
def extractor():
    return ConcreteExtractor()
    def validate_coordinates(self, lat: float | None, lon: float | None) -> bool:
        """Verifica que las coordenadas estén dentro del bounding box de Mendoza."""
        if lat is None or lon is None:
            return False
        # Ahora LAT_MIN, etc. ya están definidos por la importación de arriba
        return LAT_MIN <= lat <= LAT_MAX and LON_MIN <= lon <= LON_MAX

    def validate_data(self, data: dict) -> bool:
        """Valida la integridad técnica de los datos extraídos."""
        lat, lon = data.get('Y_COORD'), data.get('X_COORD')
        if not self.validate_coordinates(lat, lon):
            # Usamos el logger definido al inicio del archivo
            logger.error(f"[VALIDATION_ERROR] {data.get('NUM_INC')}: Coordenadas fuera de rango")
            return False
        return True

@pytest.fixture
def extractor():
    return ConcreteExtractor()

# ... (el resto de tus clases de TestFind, TestFindFloat, etc. están perfectas)


@pytest.fixture
def extractor():
    return ConcreteExtractor()


# ── _find ────────────────────────────────────────────────────────────────────

class TestFind:
    def test_retorna_grupo_cuando_matchea(self, extractor):
        assert extractor._find(r'Operador:\s+(.+)', 'Operador: YPF S.A.') == 'YPF S.A.'

    def test_retorna_none_cuando_no_matchea(self, extractor):
        assert extractor._find(r'Campo:\s+(.+)', 'Sin ese campo') is None

    def test_nunca_lanza_attribute_error(self, extractor):
        # El error más común: usar .group() sobre None
        result = extractor._find(r'(NO_EXISTE)', 'texto sin match')
        assert result is None  # no explota

    def test_case_insensitive_por_defecto(self, extractor):
        assert extractor._find(r'operador:\s+(.+)', 'Operador: YPF') == 'YPF'


# ── _find_float ──────────────────────────────────────────────────────────────

class TestFindFloat:
    def test_convierte_punto(self, extractor):
        assert extractor._find_float(r'Vol:\s+([\d.]+)', 'Vol: 8.5') == 8.5

    def test_convierte_coma_argentina(self, extractor):
        assert extractor._find_float(r'Vol:\s+([\d,]+)', 'Vol: 1,50') == 1.5

    def test_retorna_none_si_no_matchea(self, extractor):
        assert extractor._find_float(r'(NO_EXISTE)', 'texto') is None

    def test_retorna_none_si_no_es_numero(self, extractor):
        assert extractor._find_float(r'Val:\s+(\w+)', 'Val: abc') is None


# ── normalize_date ───────────────────────────────────────────────────────────

class TestNormalizeDate:
    def test_formato_dd_mm_yyyy(self, extractor):
        assert extractor.normalize_date('10/10/2025') == '10-10-2025'

    def test_formato_dd_mm_yy(self, extractor):
        assert extractor.normalize_date('10/10/25') == '10-10-2025'

    def test_formato_con_guiones(self, extractor):
        assert extractor.normalize_date('18-02-2026') == '18-02-2026'

    def test_formato_iso(self, extractor):
        assert extractor.normalize_date('2025-10-10') == '10-10-2025'

    def test_none_retorna_none(self, extractor):
        assert extractor.normalize_date(None) is None

    def test_formato_invalido_retorna_none(self, extractor):
        assert extractor.normalize_date('no-es-fecha') is None


# ── dms_to_dd ────────────────────────────────────────────────────────────────

class TestDmsToDd:
    def test_hemisferio_sur_negativo(self, extractor):
        dd = extractor.dms_to_dd(37, 20, 56.2, 'S')
        assert dd < 0
        assert abs(dd - (-37.3489)) < 0.001

    def test_hemisferio_oeste_negativo(self, extractor):
        dd = extractor.dms_to_dd(69, 3, 12.2, 'W')
        assert dd < 0

    def test_hemisferio_norte_positivo(self, extractor):
        dd = extractor.dms_to_dd(37, 0, 0, 'N')
        assert dd > 0

    def test_sin_segundos(self, extractor):
        dd = extractor.dms_to_dd(37, 20.936, hemisphere='S')
        assert abs(dd - (-37.3489)) < 0.001


# ── parse_dms_string ─────────────────────────────────────────────────────────

class TestParseDmsString:
    def test_formato_compacto_petsud(self, extractor):
        # Formato PetSud: 33°30'57,62"
        result = extractor.parse_dms_string("33°30'57,62\"")
        assert result is not None
        assert abs(result - 33.516) < 0.001

    def test_formato_con_separadores_ypf(self, extractor):
        # Formato YPF grados y minutos: 37 ° / 20.936 '
        result = extractor.parse_dms_string("37 ° / 20.936 '")
        assert result is not None
        assert abs(result - 37.3489) < 0.001

    def test_formato_con_separadores_ypf_completo(self, extractor):
        # Formato YPF completo: 37 ° / 20 ' / 56.2 ''
        result = extractor.parse_dms_string("37 ° / 20 ' / 56.2 ''")
        assert result is not None
        assert abs(result - 37.3489) < 0.001

    def test_string_invalido_retorna_none(self, extractor):
        assert extractor.parse_dms_string("no_es_coordenada") is None


# ── validate_coordinates ─────────────────────────────────────────────────────

import pytest
import logging
from src.extractors.base_extractor import BaseExtractor, LAT_MIN, LAT_MAX, LON_MIN, LON_MAX

logger = logging.getLogger(__name__)

class ConcreteExtractor(BaseExtractor):
    def extract(self, text):
        return {}

@pytest.fixture
def extractor():
    return ConcreteExtractor()

# ... (Tus clases TestFind, TestFindFloat, etc., están perfectas)

class TestValidateCoordinates:
    def test_coordenadas_validas_mendoza(self, extractor):
        # Pluspetrol JCP — dentro de Mendoza
        assert extractor.validate_coordinates(-37.4246, -68.4049) is True

    def test_latitud_fuera_de_rango(self, extractor):
        assert extractor.validate_coordinates(-40.0, -68.0) is False

    def test_none_retorna_false(self, extractor):
        assert extractor.validate_coordinates(None, None) is False
        assert extractor.validate_coordinates(None, -68.0) is False
        assert extractor.validate_coordinates(-34.0, None) is False
        assert extractor.validate_coordinates(None, None) is False
    
    # --- CONTINUACIÓN DENTRO DE LA CLASE BaseExtractor ---

