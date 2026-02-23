"""
Tests de integración para los 5 extractores.
Cada test valida los campos críticos usando los textos sanitizados (mock data)
provistos en conftest.py.
"""

import pytest
from src.extractors.ypf import YPFExtractor
from src.extractors.petsud import PetSudExtractor
from src.extractors.pluspetrol import PluspetrolExtractor
from src.extractors.aconcagua import AconcaguaExtractor
from src.extractors.pcr import PCRExtractor


# ── YPF ──────────────────────────────────────────────────────────────────────

class TestYPFExtractor:
    @pytest.fixture
    def data(self, ypf_text):
        return YPFExtractor().extract(ypf_text)

    def test_operador(self, data):
        assert data['OPERADOR'] == 'YPF S.A.'

    def test_num_inc(self, data):
        assert data['NUM_INC'] == 'YPF-0000999999'

    def test_area_concesionada(self, data):
        assert 'SIMULADO' in data['AREA_CONCE'].upper()

    def test_yacimiento(self, data):
        assert 'FICTICIO' in data['YACIMIENTO'].upper()

    def test_fecha_normalizada(self, data):
        assert data['FECHA_INC'] == '10-10-2025'

    def test_hora(self, data):
        assert data['HORA_INC'] == '10:00'

    def test_coordenadas_negativas(self, data):
        assert data['Y_COORD'] < 0
        assert data['X_COORD'] < 0

    def test_coordenadas_valores(self, data):
        assert abs(data['Y_COORD'] - (-37.333333)) < 0.0001
        assert abs(data['X_COORD'] - (-69.050000)) < 0.0001

    def test_srid(self, data):
        assert data['SRID_ORIGEN'] == 'WGS84-DD'

    def test_vol_derramado(self, data):
        assert data['VOL_D_m3'] == 8.5

    def test_vol_recuperado(self, data):
        assert data['VOL_R_m3'] == 1.0

    def test_agua_pct(self, data):
        assert data['AGUA_PCT'] == 99.8

    def test_area_afectada(self, data):
        assert data['AREA_AFECT_m2'] == 1250.0

    def test_magnitud(self, data):
        assert data['MAGNITUD'] == 'Menor'

    def test_subtipo_incidente(self, data):
        assert 'AGUA' in data['SUBTIPO_INC'].upper()


# ── PetSud ───────────────────────────────────────────────────────────────────

class TestPetSudExtractor:
    @pytest.fixture
    def data(self, petsud_text):
        return PetSudExtractor().extract(petsud_text)

    def test_operador(self, data):
        assert 'Sudamericanos' in data['OPERADOR']

    def test_num_inc(self, data):
        assert data['NUM_INC'] == 'PETSUD-999'

    def test_area(self, data):
        assert 'Ficticia' in data['AREA_CONCE']

    def test_fecha(self, data):
        assert data['FECHA_INC'] == '12-02-2026'

    def test_coordenadas_negativas(self, data):
        assert data['Y_COORD'] < 0
        assert data['X_COORD'] < 0

    def test_lat_en_rango_mendoza(self, data):
        assert -38.0 <= data['Y_COORD'] <= -32.0

    def test_lon_en_rango_mendoza(self, data):
        assert -70.0 <= data['X_COORD'] <= -67.0

    def test_vol_derramado(self, data):
        assert data['VOL_D_m3'] == 7.0

    def test_vol_recuperado(self, data):
        assert data['VOL_R_m3'] == 0.0

    def test_agua_100_pct(self, data):
        assert data['AGUA_PCT'] == 100.0

    def test_recurso_suelo(self, data):
        assert 'Suelo' in data['RECURSOS']

    def test_magnitud(self, data):
        assert data['MAGNITUD'] == 'Menor'


# ── Pluspetrol ───────────────────────────────────────────────────────────────

class TestPluspetrolExtractor:
    @pytest.fixture
    def data(self, pluspetrol_text):
        return PluspetrolExtractor().extract(pluspetrol_text)

    def test_operador(self, data):
        assert 'Pluspetrol' in data['OPERADOR']

    def test_num_inc(self, data):
        assert data['NUM_INC'] == 'PP-99/26'

    def test_area(self, data):
        assert data['AREA_CONCE'] == 'MOCK'

    def test_yacimiento(self, data):
        assert data['YACIMIENTO'] == 'MOCK'

    def test_fecha(self, data):
        assert data['FECHA_INC'] == '10-02-2026'

    def test_hora(self, data):
        assert data['HORA_INC'] == '19:00'

    def test_coordenadas_dd_directas(self, data):
        assert abs(data['Y_COORD'] - (-37.4200000)) < 0.0001
        assert abs(data['X_COORD'] - (-68.4000000)) < 0.0001

    def test_coords_gk_presentes(self, data):
        assert data['GK_X_M'] == 5858000.0
        assert data['GK_Y_M'] == 2552000.0

    def test_vol_derramado_pequeño(self, data):
        assert abs(data['VOL_D_m3'] - 0.015) < 0.0001

    def test_vol_recuperado_cero(self, data):
        assert data['VOL_R_m3'] == 0.0

    def test_agua_97_pct(self, data):
        assert data['AGUA_PCT'] == 97.0

    def test_area_afectada(self, data):
        assert data['AREA_AFECT_m2'] == 0.5

    def test_codigo_presente(self, data):
        assert data['CODIGO'] == 'DC_DR_9999_26'


# ── Aconcagua ─────────────────────────────────────────────────────────────────

class TestAconcaguaExtractor:
    @pytest.fixture
    def data(self, aconcagua_text):
        return AconcaguaExtractor().extract(aconcagua_text)

    def test_operador(self, data):
        assert 'Aconcagua' in data['OPERADOR']

    def test_num_inc_usa_subtipo(self, data):
        assert data['NUM_INC'] == 'ACO-MOCK-28'

    def test_area(self, data):
        assert 'Simulada' in data['AREA_CONCE']

    def test_fecha(self, data):
        assert data['FECHA_INC'] == '08-09-2025'

    def test_hora(self, data):
        assert data['HORA_INC'] == '18:00'

    def test_coordenadas_dd_con_signo(self, data):
        assert data['Y_COORD'] == -33.3400
        assert data['X_COORD'] == -68.9800

    def test_coordenadas_validas_mendoza(self, data):
        assert -38.0 <= data['Y_COORD'] <= -32.0
        assert -70.0 <= data['X_COORD'] <= -67.0

    def test_vol_derramado(self, data):
        assert data['VOL_D_m3'] == 1.5

    def test_vol_recuperado(self, data):
        assert data['VOL_R_m3'] == 0.0

    def test_agua_pct(self, data):
        assert data['AGUA_PCT'] == 48.0

    def test_area_afectada(self, data):
        assert data['AREA_AFECT_m2'] == 50.0

    def test_ppm_cero(self, data):
        assert data['PPM_HC'] == 0.0

    def test_responsable(self, data):
        assert 'Prueba' in data['RESPONSABLE']


# ── PCR ──────────────────────────────────────────────────────────────────────

class TestPCRExtractor:
    @pytest.fixture
    def data(self, pcr_text):
        return PCRExtractor().extract(pcr_text)

    def test_operador(self, data):
        assert 'PCR' in data['OPERADOR'] or 'Comodoro' in data['OPERADOR']

    def test_num_inc(self, data):
        assert 'MDZ-99' in data['NUM_INC']

    def test_area(self, data):
        assert 'Simulada' in data['AREA_CONCE']

    def test_fecha(self, data):
        assert data['FECHA_INC'] == '18-02-2026'

    def test_hora_deteccion(self, data):
        assert data['HORA_INC'] == '8:30'

    def test_hora_estimada(self, data):
        assert data['HORA_ESTIMADA'] == '8:00'

    def test_coordenadas_negativas(self, data):
        assert data['Y_COORD'] < 0
        assert data['X_COORD'] < 0

    def test_lat_aproximada(self, data):
        # 34°57'00.0" S ≈ -34.950°
        assert abs(data['Y_COORD'] - (-34.950)) < 0.01

    def test_lon_aproximada(self, data):
        # 69°31'00.0" O ≈ -69.516°
        assert abs(data['X_COORD'] - (-69.516)) < 0.01

    def test_vol_derramado(self, data):
        assert abs(data['VOL_D_m3'] - 1.1) < 0.01

    def test_vol_recuperado_cero(self, data):
        assert data['VOL_R_m3'] == 0.0

    def test_agua_40_pct(self, data):
        assert data['AGUA_PCT'] == 40.0

    def test_area_afectada(self, data):
        assert data['AREA_AFECT_m2'] == 11.0

    def test_responsable(self, data):
        assert 'Mock' in data['RESPONSABLE']

    def test_subtipo_hidrocarburo(self, data):
        assert data['SUBTIPO_INC'] is not None
        assert 'hidrocarburo' in data['SUBTIPO_INC'].lower()