"""Maa- ja Ruumiameti In-ADS gazetteer: aadressi normaliseerimine, koordinaadid, seosed EHR-i ja katastriga.

Dokumentatsioon: https://inaadress.maaamet.ee/ (In-ADS arendaja juhend). Teenusel on päringulimiidid –
massiliseks kasutuseks kasuta ADS-i avaandmete CSV-väljavõtet.
Vastuse väljanimed võivad versiooniti muutuda, seepärast loetakse neid mitme võimaliku nime järgi.
"""
from __future__ import annotations

from ..mudel import Objekt
from .http import Klient
from .koordinaadid import lest97_wgs84

FEATURES = "EHAK,VAIKEKOHT,TANAV,KATASTRIYKSUS,EHITISHOONE"


def _esimene(d: dict, *võtmed):
    for v in võtmed:
        if v in d and d[v] not in (None, "", []):
            return d[v]
    return None


def _float(v):
    try:
        return float(str(v).replace(",", "."))
    except (TypeError, ValueError):
        return None


def otsi(klient: Klient, url: str, aadress: str, korter: str | None = None, features: str = FEATURES) -> dict | None:
    params = {"address": aadress, "results": 1, "features": features, "seosreg": 1, "ehr2": 1}
    if korter:
        params["appartment"] = korter
    vastus = klient.json(url, params=params)
    aadressid = vastus.get("addresses") or []
    return aadressid[0] if aadressid else None


def rikasta(objekt: Objekt, kirje: dict) -> list[str]:
    """Kannab In-ADS kirje andmed objektile. Tagastab hoiatused."""
    hoiatused = []
    src = "In-ADS"
    objekt.maara("normaliseeritud_aadress", _esimene(kirje, "pikkaadress", "taisaadress", "aadresstekst"), src)
    objekt.maara("maakond", _esimene(kirje, "maakond"), src)
    objekt.maara("omavalitsus", _esimene(kirje, "omavalitsus"), src)
    objekt.maara("asustusyksus", _esimene(kirje, "asustusyksus"), src)
    objekt.maara("ads_oid", _esimene(kirje, "ads_oid", "adr_id"), src)

    # Koordinaadid: eelistatult WGS84 (viitepunkt_b/l), muidu L-EST97 viitepunkt (põhjakoordinaat ~6.3–6.7 mln)
    b, l = _float(kirje.get("viitepunkt_b")), _float(kirje.get("viitepunkt_l"))
    x, y = _float(kirje.get("viitepunkt_x")), _float(kirje.get("viitepunkt_y"))
    if b and l:
        objekt.maara("lat", round(b, 6), src)
        objekt.maara("lon", round(l, 6), src)
    elif x and y:
        ida, põhi = (x, y) if y > x else (y, x)
        lat, lon = lest97_wgs84(ida, põhi)
        objekt.maara("lat", round(lat, 6), src)
        objekt.maara("lon", round(lon, 6), src)
    else:
        hoiatused.append("In-ADS ei tagastanud koordinaate.")

    # "tunnus" tähendab EHITISHOONE puhul EHR-koodi, KATASTRIYKSUS puhul katastritunnust
    liik = str(_esimene(kirje, "liikVal", "liik") or "").upper()
    if "EHITIS" in liik or liik == "E":
        objekt.maara("ehr_kood", _esimene(kirje, "tunnus"), src)
    elif "KATASTR" in liik or liik == "K":
        objekt.maara("katastritunnus", _esimene(kirje, "tunnus"), src)
    objekt.maara("katastritunnus", _esimene(kirje, "katastritunnus"), src)
    objekt.maara("ehr_kood", _esimene(kirje, "ehr_kood", "ehrkood", "ehitisehrkood"), src)
    # Hooneosa (korter/äripind) kood In-ADS-i korterite loendist
    if objekt.hooneosa_nr:
        for k in kirje.get("appartments") or []:
            if str(k.get("tahis", "")).lower() == str(objekt.hooneosa_nr).lower():
                objekt.maara("osa_ehr_kood", k.get("tunnus"), src)
                objekt.maara("ads_oid", k.get("ads_oid"), src, kirjuta_yle=True)
                break
    for seos in kirje.get("seosed") or kirje.get("objektid") or []:
        if not isinstance(seos, dict):
            continue
        liik = str(_esimene(seos, "liik", "liikVal", "objekt_liik") or "").upper()
        kood = _esimene(seos, "tunnus", "kood", "ehr_kood", "objekt_kood")
        if "KATASTR" in liik or liik == "KY":
            objekt.maara("katastritunnus", kood, src)
        elif "EHITIS" in liik or liik in ("EH", "EHR"):
            objekt.maara("ehr_kood", kood, src)
    asum = _esimene(kirje, "asum")
    if asum:
        objekt.allikad.setdefault("asum", asum)
    if not objekt.ehr_kood and objekt.tyyp is not None and objekt.tyyp.value != "maa":
        hoiatused.append("EHR-koodi ei leitud – ehitise andmed tuleb anda käsitsi või EHR-väljavõttest.")
    return hoiatused


def eralda_hooneosa(aadress: str) -> tuple[str, str | None]:
    """'Ehitajate tee 35-55, Tallinn' -> ('Ehitajate tee 35, Tallinn', '55'). Ilma osata tagastab (aadress, None)."""
    import re
    osad = aadress.split(",")
    m = re.match(r"^(.*?\d+[A-Za-zÕÄÖÜõäöü]?)\s*-\s*(\d+[A-Za-z]?)\s*$", osad[0].strip())
    if not m:
        return aadress, None
    return ", ".join([m.group(1)] + [x.strip() for x in osad[1:]]), m.group(2)
