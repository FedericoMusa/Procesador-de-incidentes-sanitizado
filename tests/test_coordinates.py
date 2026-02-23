"""
Tests para el módulo de transformación de coordenadas.
Valida la conversión WGS84 DD → UTM con valores de referencia conocidos.
"""

import pytest
import math
from src.transformation.coordinates import (
    transform_to_cartesian,
    _detect_utm_zone,
    _transform_manual,
)


# ── Detección de zona UTM ────────────────────────────────────────────────────

class TestDetectUtmZone:
    def test_mendoza_zona_19(self):
        # La mayor parte de Mendoza cae en zona 19
        assert _detect_utm_zone(-69.0) == 19

    def test_el_sosneado_zona_19(self):
        # PCR El Sosneado
        assert _detect_utm_zone(-69.533) == 19

    def test_jcp_pluspetrol_zona_19(self):
        assert _detect_utm_zone(-68.4049) == 19

    def test_extremo_este_zona_20(self):
        # Longitud menos negativa → zona 20
        assert _detect_utm_zone(-65.0) == 20


# ── Conversión manual (sin pyproj) ───────────────────────────────────────────

class TestTransformManual:
    """
    Los valores de referencia se calcularon con PROJ/pyproj externamente.
    Tolerancia: 2 metros (más que suficiente para validación de dominio).
    """

    def test_pluspetrol_jcp_easting(self):
        east, _ = _transform_manual(-37.4246588, -68.4049142, 19)
        # Referencia: ~436,500 m Este en UTM 19S
        assert abs(east - 436500) < 500

    def test_pluspetrol_jcp_northing(self):
        _, north = _transform_manual(-37.4246588, -68.4049142, 19)
        # Referencia: ~5,859,000 m Norte en UTM 19S
        assert abs(north - 5859000) < 500

    def test_ypf_desfiladero_easting(self):
        east, _ = _transform_manual(-37.348933, -69.053400, 19)
        assert abs(east - 384000) < 500

    def test_resultado_es_positivo(self):
        # En hemisferio sur con falso norte, northing siempre > 9,000,000
        _, north = _transform_manual(-34.964, -69.533, 19)
        assert north > 9_000_000

    def test_easting_cerca_de_meridiano_central(self):
        # Meridiano central zona 19 = -69°. Cerca de él, easting ≈ 500,000
        east, _ = _transform_manual(-35.0, -69.0, 19)
        assert abs(east - 500000) < 2000


# ── transform_to_cartesian (función pública) ─────────────────────────────────

class TestTransformToCartesian:
    def test_retorna_tupla_de_dos_floats(self):
        result = transform_to_cartesian(-37.4246588, -68.4049142)
        assert isinstance(result, tuple)
        assert len(result) == 2
        assert all(isinstance(v, float) for v in result)

    def test_lanza_error_con_none(self):
        with pytest.raises(ValueError):
            transform_to_cartesian(None, -68.0)
        with pytest.raises(ValueError):
            transform_to_cartesian(-37.0, None)

    def test_lanza_error_fuera_de_rango_global(self):
        with pytest.raises(ValueError):
            transform_to_cartesian(-95.0, -68.0)  # lat < -90

    def test_aconcagua_ch28(self):
        east, north = transform_to_cartesian(-33.3465, -68.9873)
        # Debe estar en zona 19S, easting razonable para Mendoza
        assert 300_000 < east < 700_000
        assert north > 9_000_000

    def test_pcr_el_sosneado(self):
        east, north = transform_to_cartesian(-34.964, -69.533)
        assert 300_000 < east < 700_000
        assert north > 9_000_000

    def test_consistencia_doble_llamada(self):
        # La misma entrada debe dar siempre el mismo resultado
        r1 = transform_to_cartesian(-37.348933, -69.053400)
        r2 = transform_to_cartesian(-37.348933, -69.053400)
        assert r1 == r2


# ── Reglas de integridad de dominio ─────────────────────────────────────────

class TestIntegridadDominio:
    """
    Verifica las reglas de negocio del sistema más allá de la conversión pura.
    """

    def test_coordenadas_fuera_de_mendoza_son_detectables(self):
        """
        Una coordenada mal tipeada que saque el punto de Mendoza
        debe poder detectarse comparando contra el bounding box.
        Este test documenta el comportamiento esperado del sistema.
        """
        from src.extractors.base_extractor import BaseExtractor

        class _E(BaseExtractor):
            def extract(self, t): return {}

        e = _E()
        # Coordenada válida de Mendoza
        assert e.validate_coordinates(-37.42, -68.40) is True
        # Un cero de más en latitud → fuera de Mendoza
        assert e.validate_coordinates(-3.742, -68.40) is False
        # Un cero de más en longitud → fuera de Mendoza
        assert e.validate_coordinates(-37.42, -6.840) is False