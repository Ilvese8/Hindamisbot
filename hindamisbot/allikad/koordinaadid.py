"""L-EST97 (EPSG:3301) -> WGS84 teisendus ja kauguse arvutus. Ilma välise teegita."""
from __future__ import annotations

import math

# GRS80 ellipsoid
_A = 6378137.0
_F = 1 / 298.257222101
_E = math.sqrt(2 * _F - _F ** 2)

# L-EST97 Lamberti koonusprojektsiooni parameetrid
_LAT1 = math.radians(58.0)
_LAT2 = math.radians(59 + 20 / 60)
_LAT0 = math.radians(57 + 31 / 60 + 3.19415 / 3600)
_LON0 = math.radians(24.0)
_FE = 500000.0
_FN = 6375000.0


def _m(phi):
    return math.cos(phi) / math.sqrt(1 - (_E * math.sin(phi)) ** 2)


def _t(phi):
    s = math.sin(phi)
    return math.tan(math.pi / 4 - phi / 2) / ((1 - _E * s) / (1 + _E * s)) ** (_E / 2)


_N = (math.log(_m(_LAT1)) - math.log(_m(_LAT2))) / (math.log(_t(_LAT1)) - math.log(_t(_LAT2)))
_FF = _m(_LAT1) / (_N * _t(_LAT1) ** _N)
_R0 = _A * _FF * _t(_LAT0) ** _N


def lest97_wgs84(ida: float, põhi: float) -> tuple[float, float]:
    """Teisendab L-EST97 koordinaadid (idakoordinaat, põhjakoordinaat) -> (lat, lon) kraadides."""
    dx = ida - _FE
    dy = _R0 - (põhi - _FN)
    r = math.copysign(math.hypot(dx, dy), _N)
    t = (r / (_A * _FF)) ** (1 / _N)
    theta = math.atan2(dx, dy)
    lon = theta / _N + _LON0
    phi = math.pi / 2 - 2 * math.atan(t)
    for _ in range(10):
        s = math.sin(phi)
        phi_uus = math.pi / 2 - 2 * math.atan(t * ((1 - _E * s) / (1 + _E * s)) ** (_E / 2))
        if abs(phi_uus - phi) < 1e-12:
            phi = phi_uus
            break
        phi = phi_uus
    return math.degrees(phi), math.degrees(lon)


def kaugus_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Haversine kaugus meetrites."""
    r = 6371008.8
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))
