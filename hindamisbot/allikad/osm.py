"""OpenStreetMap (Overpass API): kaugused lähimate teenusteni. Andmed © OpenStreetMap kaastöötajad, ODbL."""
from __future__ import annotations

from .http import Klient
from .koordinaadid import kaugus_m

KATEGOORIAD = {
    "ühistransport": ['node["highway"="bus_stop"]', 'node["railway"="tram_stop"]', 'node["railway"="station"]'],
    "kool": ['nwr["amenity"="school"]', 'nwr["amenity"="kindergarten"]'],
    "pood": ['nwr["shop"="supermarket"]', 'nwr["shop"="convenience"]'],
    "veekogu": ['way["natural"="coastline"]', 'way["natural"="water"]', 'relation["natural"="water"]'],
}


def paring(lat: float, lon: float, raadius: int = 3000) -> str:
    osad = []
    for filtrid in KATEGOORIAD.values():
        for f in filtrid:
            osad.append(f"{f}(around:{raadius},{lat},{lon});")
    return f"[out:json][timeout:25];({''.join(osad)});out tags geom center;"


def _kategooria(tags: dict) -> str | None:
    if tags.get("highway") == "bus_stop" or tags.get("railway") in ("tram_stop", "station"):
        return "ühistransport"
    if tags.get("amenity") in ("school", "kindergarten"):
        return "kool"
    if tags.get("shop") in ("supermarket", "convenience"):
        return "pood"
    if tags.get("natural") in ("coastline", "water"):
        return "veekogu"
    return None


def _punktid(el: dict):
    if "lat" in el:
        yield el["lat"], el["lon"]
    for g in el.get("geometry") or []:
        yield g["lat"], g["lon"]
    for m in el.get("members") or []:
        for g in m.get("geometry") or []:
            yield g["lat"], g["lon"]
    if "center" in el:
        yield el["center"]["lat"], el["center"]["lon"]


def kaugused(klient: Klient, url: str, lat: float, lon: float, raadius: int = 3000) -> dict:
    """Tagastab {kategooria: lähima objekti kaugus meetrites}. Puuduvad kategooriad: > raadius."""
    vastus = klient.json(url, data={"data": paring(lat, lon, raadius)}, meetod="POST")
    return arvuta_kaugused(vastus, lat, lon)


def arvuta_kaugused(vastus: dict, lat: float, lon: float) -> dict:
    tulem: dict[str, float] = {}
    for el in vastus.get("elements", []):
        kat = _kategooria(el.get("tags") or {})
        if not kat:
            continue
        for plat, plon in _punktid(el):
            d = kaugus_m(lat, lon, plat, plon)
            if d < tulem.get(kat, float("inf")):
                tulem[kat] = round(d)
    return tulem
