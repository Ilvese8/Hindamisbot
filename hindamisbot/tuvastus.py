"""Objektitüübi automaatne tuvastamine avaandmetest.

Allikad (tähtsuse järjekorras):
  1. hooneosa liik ehitisregistris (eluruum → korter, mitteeluruum → äripind);
  2. ehitise kasutamise otstarve ehitisregistris (üksikelamu → eramu, kortermaja → korter, mitteeluhoone → äripind);
  3. aadressi vaste ilma ehitiseta + katastriüksus → maa.
Tulemus on ettepanek: kasutaja antud tüüp on alati ülimuslik.
"""
from __future__ import annotations

import re

from .mudel import ObjektiTyyp

ERAMU = re.compile(r"üksikelamu|suvila|aiamaja|kahe korteriga|paarismaja|taluelamu|ridaelamu|^elamu$", re.I)
KORTERMAJA = re.compile(r"kolme või enama korteriga|korterelamu|ühiselamu", re.I)


def tuvasta(*, inads_liik: str | None = None, otstarve: str | None = None, kaos_kood: str | None = None,
            osa_liik: str | None = None, osa_nr: str | None = None, eluruume: int = 0,
            on_katastriyksus: bool = False) -> tuple[ObjektiTyyp | None, str, list[str]]:
    """Tagastab (tüüp, põhjendus, hoiatused)."""
    hoiatused: list[str] = []
    ots = otstarve or ""
    elu_hoone = bool(KORTERMAJA.search(ots) or ERAMU.search(ots) or str(kaos_kood or "").startswith("11"))

    # 1. Hooneosa
    if osa_liik == "eluruum":
        if eluruume <= 1 and ERAMU.search(ots):
            return ObjektiTyyp.ERAMU, f"hooneosa {osa_nr} on eluruum hoones „{ots}“", hoiatused
        return ObjektiTyyp.KORTER, f"hooneosa {osa_nr} on eluruum (ehitisregister)", hoiatused
    if osa_liik == "mitteeluruum":
        return ObjektiTyyp.ARIPIND, f"hooneosa {osa_nr} on mitteeluruum (ehitisregister)", hoiatused
    if osa_nr and (KORTERMAJA.search(ots) or eluruume > 2):
        hoiatused.append(f"Hooneosa {osa_nr} ei leitud ehitisregistrist – eeldatud korterit.")
        return ObjektiTyyp.KORTER, f"aadressil on hooneosa number ja hoone on „{ots}“", hoiatused

    # 2. Terve ehitis
    if ots or kaos_kood:
        if KORTERMAJA.search(ots) or (str(kaos_kood or "").startswith("11") and eluruume > 2):
            hoiatused.append("Aadress on kortermaja – anna korteri number (nt „Ehitajate tee 35-55“), "
                             "et hinnata ühte korterit.")
            return ObjektiTyyp.KORTER, f"hoone on „{ots}“", hoiatused
        if ERAMU.search(ots) or (elu_hoone and eluruume <= 2):
            if re.search(r"ridaelamu", ots, re.I):
                hoiatused.append("Ridaelamu – kui boksid on eraldi korteriomandid, anna boksi number.")
            if re.search(r"suvila|aiamaja", ots, re.I):
                hoiatused.append("Suvila/aiamaja – turustatistika võrdleb eluhoonetega, kontrolli sobivust.")
            return ObjektiTyyp.ERAMU, f"hoone on „{ots}“", hoiatused
        return ObjektiTyyp.ARIPIND, f"hoone on mitteeluhoone „{ots}“", hoiatused

    # 3. Ehitiseta katastriüksus
    if on_katastriyksus or (inads_liik or "").upper() == "KATASTRIYKSUS":
        return ObjektiTyyp.MAA, "aadressil ei ole ehitist, leiti katastriüksus", hoiatused
    return None, "tüüpi ei õnnestunud tuvastada", ["Objektitüüpi ei õnnestunud tuvastada – anna see käsitsi."]
