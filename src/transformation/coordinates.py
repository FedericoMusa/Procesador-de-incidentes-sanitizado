"""
Módulo de transformación de coordenadas.
Convierte coordenadas WGS84 (grados decimales) a coordenadas cartesianas UTM (metros).

Para Mendoza, la zona UTM correspondiente es:
  - Zona 19S (la mayor parte de Mendoza y sur de la provincia)
  - Zona 20S (extremo este, menos común en operaciones O&G)

El módulo detecta automáticamente la zona correcta según la longitud.
También conserva la conversión a Gauss-Krüger Faja 2 (sistema local argentino)
ya que algunos informes como Pluspetrol reportan en ese sistema.
"""

import logging
from typing import Tuple

logger = logging.getLogger(__name__)

# Intentar importar pyproj; si no está disponible, usar conversión manual aproximada
try:
    from pyproj import Transformer, CRS
    PYPROJ_AVAILABLE = True
    logger.info("pyproj disponible — usando transformación precisa.")
except ImportError:
    PYPROJ_AVAILABLE = False
    logger.warning(
        "pyproj no está instalado. Se usará conversión UTM aproximada. "
        "Instalar con: pip install pyproj"
    )


# ── Transformación principal ────────────────────────────────────────────────

def transform_to_cartesian(lat: float, lon: float) -> Tuple[float, float]:
    """
    Convierte coordenadas WGS84 DD a UTM en metros.

    Args:
        lat: Latitud en grados decimales (negativo para Sur). Ej: -34.958
        lon: Longitud en grados decimales (negativo para Oeste). Ej: -69.533

    Returns:
        Tuple (easting_m, northing_m) en metros UTM.

    Raises:
        ValueError: Si las coordenadas son None o están fuera de rango razonable.
    """
    if lat is None or lon is None:
        raise ValueError("Las coordenadas no pueden ser None.")

    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        raise ValueError(f"Coordenadas fuera de rango global: lat={lat}, lon={lon}")

    utm_zone = _detect_utm_zone(lon)

    if PYPROJ_AVAILABLE:
        return _transform_pyproj(lat, lon, utm_zone)
    else:
        return _transform_manual(lat, lon, utm_zone)


def transform_to_gauss_kruger(lat: float, lon: float) -> Tuple[float, float]:
    """
    Convierte coordenadas WGS84 DD a Gauss-Krüger Faja 2 (Campo Inchauspe 1969).
    Este es el sistema local argentino usado históricamente en Pluspetrol y otros.

    Args:
        lat: Latitud WGS84 en grados decimales.
        lon: Longitud WGS84 en grados decimales.

    Returns:
        Tuple (x_gk, y_gk) en metros Gauss-Krüger.
    """
    if not PYPROJ_AVAILABLE:
        logger.warning("pyproj requerido para conversión Gauss-Krüger. Retornando (None, None).")
        return None, None

    try:
        # EPSG:22192 = Campo Inchauspe / Argentina 2 (Faja 2, meridiano central -69°)
        transformer = Transformer.from_crs(
            "EPSG:4326",   # WGS84
            "EPSG:22192",  # Campo Inchauspe Faja 2
            always_xy=True
        )
        x_gk, y_gk = transformer.transform(lon, lat)
        logger.debug(f"GK Faja 2: ({x_gk:.2f}, {y_gk:.2f})")
        return round(x_gk, 2), round(y_gk, 2)

    except Exception as e:
        logger.error(f"Error en transformación Gauss-Krüger: {e}")
        raise


# ── Detección de zona UTM ────────────────────────────────────────────────────

def _detect_utm_zone(lon: float) -> int:
    """
    Detecta la zona UTM según la longitud.
    Para Mendoza: zona 19 (lon < -66°) o zona 20 (lon >= -66°).
    En la práctica, casi todas las operaciones caen en zona 19S.
    """
    zone = int((lon + 180) / 6) + 1
    logger.debug(f"Zona UTM detectada: {zone}S para lon={lon}")
    return zone


# ── Backend pyproj (preciso) ─────────────────────────────────────────────────

def _transform_pyproj(lat: float, lon: float, utm_zone: int) -> Tuple[float, float]:
    """Transformación precisa usando pyproj."""
    try:
        # Construir CRS UTM para el hemisferio sur
        crs_utm = CRS.from_dict({
            "proj": "utm",
            "zone": utm_zone,
            "south": True,
            "datum": "WGS84",
            "units": "m",
        })
        transformer = Transformer.from_crs(
            "EPSG:4326",  # WGS84 lat/lon
            crs_utm,
            always_xy=True
        )
        easting, northing = transformer.transform(lon, lat)
        logger.debug(
            f"UTM {utm_zone}S (pyproj): E={easting:.2f}, N={northing:.2f}"
        )
        return round(easting, 2), round(northing, 2)

    except Exception as e:
        logger.error(f"Error en transformación pyproj: {e}")
        raise


# ── Backend manual (fallback sin pyproj) ────────────────────────────────────

def _transform_manual(lat: float, lon: float,
                      utm_zone: int) -> Tuple[float, float]:
    """
    Conversión UTM aproximada sin dependencias externas.
    Precisión: ~1 metro para latitudes de Mendoza. Suficiente para validación,
    no recomendado para cartografía de precisión.

    Algoritmo basado en la fórmula de Karney (simplificada).
    """
    import math

    # Constantes WGS84
    a = 6378137.0           # semieje mayor (m)
    f = 1 / 298.257223563   # achatamiento
    b = a * (1 - f)         # semieje menor
    e2 = 1 - (b / a) ** 2  # excentricidad al cuadrado
    e_prime2 = e2 / (1 - e2)
    k0 = 0.9996             # factor de escala UTM
    E0 = 500000.0           # falso este (m)
    N0 = 10000000.0         # falso norte hemisferio sur (m)

    lat_rad = math.radians(lat)
    lon_rad = math.radians(lon)
    lon0_rad = math.radians((utm_zone - 1) * 6 - 180 + 3)  # meridiano central

    N = a / math.sqrt(1 - e2 * math.sin(lat_rad) ** 2)
    T = math.tan(lat_rad) ** 2
    C = e_prime2 * math.cos(lat_rad) ** 2
    A = math.cos(lat_rad) * (lon_rad - lon0_rad)

    # Meridional arc
    e2_4 = e2 ** 2
    e2_6 = e2 ** 3
    M = a * (
        (1 - e2 / 4 - 3 * e2_4 / 64 - 5 * e2_6 / 256) * lat_rad
        - (3 * e2 / 8 + 3 * e2_4 / 32 + 45 * e2_6 / 1024) * math.sin(2 * lat_rad)
        + (15 * e2_4 / 256 + 45 * e2_6 / 1024) * math.sin(4 * lat_rad)
        - (35 * e2_6 / 3072) * math.sin(6 * lat_rad)
    )

    easting = k0 * N * (
        A
        + (1 - T + C) * A ** 3 / 6
        + (5 - 18 * T + T ** 2 + 72 * C - 58 * e_prime2) * A ** 5 / 120
    ) + E0

    northing = k0 * (
        M
        + N * math.tan(lat_rad) * (
            A ** 2 / 2
            + (5 - T + 9 * C + 4 * C ** 2) * A ** 4 / 24
            + (61 - 58 * T + T ** 2 + 600 * C - 330 * e_prime2) * A ** 6 / 720
        )
    ) + N0

    logger.debug(
        f"UTM {utm_zone}S (manual): E={easting:.2f}, N={northing:.2f}"
    )
    return round(easting, 2), round(northing, 2)