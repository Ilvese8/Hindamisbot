"""Hindaja kogutud võrdlusobjektid (CSV).

Fail täidetakse käsitsi: hindaja enda tehinguandmed (nt tehingute andmebaasi väljavõte, kui tal on
ligipääs), oma büroo tehingud või käsitsi üle vaadatud kuulutused. Bot ise portaale ei päri.

Veerud: aadress, lat, lon, tyyp, pind_m2, hind, kuupaev, allika_tyyp (tehing|pakkumine),
ehitusaasta, korrus, korruseid, seisukord, energiaklass, krundi_pind_m2, allikas, markus
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from .tabel import arv, loe, vastenda

ALIASED = {
    "kuupaev": ["kuupäev", "tehingu kuupaev", "date"],
    "allika_tyyp": ["allika tüüp", "liik", "tehing voi pakkumine"],
    "pind_m2": ["pind", "uldpind", "netopind"],
    "hind": ["hind eur", "tehinguhind", "pakkumishind"],
    "krundi_pind_m2": ["krundi pind", "krunt m2"],
    "markus": ["märkus", "markused"],
}


@dataclass
class Vordlusobjekt:
    aadress: str
    lat: float | None
    lon: float | None
    tyyp: str
    pind_m2: float | None
    hind: float
    kuupaev: date | None
    allika_tyyp: str
    ehitusaasta: int | None = None
    korrus: int | None = None
    korruseid: int | None = None
    seisukord: str | None = None
    energiaklass: str | None = None
    krundi_pind_m2: float | None = None
    allikas: str = ""
    markus: str = ""


def _kuupaev(s) -> date | None:
    s = str(s or "").strip()
    for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y", "%Y.%m.%d"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            pass
    return None


def _int(v):
    x = arv(v)
    return int(x) if x is not None else None


def lae(tee: Path) -> list[Vordlusobjekt]:
    if not tee.exists():
        return []
    df = vastenda(loe(tee), ALIASED)
    tulem = []
    for _, r in df.iterrows():
        hind = arv(r.get("hind"))
        if not hind:
            continue
        tulem.append(Vordlusobjekt(
            aadress=str(r.get("aadress", "")), lat=arv(r.get("lat")), lon=arv(r.get("lon")),
            tyyp=str(r.get("tyyp", "")).strip().lower(), pind_m2=arv(r.get("pind_m2")), hind=hind,
            kuupaev=_kuupaev(r.get("kuupaev")),
            allika_tyyp=(str(r.get("allika_tyyp", "tehing")).strip().lower() or "tehing"),
            ehitusaasta=_int(r.get("ehitusaasta")), korrus=_int(r.get("korrus")),
            korruseid=_int(r.get("korruseid")),
            seisukord=(str(r.get("seisukord", "")).strip().lower() or None),
            energiaklass=(str(r.get("energiaklass", "")).strip().upper()[:1] or None),
            krundi_pind_m2=arv(r.get("krundi_pind_m2")),
            allikas=str(r.get("allikas", "")), markus=str(r.get("markus", "")),
        ))
    return tulem
