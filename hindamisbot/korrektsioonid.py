"""Korrektsioonitegurid seadistustest. Kõik tegurid on suhtelised piirkonna 'tüüpobjekti' suhtes (=1.00)."""
from __future__ import annotations

from .mudel import Korrektsioon, Objekt


def _seisukord(s, objekt_seisukord):
    if not objekt_seisukord:
        return None
    t = s.get_path("korrektsioonid.seisukord", {}).get(objekt_seisukord.value if hasattr(objekt_seisukord, "value")
                                                         else str(objekt_seisukord))
    return t


def seisukorra_tegur(s, seisukord) -> float:
    return _seisukord(s, seisukord) or 1.0


def energiaklassi_tegur(s, klass) -> float:
    return s.get_path("korrektsioonid.energiaklass", {}).get((klass or "").upper(), 1.0) if klass else 1.0


def ehitusaasta_tegur(s, aasta) -> float:
    if not aasta:
        return 1.0
    tabel = {int(k): v for k, v in s.get_path("korrektsioonid.ehitusaasta", {}).items()}
    sobivad = [k for k in tabel if k <= aasta]
    return tabel[max(sobivad)] if sobivad else 1.0


def korruse_tegur(s, korrus, korruseid, lift=None) -> float:
    t = s.get_path("korrektsioonid.korrus", {})
    if korrus is None:
        return 1.0
    if korrus <= 1:
        return t.get("esimene", 1.0)
    ilma_liftita = (lift is False) or (lift is None and korruseid and korruseid <= 5)
    if korruseid and korrus == korruseid and ilma_liftita:
        return t.get("viimane_ilma_liftita", 1.0)
    return t.get("muu", 1.0)


def objekti_korrektsioonid(s, o: Objekt, *, asukoht: bool = True, ehitusperiood: bool = True) -> list[Korrektsioon]:
    """Objekti omadustest tulenevad korrektsioonid piirkonna keskmise suhtes."""
    k: list[Korrektsioon] = []
    if o.tyyp.value != "maa":
        if o.seisukord:
            k.append(Korrektsioon("Seisukord", seisukorra_tegur(s, o.seisukord), f"seisukord: {o.seisukord.value}"))
        if o.energiaklass:
            k.append(Korrektsioon("Energiaklass", energiaklassi_tegur(s, o.energiaklass), f"klass {o.energiaklass}"))
        if ehitusperiood and o.ehitusaasta:
            k.append(Korrektsioon("Ehitusperiood", ehitusaasta_tegur(s, o.ehitusaasta), f"ehitatud {o.ehitusaasta}"))
    if o.tyyp.value == "korter" and o.korrus is not None:
        k.append(Korrektsioon("Korrus", korruse_tegur(s, o.korrus, o.korruseid, o.lift),
                              f"{o.korrus}. korrus" + (f" / {o.korruseid}" if o.korruseid else "")))
    if asukoht and o.kaugused_m:
        kk = s.get_path("korrektsioonid.kaugus", {})
        for kat, võti in (("ühistransport", "ühistransport"), ("kool", "kool"), ("pood", "pood"), ("veekogu", "veekogu")):
            d = o.kaugused_m.get(kat)
            piir = kk.get(f"{võti}_lähedal_m")
            if d is not None and piir and d <= piir:
                k.append(Korrektsioon(f"Lähedus: {kat}", kk.get(f"{võti}_tegur", 1.0), f"{d} m"))
    return [x for x in k if abs(x.tegur - 1.0) > 1e-9]


def korruta(korrektsioonid: list[Korrektsioon]) -> float:
    t = 1.0
    for k in korrektsioonid:
        t *= k.tegur
    return t
