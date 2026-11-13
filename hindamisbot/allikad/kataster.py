"""Maakataster: katastriüksuse pindala, sihtotstarve, omandivorm, kinnistu number ja maa maksustamishind.

Maa- ja Ruumiameti avalik WFS-teenus (sama andmestik, mida näitab X-GIS katastrikaart):
  https://gsavalik.envir.ee/geoserver/kataster/ows   kiht kataster:ky_omandivorm (varuvariant ky_kehtiv)
Andmestruktuur: Maa- ja Ruumiameti katastri kaarditeenuste andmestruktuuri dokument (kataster.ee).
Isikuandmeid (omaniku nime) teenus ei sisalda – ainult omandivormi (eraomand, munitsipaalomand, riigiomand…).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from ..mudel import Objekt
from .http import Klient

VÄLJAD = ("tunnus,l_aadress,pindala,siht1,so_prts1,siht2,so_prts2,siht3,so_prts3,mk_nimi,ov_nimi,ay_nimi,"
          "omvorm,kinnistu,maks_hind,marked,haritav,rohumaa,mets,ouemaa,muumaa,registr,muudet")
TUNNUS = re.compile(r"^\d{5}:\d{3}:\d{4}$")


@dataclass
class Katastriyksus:
    tunnus: str
    aadress: str | None
    pindala_m2: float | None
    sihtotstarbed: list = field(default_factory=list)   # [(nimi, protsent)]
    omandivorm: str | None = None
    kinnistu_nr: str | None = None
    maks_hind: float | None = None
    markus: str | None = None
    kolvikud: dict = field(default_factory=dict)

    @property
    def peamine_sihtotstarve(self) -> str | None:
        return max(self.sihtotstarbed, key=lambda x: x[1] or 0)[0] if self.sihtotstarbed else None

    @property
    def sihtotstarbed_tekst(self) -> str | None:
        return ", ".join(f"{n} {p:.0f}%" for n, p in self.sihtotstarbed) if self.sihtotstarbed else None


def _f(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def parsi(props: dict) -> Katastriyksus | None:
    if not props or not props.get("tunnus"):
        return None
    siht = []
    for i in (1, 2, 3):
        nimi = props.get(f"siht{i}")
        if nimi:
            siht.append((str(nimi).strip().lower(), _f(props.get(f"so_prts{i}")) or (100.0 if i == 1 else 0.0)))
    kolv = {k: _f(props.get(k)) for k in ("haritav", "rohumaa", "mets", "ouemaa", "muumaa") if _f(props.get(k))}
    return Katastriyksus(
        tunnus=props["tunnus"], aadress=props.get("l_aadress"), pindala_m2=_f(props.get("pindala")),
        sihtotstarbed=siht, omandivorm=props.get("omvorm"),
        kinnistu_nr=str(props["kinnistu"]) if props.get("kinnistu") else None,
        maks_hind=_f(props.get("maks_hind")), markus=props.get("marked"), kolvikud=kolv)


class Kataster:
    def __init__(self, klient: Klient, s):
        self.k = klient
        self.url = s.get_path("liidesed.kataster_wfs_url", "https://gsavalik.envir.ee/geoserver/kataster/ows")

    def _paring(self, kiht: str, tunnus: str, väljad: str | None):
        p = {"service": "WFS", "version": "2.0.0", "request": "GetFeature", "typeNames": f"kataster:{kiht}",
             "outputFormat": "application/json", "count": 1, "cql_filter": f"tunnus='{tunnus}'"}
        if väljad:
            p["propertyName"] = väljad
        return self.k.json(self.url, params=p)

    def yksus(self, tunnus: str) -> Katastriyksus | None:
        tunnus = str(tunnus).strip()
        if not TUNNUS.match(tunnus):          # kaitse CQL-süstimise ja vigase sisendi eest
            return None
        for kiht, väljad in (("ky_omandivorm", VÄLJAD), ("ky_kehtiv", None)):
            try:
                v = self._paring(kiht, tunnus, väljad)
            except ConnectionError:
                continue
            feats = (v or {}).get("features") or []
            if feats:
                return parsi(feats[0].get("properties") or {})
        return None


def rikasta(o: Objekt, ky: Katastriyksus) -> list[str]:
    src = "Maakataster"
    hoiatused = []
    o.maara("katastritunnus", ky.tunnus, src)
    o.maara("krundi_pind_m2", ky.pindala_m2, src)
    o.maara("sihtotstarve", ky.peamine_sihtotstarve, src)
    o.maara("sihtotstarbed", ky.sihtotstarbed_tekst, src)
    o.maara("omandivorm", ky.omandivorm, src)
    o.maara("kinnistu_nr", ky.kinnistu_nr, src)
    o.maara("maa_maksustamishind", ky.maks_hind, src)
    if ky.markus:
        o.maara("katastri_markus", ky.markus, src)
        hoiatused.append(f"Katastri märge: {ky.markus}.")
    if len(ky.sihtotstarbed) > 1:
        hoiatused.append(f"Katastriüksusel on mitu sihtotstarvet ({ky.sihtotstarbed_tekst}).")
    if ky.omandivorm and ky.omandivorm.lower() not in ("eraomand",):
        hoiatused.append(f"Omandivorm: {ky.omandivorm} – kontrolli kinnistusraamatust.")
    return hoiatused
