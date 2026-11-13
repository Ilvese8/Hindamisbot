"""Ehitisregistri (EHR) andmed avaandmete väljavõttest.

EHR-i avaandmeid saab tellida/alla laadida ehitisregistri keskkonnast või avaandmete portaalist.
Salvesta väljavõte CSV-na ja määra tee seadistuste failis (andmefailid.ehitisregister).
"""
from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

from ..mudel import Objekt
from .tabel import arv, loe, vastenda

ALIASED = {
    "ehr_kood": ["ehr kood", "ehitise kood", "ehitis_ehr_kood", "ehrcode"],
    "aadress": ["taisaadress", "ehitise aadress", "address"],
    "esmane_kasutus": ["esmane kasutus", "kasutusele votu aasta", "ehitusaasta", "esmase kasutuselevotu aasta"],
    "korruseid": ["maapealsete korruste arv", "korruste arv", "maapealseid korruseid"],
    "netopind": ["suletud netopind", "netopind", "uldpind", "koetav pind"],
    "materjal": ["kandekonstruktsiooni materjal", "kandvate seinte materjal", "valisseina materjal"],
    "energiaklass": ["energiamargise klass", "energiatohususklass", "energiaklass"],
    "kasutamise_otstarve": ["kasutamise otstarve", "otstarve"],
}

_MATERJAL = {"paneel": ["paneel", "monteeritav raudbetoon"], "kivi": ["kivi", "tellis", "betoon", "plokk", "silikaat"],
            "puit": ["puit", "palk"]}


class Ehitisregister:
    def __init__(self, tee: Path):
        self.df = vastenda(loe(tee), ALIASED) if tee.exists() else pd.DataFrame()

    @property
    def olemas(self) -> bool:
        return not self.df.empty

    def leia(self, ehr_kood: str | None = None, aadress: str | None = None) -> dict | None:
        if not self.olemas:
            return None
        if ehr_kood and "ehr_kood" in self.df:
            r = self.df[self.df["ehr_kood"].astype(str).str.strip() == str(ehr_kood).strip()]
            if len(r):
                return r.iloc[0].to_dict()
        if aadress and "aadress" in self.df:
            # Hoone aadress: esimene osa enne koma, korteri number ("-15") eemaldatud
            hoone = re.sub(r"-\s*\d+\w*$", "", aadress.split(",")[0].strip()).lower()
            muster = re.compile(rf"(^|,\s*){re.escape(hoone)}\s*$")
            r = self.df[self.df["aadress"].str.lower().map(lambda a: bool(muster.search(a.strip())))]
            if len(r) == 1:
                return r.iloc[0].to_dict()
        return None


def materjali_klass(tekst: str | None) -> str | None:
    if not tekst:
        return None
    t = tekst.lower()
    for klass, märksõnad in _MATERJAL.items():
        if any(m in t for m in märksõnad):
            return klass
    return "muu"


def rikasta(objekt: Objekt, kirje: dict) -> None:
    src = "Ehitisregister"
    aasta = arv(kirje.get("esmane_kasutus"))
    objekt.maara("ehitusaasta", int(aasta) if aasta else None, src)
    k = arv(kirje.get("korruseid"))
    objekt.maara("korruseid", int(k) if k else None, src)
    # Korteri puhul ei sobi hoone netopind korteri pinnaks
    if objekt.tyyp.value in ("eramu", "aripind"):
        objekt.maara("pind_m2", arv(kirje.get("netopind")), src)
    objekt.maara("materjal", materjali_klass(kirje.get("materjal")), src)
    ek = (kirje.get("energiaklass") or "").strip().upper()[:1] or None
    objekt.maara("energiaklass", ek, src)
