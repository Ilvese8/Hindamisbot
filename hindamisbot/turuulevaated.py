"""Infopank: avalike turuülevaadete näitajad (andmed/turuulevaated.csv).

Annab hinnangule turu konteksti (piirkonna hinnatase, värskeimad kuuülevaated, ärikinnisvara üürid ja
tootlused) ning teeb usutavuskontrolli: kui korteri hinnang €/m² erineb piirkonna indekseeritud
mediaanist rohkem kui lubatud, lisatakse hoiatus.
"""
from __future__ import annotations

import csv
import re
from dataclasses import dataclass, field
from pathlib import Path

LUBATUD_KÕRVALEKALLE = 0.25
MIN_TEHINGUID = 10

_SILDID = {
    "korter_mediaan": ("Korterite mediaanhind {p} ({per})", "Apartment median price {p} ({per})"),
    "korter_tehinguid": ("Korteritehinguid {p} ({per})", "Apartment transactions {p} ({per})"),
    "korter_kuu": ("Korterite mediaanhind {p}, {per}", "Apartment median price {p}, {per}"),
    "korter_kuu_kesk": ("Korterite keskmine hind {p}, {per}", "Apartment average price {p}, {per}"),
    "pindi": ("Pindi indeks (suuremad linnad), {per}", "Pindi index (larger towns), {per}"),
    "eramu_mediaan": ("Eramu tehingu mediaanhind {p} ({per})", "House transaction median {p} ({per})"),
    "elamumaa": ("Elamumaa mediaanhind {p} ({per})", "Residential land median {p} ({per})"),
    "haritav": ("Haritava maa mediaanhind {p} ({per})", "Arable land median {p} ({per})"),
    "mets": ("Metsamaa mediaanhind {p} ({per})", "Forest land median {p} ({per})"),
    "indeks": ("Korteriomandite hinnaindeksi muutus aastaga ({per})", "Apartment price index, year on year ({per})"),
    "viide": ("Piirkonna võrdlustase täna (indekseeritud)", "Local reference level today (indexed)"),
    "ari": ("{seg}: {n} ({p}, {per})", "{seg}: {n} ({p}, {per})"),
}
_ARI_NÄITAJAD = {"vakants": ("vakants", "vacancy"), "vakants_kokku": ("vakants", "vacancy"),
                 "üür": ("üür", "rent"), "tootlus": ("tootlus", "yield"), "prime_tootlus": ("prime-tootlus", "prime yield")}


def _n(s: str) -> str:
    s = (s or "").lower().strip()
    s = re.sub(r" (linnaosa|asum)$", "", s)
    return s


def _sama(a: str, b: str) -> bool:
    a, b = _n(a), _n(b)
    return bool(a and b) and (a == b or (a.startswith(b) and len(a) - len(b) <= 1)
                              or (b.startswith(a) and len(b) - len(a) <= 1))


_ROOMA = {"I": 1, "II": 2, "III": 3, "IV": 4}


def _per_võti(r) -> tuple:
    a, _, q = r["periood"].partition("-")
    return int(a), _ROOMA.get(q, 0)


def _arv(v: str):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _eur(v: float) -> str:
    return f"{v:,.0f}".replace(",", " ")


@dataclass
class Rida:
    silt: str
    väärtus: str
    allikas: str
    url: str = ""


@dataclass
class TuruKontekst:
    read: list = field(default_factory=list)
    viide_eur_m2: float | None = None
    viide_piirkond: str | None = None
    kõrvalekalle: float | None = None
    hoiatus: str | None = None

    @property
    def tyhi(self) -> bool:
        return not self.read


class Turuulevaated:
    def __init__(self, tee: Path):
        self.read: list[dict] = []
        if tee and Path(tee).exists():
            with open(tee, encoding="utf-8") as f:
                self.read = list(csv.DictReader(f))

    @property
    def olemas(self) -> bool:
        return bool(self.read)

    # --- päringud
    def _leia(self, segment, näitaja, piirkond, tase=None, ülem=None, allikas=None):
        return [r for r in self.read if r["segment"] == segment and r["näitaja"] == näitaja
                and _sama(r["piirkond"], piirkond) and (tase is None or r["tase"] == tase)
                and (ülem is None or _sama(r["ülem"], ülem) or not r["ülem"])
                and (allikas is None or r["allikas"] == allikas)]

    def _maru(self, segment, näitaja, kandidaadid):
        """Esimene sobiv Maa- ja Ruumiameti aastaülevaate rida kõige täpsemast piirkonnast."""
        for tase, nimi, ülem in kandidaadid:
            if not nimi:
                continue
            r = self._leia(segment, näitaja, nimi, tase, ülem, "Maa- ja Ruumiamet")
            if r:
                return r[0]
        return None

    def indeksi_tegur(self) -> tuple[float, str] | None:
        """Korteriomandite indeksi värskeim väärtus / aastaülevaate aasta keskmine."""
        ind = [r for r in self.read if r["näitaja"] == "hinnaindeks" and r["segment"] == "korter"]
        if not ind:
            return None
        aasta = next((r["periood"] for r in self.read if r["allikas"] == "Maa- ja Ruumiamet"
                      and r["näitaja"] == "mediaan_eur_m2" and r["segment"] == "korter"), None)
        baas = [float(r["väärtus"]) for r in ind if aasta and r["periood"].startswith(aasta + "-")]
        viimane = max(ind, key=_per_võti)
        if not baas:
            return None
        return float(viimane["väärtus"]) / (sum(baas) / len(baas)), viimane["periood"]

    def _aasta_muutus(self):
        ind = sorted([r for r in self.read if r["näitaja"] == "hinnaindeks" and r["segment"] == "korter"],
                     key=_per_võti)
        if len(ind) < 5:
            return None
        v, per = ind[-1], ind[-1]["periood"]
        a, q = per.split("-")
        eelmine = next((r for r in ind if r["periood"] == f"{int(a) - 1}-{q}"), None)
        if not eelmine:
            return None
        return float(v["väärtus"]) / float(eelmine["väärtus"]) - 1, per, v

    # --- kontekst
    def kontekst(self, o, eur_m2: float | None = None, keel: str = "et") -> TuruKontekst:
        k = TuruKontekst()
        if not self.olemas or o.tyyp is None:
            return k
        L = (lambda võti, **kw: _SILDID[võti][1 if keel == "en" else 0].format(**kw))
        asum = (o.allikad or {}).get("asum")
        ay = o.asustusyksus or ""
        linnaosa = ay if ay.endswith("linnaosa") else None
        kand = [("asum", asum, _n(linnaosa) if linnaosa else None),
                ("linnaosa", asum, o.omavalitsus),
                ("linnaosa", linnaosa, o.omavalitsus),
                ("asula", ay if not linnaosa else None, None),
                ("asula", o.omavalitsus, None),
                ("omavalitsus", o.omavalitsus, None),
                ("maakond", o.maakond, None),
                ("riik", "Eesti", None)]

        def lähe(r):
            return f"{r['allikas']}, {r['väljaanne']}"

        t = o.tyyp.value
        TASE = {"asum": ("asum", "district"), "linnaosa": ("linnaosa", "city district")}

        def nimi_tasemega(r):
            lisa = TASE.get(r["tase"])
            return f"{r['piirkond']} {lisa[1 if keel == 'en' else 0]}" if lisa else r["piirkond"]

        if t in ("korter", "aripind"):
            nähtud = set()
            for tase, nimi, ülem in kand:
                if not nimi:
                    continue
                r = self._leia("korter", "mediaan_eur_m2", nimi, tase, ülem, "Maa- ja Ruumiamet")
                if not r or (r[0]["tase"], r[0]["piirkond"], r[0]["ülem"]) in nähtud:
                    continue
                r = r[0]
                nähtud.add((r["tase"], r["piirkond"], r["ülem"]))
                n = self._leia("korter", "tehinguid", r["piirkond"], r["tase"], r["ülem"] or None, "Maa- ja Ruumiamet")
                arv = int(float(n[0]["väärtus"])) if n else 0
                if t == "korter" or tase in ("asula", "omavalitsus", "maakond"):
                    k.read.append(Rida(L("korter_mediaan", p=nimi_tasemega(r), per=r["periood"]),
                                       f"{_eur(float(r['väärtus']))} €/m²" + (f" · {arv} tk" if keel == "et" else
                                                                             f" · {arv} deals"), lähe(r), r["url"]))
                if t == "korter" and k.viide_eur_m2 is None and arv >= MIN_TEHINGUID:
                    tegur = self.indeksi_tegur()
                    if tegur:
                        k.viide_eur_m2 = float(r["väärtus"]) * tegur[0]
                        k.viide_piirkond = f"{nimi_tasemega(r)} {r['periood']} × {tegur[0]:.3f} ({tegur[1]})"
                if len(k.read) >= 3:
                    break
            # Värskeimad kinnisvarafirmade kuuülevaated sama asula kohta
            for nimi in (o.omavalitsus, ay):
                if not nimi:
                    continue
                kuu = [r for r in self.read if r["allikas"] != "Maa- ja Ruumiamet" and r["segment"] == "korter"
                       and r["näitaja"] in ("mediaan_eur_m2", "keskmine_eur_m2") and _sama(r["piirkond"], nimi)]
                viimased = {}
                for r in sorted(kuu, key=lambda r: r["periood"], reverse=True):
                    viimased.setdefault((r["allikas"], r["näitaja"]), r)
                for r in viimased.values():
                    võti = "korter_kuu" if r["näitaja"] == "mediaan_eur_m2" else "korter_kuu_kesk"
                    k.read.append(Rida(L(võti, p=r["piirkond"], per=r["periood"]),
                                       f"{_eur(float(r['väärtus']))} €/m²" + (f" ({r['märkus']})" if r["märkus"] else ""),
                                       lähe(r), r["url"]))
                if viimased:
                    break
            pindi = [r for r in self.read if r["allikas"] == "Pindi Kinnisvara"]
            if pindi and t == "korter":
                r = max(pindi, key=lambda r: r["periood"])
                k.read.append(Rida(L("pindi", per=r["periood"]), f"{_eur(float(r['väärtus']))} €/m²", lähe(r), r["url"]))
            m = self._aasta_muutus()
            if m:
                k.read.append(Rida(L("indeks", per=m[1]), f"{m[0]:+.1%}".replace(".", ","), lähe(m[2]), m[2]["url"]))
        if t == "eramu":
            for tase, nimi, ülem in kand:
                r = nimi and self._leia("eramu", "tehingu_mediaan", nimi, tase, ülem, "Maa- ja Ruumiamet")
                if r:
                    r = r[0]
                    k.read.append(Rida(L("eramu_mediaan", p=r["piirkond"], per=r["periood"]),
                                       f"{_eur(float(r['väärtus']))} €", lähe(r), r["url"]))
                    if len(k.read) >= 2:
                        break
        if t in ("maa", "eramu"):
            siht = (o.sihtotstarve or o.sihtotstarbed or "").lower()
            if "maatulundus" in siht:
                for seg, võti in (("haritav maa", "haritav"), ("metsamaa", "mets")):
                    r = self._maru(seg, "mediaan_eur_ha", [("maakond", o.maakond, None), ("riik", "Eesti", None)])
                    if r:
                        k.read.append(Rida(L(võti, p=r["piirkond"], per=r["periood"]),
                                           f"{_eur(float(r['väärtus']))} €/ha", lähe(r), r["url"]))
            else:
                for tase, nimi, ülem in kand:
                    r = nimi and self._leia("elamumaa", "mediaan_eur_m2", nimi, tase, ülem, "Maa- ja Ruumiamet")
                    if r:
                        r = r[0]
                        k.read.append(Rida(L("elamumaa", p=r["piirkond"], per=r["periood"]),
                                           f"{float(r['väärtus']):.1f} €/m²".replace(".", ","), lähe(r), r["url"]))
                        break
        if t == "aripind":
            linn = o.omavalitsus or ""
            for r in self.read:
                if r["näitaja"] in _ARI_NÄITAJAD and r["allikas"] != "Maa- ja Ruumiamet" and _sama(r["piirkond"], linn):
                    n = _ARI_NÄITAJAD[r["näitaja"]][1 if keel == "en" else 0]
                    k.read.append(Rida(L("ari", seg=r["segment"], n=n, p=r["piirkond"], per=r["periood"]),
                                       f"{r['väärtus'].replace('.', ',')} {r['ühik']}", lähe(r), r["url"]))

        if k.viide_eur_m2:
            k.read.insert(0, Rida(L("viide"), f"{_eur(k.viide_eur_m2)} €/m²", k.viide_piirkond))
            if eur_m2:
                k.kõrvalekalle = eur_m2 / k.viide_eur_m2 - 1
                if abs(k.kõrvalekalle) > LUBATUD_KÕRVALEKALLE:
                    k.hoiatus = (f"Turuülevaadete kontroll: hinnang {_eur(eur_m2)} €/m² erineb piirkonna "
                                 f"võrdlustasemest {_eur(k.viide_eur_m2)} €/m² {k.kõrvalekalle:+.0%} – kontrolli "
                                 f"seisukorda, ehitusaastat ja võrdlusgruppi.")
        return k
