"""Ehitisregistri (EHR) avalik andmepäring: kõik ehitised ja nende osad (korterid, äripinnad jm).

Sama liides, mida kasutab ehitisregistri avalik vaade (https://livekluster.ehr.ee/ui/ehr/v1/building/<EHR-kood>).
Liides ei ole ametlikult dokumenteeritud ja võib muutuda – siis kasutatakse kohalikku EHR-väljavõtet.

Hoone tasemel: ehitusaasta, korruste arv, lift, suletud netopind, eluruumide pind, kasutamise otstarve,
kandekonstruktsiooni materjal, katastritunnus(ed), energiamärgis.
Hooneosa tasemel (eluruum/mitteeluruum): pind, tubade arv, sissepääsu korrus.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime

from ..mudel import Objekt
from .ehr import materjali_klass
from .http import Klient

OSA_LIIK = {"K": "eluruum", "M": "mitteeluruum", "Y": "üldkasutatav pind", "T": "tehnopind"}


def _f(v):
    try:
        return float(str(v).replace(",", "."))
    except (TypeError, ValueError):
        return None


def _i(v):
    x = _f(v)
    return int(x) if x is not None else None


def _list(d, *tee):
    for t in tee:
        d = (d or {}).get(t) if isinstance(d, dict) else None
    return d if isinstance(d, list) else []


@dataclass
class Hooneosa:
    tahis: str | None
    ehr_kood: str | None
    liik: str
    pind_m2: float | None
    tube: int | None
    korrus: int | None
    aadress: str | None


@dataclass
class Ehitis:
    ehr_kood: str
    nimetus: str | None
    otstarve: str | None
    aadress: str | None
    kaos_kood: str | None
    ehitusaasta: int | None
    korruseid: int | None
    lift: bool | None
    suletud_netopind: float | None
    eluruumide_pind: float | None
    ehitisealune_pind: float | None
    materjal_tekst: str | None
    katastritunnused: list = field(default_factory=list)
    energiaklass: str | None = None
    energiamargise_kp: date | None = None
    osad: list = field(default_factory=list)
    esmane_kasutus: int | None = None             # EHR-i väli "esmase kasutuselevõtu aasta"
    ehitusaasta_allikas: str | None = None        # millisest dokumendist ehitusaasta pärineb
    rekonstrueeritud: int | None = None           # viimase rekonstrueerimise/ümberehituse kasutusloa aasta

    @property
    def materjal(self):
        return materjali_klass(self.materjal_tekst)

    def leia_osa(self, tähis: str | None = None, osa_ehr_kood: str | None = None) -> Hooneosa | None:
        if osa_ehr_kood:
            o = next((o for o in self.osad if o.ehr_kood == osa_ehr_kood), None)
            if o:
                return o
        if tähis:
            t = str(tähis).strip().lower()
            return next((o for o in self.osad if (o.tahis or "").lower() == t), None) or \
                next((o for o in self.osad if (o.aadress or "").lower().endswith(f"-{t}")), None)
        return None

    @property
    def eluruume(self) -> int:
        return sum(1 for o in self.osad if o.liik == "eluruum")

    @property
    def mitteeluruume(self) -> int:
        return sum(1 for o in self.osad if o.liik == "mitteeluruum")


def parsi(andmed: dict, energia: list | None = None) -> Ehitis | None:
    e = (andmed or {}).get("ehitis") or {}
    a = e.get("ehitiseAndmed") or {}
    if not a.get("ehrKood"):
        return None
    p = e.get("ehitisePohiandmed") or {}
    kehad = _list(e, "ehitiseKehand", "kehand")
    tehn = _list(e, "ehitiseTehnilisedNaitajad", "tehnilineNaitaja")
    materjal = next((t.get("nimetus") for t in tehn if t.get("klKood") == "KONS_KKONSTR"), None) or \
        next((t.get("nimetus") for t in tehn if t.get("klKood") == "KONS_VSEIN"), None)
    otstarbed = _list(e, "ehitiseKasutusotstarbed", "kasutusotstarve")
    elu = sum(_f(x.get("eluruumidePind")) or 0 for x in otstarbed) or None
    osad = []
    for k in kehad:
        for o in _list(k, "ehitiseOsad", "ehitiseOsa"):
            pa = o.get("ehitiseOsaPohiandmed") or {}
            osad.append(Hooneosa(
                tahis=o.get("tahis"), ehr_kood=o.get("ehrKood"), liik=OSA_LIIK.get(o.get("liik"), o.get("liik") or ""),
                pind_m2=_f(pa.get("pind")), tube=_i(pa.get("tubadeArv")), korrus=_i(pa.get("sissepaasuKorrus")),
                aadress=(o.get("aadress") or {}).get("lahiaadress")))
    ehitis = Ehitis(
        ehr_kood=str(a["ehrKood"]), nimetus=a.get("nimetus"), otstarve=a.get("kaosIdTxt"), aadress=a.get("taisaadress"),
        kaos_kood=str(a.get("kaosKood") or a.get("kaosIdPeamine") or "") or None,
        ehitusaasta=_i(a.get("esmaneKasutus")) or next((_i(k.get("esmane_kasutus")) for k in kehad if k.get("esmane_kasutus")), None),
        korruseid=_i(p.get("maxKorrusteArv")), lift=None if p.get("lift") is None else _i(p.get("lift")) > 0,
        suletud_netopind=_f(p.get("suletud_netopind")), eluruumide_pind=elu,
        ehitisealune_pind=_f(p.get("ehitisalunePind")), materjal_tekst=materjal,
        katastritunnused=[k.get("katastritunnus") for k in _list(e, "ehitiseKatastriyksused", "ehitiseKatastriyksus")
                          if k.get("katastritunnus")],
        osad=osad,
    )
    ehitis.esmane_kasutus = ehitis.ehitusaasta
    ehitis.ehitusaasta_allikas = "esmase kasutuselevõtu aasta" if ehitis.ehitusaasta else None
    # Energiamärgis: uusim registrisse kantud märgis
    märgised = []
    for m in energia or []:
        if m.get("energyClass") and "KANTUD" in str(m.get("documentStatusCode", "")).upper():
            try:
                kp = datetime.fromisoformat(str(m.get("documentDate"))[:10]).date()
            except ValueError:
                kp = None
            märgised.append((kp or date.min, m["energyClass"]))
    for m in _list(e, "ehitiseEnergiamargised", "energiamargis"):
        klass = next((v for k, v in m.items() if "klass" in k.lower() and isinstance(v, str) and len(v.strip()) == 1), None)
        if klass:
            märgised.append((date.min, klass))
    if märgised:
        kp, klass = max(märgised)
        ehitis.energiaklass, ehitis.energiamargise_kp = klass.strip().upper(), (kp if kp != date.min else None)
    return ehitis


# --------------------------------------------------------------------------- dokumentidest ehitusaasta
_KEHTETU = ("KEELDUTUD", "KEHTETU", "TAGASI", "MENETLUSES", "ESITATUD", "KOOSTAMISEL")


def _dok_kp(d: dict) -> date | None:
    s = str(d.get("date") or d.get("documentDate") or "")
    if not s:
        return None
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        if dt.tzinfo:  # Eesti aeg: 31.12 kl 22:00 UTC on juba uus aasta
            from zoneinfo import ZoneInfo
            dt = dt.astimezone(ZoneInfo("Europe/Tallinn"))
        return dt.date()
    except ValueError:
        return None


def _kehtiv(d: dict) -> bool:
    olek = str(d.get("documentState") or d.get("documentStatusCode") or "").upper()
    return not any(x in olek for x in _KEHTETU)


def ehitusaasta_dokumentidest(dokumendid: list[dict], esmane_kasutus: int | None
                              ) -> tuple[int | None, str | None, int | None]:
    """Tagastab (ehitusaasta, allika kirjeldus, rekonstrueerimise aasta).

    Järjekord: 1) kasutusluba/kasutusteatis ehitise püstitamisel (varaseim);
               2) ehitusluba ehitise püstitamiseks (varaseim);
               3) EHR-i esmase kasutuselevõtu aasta.
    Täpsustuseta „Kasutusluba“/„Kasutusteatis“ loetakse püstitamise omaks ainult siis, kui see ei ole
    esmasest kasutuselevõtust üle 3 aasta hilisem (muidu on see ümberehituse või muu töö luba).
    Rekonstrueerimise/ümberehituse kasutusload ehitusaastat ei muuda.
    """
    kasutus_püst, ehitusluba_püst, rekon, üldised = [], [], [], []
    for d in dokumendid or []:
        liik = str(d.get("documentType") or "").lower().strip()
        kp = _dok_kp(d)
        if not kp or not _kehtiv(d) or "taotlus" in liik:
            continue
        on_kasutus = liik.startswith("kasutusluba") or liik.startswith("kasutusteatis")
        if on_kasutus and "püstitamisel" in liik:
            kasutus_püst.append((kp, d))
        elif on_kasutus and any(x in liik for x in ("rekonstrueerimisel", "ümberehitamisel", "laiendamisel")):
            rekon.append(kp.year)
        elif on_kasutus and liik in ("kasutusluba", "kasutusteatis"):
            üldised.append((kp, d))
        elif liik.startswith("ehitusluba") and "püstitamiseks" in liik:
            ehitusluba_püst.append((kp, d))
    # Täpsustuseta kasutusluba/-teatis: püstitamise oma ainult siis, kui see ei ole teadaolevast
    # ehitusajast (püstitamise kasutusluba või esmane kasutuselevõtt) üle 3 aasta hilisem
    alus = min(kasutus_püst, key=lambda x: x[0])[0].year if kasutus_püst else esmane_kasutus
    for kp, d in üldised:
        if alus is None or kp.year <= alus + 3:
            kasutus_püst.append((kp, d))
        else:
            rekon.append(kp.year)
    rek = max(rekon) if rekon else None
    if kasutus_püst:
        kp, d = min(kasutus_püst, key=lambda x: x[0])
        return kp.year, f"{d.get('documentType')} nr {d.get('documentNumber')} ({kp:%d.%m.%Y})", rek
    if ehitusluba_püst:
        kp, d = min(ehitusluba_püst, key=lambda x: x[0])
        return kp.year, f"{d.get('documentType')} nr {d.get('documentNumber')} ({kp:%d.%m.%Y})", rek
    if esmane_kasutus:
        return esmane_kasutus, "esmase kasutuselevõtu aasta", rek
    return None, None, rek


class EhrApi:
    def __init__(self, klient: Klient, s):
        self.k = klient
        self.url = s.get_path("liidesed.ehr_url", "https://livekluster.ehr.ee/api")

    def ehitis(self, ehr_kood: str) -> Ehitis | None:
        kood = re.sub(r"\D", "", str(ehr_kood).split("-")[0])
        andmed = self.k.json(f"{self.url}/building/v3/buildingData", params={"ehr_code": kood})
        try:
            energia = self.k.json(f"{self.url}/document/v1/document/building/{kood}/buildingRelatedEnergyCertificates")
        except ConnectionError:
            energia = []
        try:
            dokumendid = self.k.json(f"{self.url}/document/v1/document/building/{kood}")
        except ConnectionError:
            dokumendid = []
        e = parsi(andmed, energia if isinstance(energia, list) else [])
        if e:
            rakenda_dokumendid(e, dokumendid if isinstance(dokumendid, list) else [])
        return e


def rakenda_dokumendid(e: "Ehitis", dokumendid: list[dict]) -> None:
    aasta, allikas, rek = ehitusaasta_dokumentidest(dokumendid, e.esmane_kasutus)
    if aasta:
        e.ehitusaasta, e.ehitusaasta_allikas = aasta, allikas
    e.rekonstrueeritud = rek if (rek and (not e.ehitusaasta or rek > e.ehitusaasta)) else None


def rikasta(o: Objekt, e: Ehitis, osa: Hooneosa | None, kuupäev: date | None = None) -> list[str]:
    """Kannab EHR-i andmed objektile. Käsitsi antud väärtused jäävad alles. Tagastab hoiatused."""
    src = "Ehitisregister"
    hoiatused = []
    kuupäev = kuupäev or date.today()
    o.maara("ehr_kood", e.ehr_kood, src)
    o.maara("ehitusaasta", e.ehitusaasta, f"{src}: {e.ehitusaasta_allikas}" if e.ehitusaasta_allikas else src)
    if e.rekonstrueeritud:
        o.maara("rekonstrueeritud", e.rekonstrueeritud, src)
        hoiatused.append(f"Hoonel on hilisem ({e.rekonstrueeritud}) rekonstrueerimise/ümberehituse või muu töö "
                         "kasutusluba/-teatis – vaata EHR-ist, mida tehti, ja arvesta seda seisukorra hindamisel.")
    o.maara("korruseid", e.korruseid, src)
    o.maara("materjal", e.materjal, src)
    o.maara("lift", e.lift, src)
    o.maara("ehitise_otstarve", e.otstarve, src)
    if e.katastritunnused:
        o.maara("katastritunnus", e.katastritunnused[0], src)
    if e.energiaklass:
        vanus = (kuupäev - e.energiamargise_kp).days / 365.25 if e.energiamargise_kp else None
        if vanus is not None and vanus > 10:
            hoiatused.append(f"Energiamärgis ({e.energiaklass}, {e.energiamargise_kp:%Y}) on vanem kui 10 aastat – "
                             "ei kasutatud.")
        else:
            o.maara("energiaklass", e.energiaklass, src)

    if osa is not None:
        o.maara("pind_m2", osa.pind_m2, f"{src} ({osa.liik} {osa.tahis})")
        o.maara("tube", osa.tube, src)
        o.maara("korrus", osa.korrus, src)
        o.maara("hooneosa", f"{osa.liik} {osa.tahis} ({osa.ehr_kood})", src)
    elif o.tyyp.value == "korter":
        hoiatused.append("Korterit ei leitud ehitisregistri hooneosade hulgast – kontrolli korteri numbrit "
                         "või sisesta pind käsitsi.")
    else:
        # Terve hoone: eramu/ärihoone. Eramu puhul eluruumide pind, muidu suletud netopind.
        pind = (e.eluruumide_pind if o.tyyp.value == "eramu" and e.eluruumide_pind else None) or e.suletud_netopind
        alus = "eluruumide pind" if pind and pind == e.eluruumide_pind else "suletud netopind"
        o.maara("pind_m2", pind, f"{src} ({alus})")
        if o.tyyp.value == "eramu" and (e.eluruume > 1):
            hoiatused.append(f"Hoones on {e.eluruume} eluruumi – kui hinnatakse ühte neist (nt ridaelamuboks), "
                             "anna hooneosa number.")
    return hoiatused
