"""Maa- ja Ruumiameti kinnisvara hinnastatistika otse päringukeskkonna liidesest (statistika.kataster.ee).

Sama avalik liides, mida kasutab veebileht https://statistika.kataster.ee/kinnisvara/. Liides ei ole
ametlikult dokumenteeritud ja võib muutuda – siis langeb bot tagasi kohalikule failile.
Andmed on koondatud; alla 5 tehinguga lahtrid on peidetud (maakatastriseadus § 6).
Viide andmetele: "Maa- ja Ruumiamet, tehingute andmebaas".

Kasutatud statistika liigid:
  korterid_ehitusaasta   – korteriomandid hoone esmakasutusaasta järgi (€/m² üldpinnast)
  korteriomand           – korteriomandid pinnavahemiku järgi
  eluhooned_ehitusaasta  – eluhoonetega hoonestatud elamumaa hoone esmakasutusaasta järgi (€/m² hoone pinnast)
  ehitise_liik           – sama hoone liigi järgi (Elamu, Suvila …)
  hoonestamata_maa       – hoonestamata maa sihtotstarbe järgi (€/m² krundist)
  hoonestatud_maa        – hoonestatud maa sihtotstarbe järgi (€/m² krundist)
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date

from .hinnastatistika import StatTulemus, kvartal_kuupaevast
from .http import Klient

# Objektitüüp -> päringud eelistuse järjekorras: (statistikaLiik, rea valiku viis, pinna alus)
PARINGUD = {
    "korter": [("korterid_ehitusaasta", "ehitusaasta", "üldpind"), ("korteriomand", "pind", "üldpind")],
    "eramu": [("eluhooned_ehitusaasta", "ehitusaasta", "hoone pind"), ("ehitise_liik", "elamu", "hoone pind")],
    "maa": [("hoonestamata_maa", "sihtotstarve", "krunt")],
    "aripind": [("hoonestatud_maa", "sihtotstarve", "krunt")],
}


def _n(s) -> str:
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode().lower()
    return re.sub(r"\s+", " ", s).strip()


def _f(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def vahemik(nimi: str) -> tuple[float | None, float | None]:
    """'41-54,99' -> (41, 54.99); '<1939' -> (None, 1939); '2026 ...' / '100+' -> (2026, None)."""
    s = str(nimi).replace(",", ".").replace(" ", "")
    nums = [float(x) for x in re.findall(r"\d+(?:\.\d+)?", s)]
    if not nums:
        return None, None
    if s.startswith("<"):
        return None, nums[0]
    if s.startswith(">") or "..." in s or s.endswith("+") or len(nums) == 1:
        return nums[0], None
    return nums[0], nums[1]


def _sisaldab(nimi: str, x: float) -> bool:
    a, b = vahemik(nimi)
    if a is None and b is None:
        return False
    return (a is None or x >= a) and (b is None or x <= b + 0.999)


@dataclass
class Geo:
    mk: str | None = None
    ov: str | None = None
    asum: str | None = None
    nimed: dict = field(default_factory=dict)


class KatasterStatistika:
    """Annab sama liidese nagu failipõhine Hinnastatistika (meetod `leia`)."""

    def __init__(self, klient: Klient, s):
        self.k = klient
        self.url = s.get_path("liidesed.statistika_url", "https://statistika.kataster.ee/api/tehingud")
        self.ost_myyk = s.get_path("statistika.ainult_ost_myyk", True)
        self.loige = s.get_path("statistika.loikeprotsent", 0)
        self.kuid = s.get_path("statistika.periood_kuud", 12)
        self.max_kuid = s.get_path("statistika.max_periood_kuud", 24)
        self.logi: list[str] = []
        self._ov: dict[str, list] = {}

    olemas = True

    # ---------------------------------------------------------------- piirkonnad
    def _get(self, tee: str, **params):
        return self.k.json(f"{self.url}/{tee}", params=params)

    def geo(self, maakond, omavalitsus, asustusyksus) -> Geo:
        g = Geo()
        if not maakond and not omavalitsus:
            return g
        mkd = self._get("filter/maakonnad")
        if maakond:
            m = next((x for x in mkd if _n(x["mkNimi"]) == _n(maakond)
                      or _n(x["mkNimi"]).startswith(_n(maakond).replace(" maakond", ""))), None)
            if m:
                g.mk, g.nimed["mk"] = m["mkKood"], m["mkNimi"]
        kandidaadid = [g.mk] if g.mk else [x["mkKood"] for x in mkd]
        ov_nimi = _n(omavalitsus).replace(" linn", "") if omavalitsus else None
        for mk in kandidaadid:
            if mk not in self._ov:
                self._ov[mk] = self._get("filter/omavalitsused", mkKood=mk)
            ovs = self._ov[mk]
            if ov_nimi:
                o = next((x for x in ovs if not x.get("parentOvKood") and
                          _n(x["ovNimi"]).replace(" linn", "") == ov_nimi), None)
                if o:
                    g.mk, g.ov, g.nimed["ov"] = mk, o["ovKood"], o["ovNimi"]
                    g.nimed.setdefault("mk", o.get("mkNimi"))
            if g.ov and asustusyksus:
                a = _n(asustusyksus)
                # Linnaosad (nt Mustamäe linnaosa) on ov-loendis ema-linna all, päringus lähevad asumKood-i
                lo = next((x for x in ovs if str(x.get("parentOvKood")) == str(g.ov) and
                           (_n(x["ovNimi"]) == a or _n(x["ovNimi"]).startswith(a.replace(" linnaosa", "")))), None)
                if lo:
                    g.asum, g.nimed["asum"] = lo["ovKood"], lo["ovNimi"]
                else:
                    asumid = self._get("filter/asumid", ovKood=g.ov)
                    x = next((x for x in asumid if _n(x["asumNimi"]) == a), None) or \
                        next((x for x in asumid if _n(x["asumNimi"]).split(" ")[0] == a.split(" ")[0]), None)
                    if x:
                        g.asum, g.nimed["asum"] = x["asumKood"], x["asumNimi"]
            if g.ov:
                break
        return g

    # ---------------------------------------------------------------- hinnad
    def _hinnad(self, liik: str, g: Geo, tase: str, alates: date, kuni: date) -> list[dict]:
        p = {"statistikaLiik": liik, "aastast": alates.year, "kuust": alates.month,
             "aastani": kuni.year, "kuuni": kuni.month, "mkKood": g.mk or "",
             "ovKood": g.ov if tase in ("omavalitsus",) else "",
             "asumKood": g.asum if tase == "asustusyksus" else "",
             "piirkondId": 0, "tehinguLiik": "OSTM" if self.ost_myyk else "",
             "loikeAlt": self.loige, "loikeYlevalt": self.loige}
        if tase == "maakond":
            p["ovKood"] = ""
        return self._get("hinnad", **p) or []

    @staticmethod
    def _vali_rida(read: list[dict], viis: str, pind, ehitusaasta, sihtotstarve):
        read = [r for r in read if not r.get("peidetud") and _f(r.get("yhikuHindMed"))]
        if viis == "ehitusaasta":
            return next((r for r in read if ehitusaasta and _sisaldab(r["nimi"], ehitusaasta)), None)
        if viis == "pind":
            return next((r for r in read if pind and _sisaldab(r["nimi"], pind)), None)
        if viis == "elamu":
            return next((r for r in read if _n(r["nimi"]) == "elamu"), None)
        if viis == "sihtotstarve":
            soov = _n(sihtotstarve or "elamumaa")
            return next((r for r in read if _n(r["nimi"]) == soov), None) or \
                next((r for r in read if soov.startswith(_n(r["nimi"])[:5])), None)
        return None

    def leia(self, tyyp, maakond=None, omavalitsus=None, asustusyksus=None, pind=None, sihtotstarve=None,
             kuni_kvartal=None, max_kvartaleid=8, min_tehinguid=5, ehitusaasta=None,
             kuupäev: date | None = None) -> StatTulemus | None:
        kuupäev = kuupäev or date.today()
        # Jooksev kuu on poolik – kasuta perioodi kuni eelmise kuu lõpuni
        kuni = date(kuupäev.year, kuupäev.month, 1)
        kuni = date(kuni.year - (kuni.month == 1), 12 if kuni.month == 1 else kuni.month - 1, 1)
        g = self.geo(maakond, omavalitsus, asustusyksus)
        if not (g.mk or g.ov):
            self.logi.append("Statistika: piirkonda ei tuvastatud.")
            return None
        tasemed = [t for t, v in (("asustusyksus", g.asum), ("omavalitsus", g.ov), ("maakond", g.mk)) if v]
        for tase in tasemed:
            for kuid in sorted({self.kuid, self.max_kuid}):
                alg_kuu = kuni.year * 12 + kuni.month - 1 - (kuid - 1)
                alates = date(alg_kuu // 12, alg_kuu % 12 + 1, 1)
                for liik, viis, alus in PARINGUD.get(tyyp, []):
                    if viis == "ehitusaasta" and not ehitusaasta:
                        continue
                    read = self._hinnad(liik, g, tase, alates, kuni)
                    r = self._vali_rida(read, viis, pind, ehitusaasta, sihtotstarve)
                    if not r or int(r["arv"]) < min_tehinguid:
                        continue
                    kesk = alg_kuu + (kuid - 1) / 2
                    kesk_kv = (int(kesk // 12), int((kesk % 12) // 3) + 1)
                    nimi = g.nimed.get({"asustusyksus": "asum", "omavalitsus": "ov", "maakond": "mk"}[tase])
                    self.logi.append(f"Statistika: {liik} / {r['nimi']} / {nimi} / {alates:%m.%Y}–{kuni:%m.%Y}")
                    return StatTulemus(
                        eur_m2=_f(r["yhikuHindMed"]), tehinguid=int(r["arv"]), tase=tase,
                        perioodid=[f"{alates:%m.%Y}–{kuni:%m.%Y}"],
                        min_eur_m2=_f(r.get("yhikuHindMin")), max_eur_m2=_f(r.get("yhikuHindMaks")),
                        pinna_alus=alus, allikas="api",
                        read=[{**r, "_kv": kesk_kv, "liik": liik, "piirkond": nimi,
                               "keskmine_eur_m2": _f(r.get("yhikuHindKeskm")),
                               "standardhälve": _f(r.get("yhikuHindHalve"))}],
                    )
        return None


class StatAllikas:
    """Proovib esmalt liidest, siis kohalikku faili."""

    def __init__(self, api: "KatasterStatistika | None", fail):
        self.api, self.fail = api, fail
        self.hoiatused: list[str] = []

    @property
    def olemas(self) -> bool:
        return self.api is not None or self.fail.olemas

    def leia(self, *a, **kw):
        if self.api is not None:
            try:
                r = self.api.leia(*a, **kw)
                if r:
                    return r
            except ConnectionError as e:
                self.hoiatused.append(f"Statistika liides pole kättesaadav ({e}) – kasutan kohalikku faili.")
        return self.fail.leia(*a, **kw) if self.fail.olemas else None
