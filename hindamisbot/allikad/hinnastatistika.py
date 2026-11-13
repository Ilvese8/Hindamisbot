"""Maa- ja Ruumiameti kinnisvara hinnastatistika ja hinnaindeks (avalikud koondandmed).

Hinnastatistika päringukeskkonnast saab tehingute koondnäitajaid piirkonna, objekti liigi,
pinnavahemiku ja perioodi kaupa. Laadi väljavõte alla (CSV/XLSX) ja määra tee seadistustes.
Üksiktehingute andmebaas on piiratud ligipääsuga – seda moodul ei eelda.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from .tabel import arv, loe, vastenda

ALIASED = {
    "periood": ["kvartal", "aasta kvartal", "ajavahemik", "period"],
    "maakond": ["maakond"],
    "omavalitsus": ["omavalitsus", "kov", "linn vald"],
    "asustusyksus": ["asustusuksus", "linnaosa", "asum", "kula"],
    "tyyp": ["objekti liik", "liik", "vara liik", "tehingu objekt"],
    "sihtotstarve": ["sihtotstarve", "maa sihtotstarve"],
    "pinnavahemik": ["pinnavahemik", "pind m2", "suurusvahemik"],
    "tehinguid": ["tehingute arv", "arv", "tehinguid"],
    "mediaan_eur_m2": ["mediaan eur m2", "mediaanhind eur m2", "pinnaühiku hind mediaan", "mediaan"],
    "keskmine_eur_m2": ["keskmine eur m2", "pinnauhiku hind keskmine", "keskmine"],
    "min_eur_m2": ["min eur m2", "pinnauhiku hind min", "min"],
    "max_eur_m2": ["max eur m2", "pinnauhiku hind max", "max"],
    "pinna_alus": ["pinna alus", "uhik"],
}

# Maa- ja Ruumiameti liiginimed -> boti objektitüüp
TYYBID = {
    "korter": "korter", "korteriomand": "korter", "korteriomandid": "korter",
    "eramu": "eramu", "hoonestatud elamumaa": "eramu", "elamu": "eramu", "hoonestatud maa": "eramu",
    "maa": "maa", "hoonestamata maa": "maa", "hoonestamata elamumaa": "maa", "elamumaa": "maa",
    "maatulundusmaa": "maa", "haritav maa": "maa", "metsamaa": "maa",
    "aripind": "aripind", "arimaa": "aripind", "hoonestatud arimaa": "aripind", "tootmismaa": "aripind",
}

_ROOMA = {"I": 1, "II": 2, "III": 3, "IV": 4}


def kvartal(tekst) -> tuple[int, int] | None:
    """'2026 III', '2026-Q3', '2026/3', 'III kv 2026', '2026' -> (2026, 3). Aasta puhul IV kvartal."""
    if tekst is None:
        return None
    s = str(tekst).strip().upper()
    m = re.search(r"(20\d\d|19\d\d)", s)
    if not m:
        return None
    aasta = int(m.group(1))
    rest = (s[:m.start()] + " " + s[m.end():]).strip()
    m2 = re.search(r"\b(IV|III|II|I)\b", rest)
    if m2:
        return aasta, _ROOMA[m2.group(1)]
    m3 = re.search(r"Q?([1-4])", rest)
    if m3:
        return aasta, int(m3.group(1))
    return aasta, 4


def kvartal_kuupaevast(d) -> tuple[int, int]:
    return d.year, (d.month - 1) // 3 + 1


def kvartaleid_vahel(a: tuple[int, int], b: tuple[int, int]) -> int:
    return (b[0] - a[0]) * 4 + (b[1] - a[1])


def pinnavahemik(tekst) -> tuple[float | None, float | None]:
    """'30-40,99' -> (30, 40.99); '>100' / '100+' -> (100, None); '<30' -> (None, 30)."""
    if tekst is None or str(tekst).strip() == "":
        return None, None
    s = str(tekst).replace(",", ".").replace(" ", "").replace("–", "-")
    nums = [float(x) for x in re.findall(r"\d+(?:\.\d+)?", s)]
    if not nums:
        return None, None
    if s.startswith(("<", "kuni")):
        return None, nums[0]
    if s.startswith(">") or s.endswith("+") or "üle" in s.lower():
        return nums[0], None
    return (nums[0], nums[1]) if len(nums) > 1 else (nums[0], nums[0])


def _norm_txt(s) -> str:
    return re.sub(r"\s+", " ", str(s or "").strip().lower())


@dataclass
class StatTulemus:
    eur_m2: float
    tehinguid: int
    tase: str                 # millise piirkonna tasemel leiti (asustusyksus/omavalitsus/maakond)
    perioodid: list
    min_eur_m2: float | None
    max_eur_m2: float | None
    pinna_alus: str
    read: list
    allikas: str = "fail"


class Hinnastatistika:
    def __init__(self, tee: Path):
        if not tee.exists():
            self.df = pd.DataFrame()
            return
        df = vastenda(loe(tee), ALIASED)
        df["_kv"] = df["periood"].map(kvartal) if "periood" in df else None
        df["_tyyp"] = df["tyyp"].map(lambda v: TYYBID.get(_norm_txt(v).replace("ä", "a"), _norm_txt(v))) \
            if "tyyp" in df else None
        vahemikud = df["pinnavahemik"].map(pinnavahemik) if "pinnavahemik" in df else [(None, None)] * len(df)
        df["_pmin"] = [v[0] for v in vahemikud]
        df["_pmax"] = [v[1] for v in vahemikud]
        for k in ("tehinguid", "mediaan_eur_m2", "keskmine_eur_m2", "min_eur_m2", "max_eur_m2"):
            df[k] = df[k].map(arv) if k in df else None
        for k in ("maakond", "omavalitsus", "asustusyksus", "sihtotstarve", "pinna_alus"):
            df[k] = df[k].map(_norm_txt) if k in df else ""
        self.df = df

    @property
    def olemas(self) -> bool:
        return not self.df.empty

    def leia(self, tyyp: str, maakond=None, omavalitsus=None, asustusyksus=None, pind=None,
             sihtotstarve=None, kuni_kvartal=None, max_kvartaleid=8, min_tehinguid=5,
             **_) -> StatTulemus | None:
        """Leiab kõige täpsema piirkonna, kus on piisavalt tehinguid; kaalutud mediaan €/m²."""
        if not self.olemas:
            return None
        df = self.df[self.df["_tyyp"] == tyyp]
        if sihtotstarve and (df["sihtotstarve"] != "").any():
            sobiv = df[df["sihtotstarve"].str.contains(_norm_txt(sihtotstarve), regex=False)]
            if len(sobiv):
                df = sobiv
        if pind is not None:
            mask = ((df["_pmin"].isna()) | (df["_pmin"] <= pind)) & ((df["_pmax"].isna()) | (df["_pmax"] >= pind))
            df = df[mask]
        if kuni_kvartal:
            df = df[df["_kv"].map(lambda k: k is not None and 0 <= kvartaleid_vahel(k, kuni_kvartal) < max_kvartaleid)]
        df = df[df["mediaan_eur_m2"].notna() | df["keskmine_eur_m2"].notna()]

        tasemed = [("asustusyksus", asustusyksus), ("omavalitsus", omavalitsus), ("maakond", maakond)]
        for i, (tase, väärtus) in enumerate(tasemed):
            if not väärtus:
                continue
            v = _norm_txt(väärtus)
            alam = df[df[tase] == v]
            # Laiem tase: alamtasandi veerud peavad olema tühjad (koondrida), kui need on olemas
            for madalam, _ in tasemed[:i]:
                if (alam[madalam] != "").any() and (alam[madalam] == "").any():
                    alam = alam[alam[madalam] == ""]
            if alam.empty:
                continue
            # Võta värskeimad kvartalid, kuni tehinguid on piisavalt
            alam = alam.sort_values("_kv", key=lambda s: s.map(lambda k: (k or (0, 0))), ascending=False)
            valitud, kokku = [], 0
            for _, r in alam.iterrows():
                valitud.append(r)
                kokku += int(r["tehinguid"] or 0)
                if kokku >= max(min_tehinguid, 1) * 2:
                    break
            if kokku < min_tehinguid:
                continue
            kaalud = [max(int(r["tehinguid"] or 1), 1) for r in valitud]
            hinnad = [r["mediaan_eur_m2"] if pd.notna(r["mediaan_eur_m2"]) else r["keskmine_eur_m2"] for r in valitud]
            eur_m2 = sum(h * k for h, k in zip(hinnad, kaalud)) / sum(kaalud)
            mins = [r["min_eur_m2"] for r in valitud if pd.notna(r["min_eur_m2"])]
            maxs = [r["max_eur_m2"] for r in valitud if pd.notna(r["max_eur_m2"])]
            return StatTulemus(
                eur_m2=eur_m2, tehinguid=kokku, tase=tase, allikas="fail",
                perioodid=[f"{r['_kv'][0]} Q{r['_kv'][1]}" for r in valitud if r["_kv"]],
                min_eur_m2=min(mins) if mins else None, max_eur_m2=max(maxs) if maxs else None,
                pinna_alus=valitud[0]["pinna_alus"] or "", read=[dict(r) for r in valitud],
            )
        return None


class Hinnaindeks:
    """Kvartaalne hinnaindeks (nt Maa- ja Ruumiameti kinnisvara/korteriomandite hinnaindeks)."""

    def __init__(self, tee: Path):
        self.indeks: dict[str, dict[tuple, float]] = {}
        if not tee.exists():
            return
        df = loe(tee)
        pveerg = next((c for c in df.columns if c in ("periood", "kvartal", "period")), df.columns[0])
        for c in df.columns:
            if c == pveerg:
                continue
            seeria = {}
            for p, v in zip(df[pveerg], df[c]):
                k, x = kvartal(p), arv(v)
                if k and x:
                    seeria[k] = x
            if seeria:
                self.indeks[c] = seeria

    def tegur(self, alates: tuple, kuni: tuple, seeria: str | None = None) -> float | None:
        """Kordaja hinna viimiseks perioodist `alates` perioodi `kuni`. Puuduva perioodi korral lähim varasem."""
        if not self.indeks:
            return None
        s = self.indeks.get(seeria) if seeria else None
        s = s or self.indeks.get("indeks") or next(iter(self.indeks.values()))

        def väärtus(k):
            sobivad = [p for p in s if p <= k]
            return s[max(sobivad)] if sobivad else None

        a, b = väärtus(alates), väärtus(kuni)
        return b / a if a and b else None
