"""Meetodite tulemuste lepitamine üheks turuväärtuseks."""
from __future__ import annotations

from datetime import date

from .mudel import Hinnang, MeetodiTulemus, Objekt


def ümarda(v: float) -> float:
    """Ümardab hindamispraktikale omaselt: <100k → 500 €, <1M → 1000 €, muidu 5000 €."""
    samm = 500 if v < 100_000 else 1000 if v < 1_000_000 else 5000
    return round(v / samm) * samm


def lepita(o: Objekt, tulemused: list[MeetodiTulemus], s, kuupäev: date) -> Hinnang:
    baas = s.get_path(f"kaalud.{o.tyyp.value}", {})
    kehtivad = [t for t in tulemused if t.kehtiv and baas.get(t.meetod, 0) > 0]
    hoiatused = [f"[{t.meetod}] {h}" for t in tulemused for h in t.hoiatused]
    if not kehtivad:
        return Hinnang(o, kuupäev, tulemused, None, None, {},
                       hoiatused + ["Ühtegi meetodit ei õnnestunud rakendada – turuväärtust ei saa anda."])
    toorkaalud = {t.meetod: baas[t.meetod] * max(t.usaldus, 0.05) for t in kehtivad}
    kokku = sum(toorkaalud.values())
    kaalud = {m: k / kokku for m, k in toorkaalud.items()}
    väärtus = sum(t.väärtus * kaalud[t.meetod] for t in kehtivad)
    madal = sum((t.vahemik or (t.väärtus, t.väärtus))[0] * kaalud[t.meetod] for t in kehtivad)
    kõrge = sum((t.vahemik or (t.väärtus, t.väärtus))[1] * kaalud[t.meetod] for t in kehtivad)
    # Meetodite omavaheline lahknevus laiendab vahemikku
    vmin, vmax = min(t.väärtus for t in kehtivad), max(t.väärtus for t in kehtivad)
    if len(kehtivad) > 1 and (vmax - vmin) / väärtus > 0.2:
        hoiatused.append(f"Meetodite tulemused lahknevad {((vmax - vmin) / väärtus):.0%} – hindaja peab "
                         "põhjendama lõpliku kaalumise.")
        madal, kõrge = min(madal, vmin), max(kõrge, vmax)
    if len(kehtivad) == 1:
        hoiatused.append("Rakendati ainult üks meetod – tulemus on vähem kindel.")
    return Hinnang(o, kuupäev, tulemused, ümarda(väärtus), (ümarda(madal), ümarda(kõrge)), kaalud, hoiatused)
