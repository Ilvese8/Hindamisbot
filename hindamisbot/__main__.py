"""Käsurida ja vestlusbot.

  python -m hindamisbot bot                       # küsib andmed samm-sammult
  python -m hindamisbot hinda "Aadress" --tyyp korter --pind 54 --seisukord hea --korrus 3
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

from . import aruanne
from .hindaja import Hindaja
from .mudel import Objekt, ObjektiTyyp, Seisukord
from .seadistused import lae


def _objekt(a) -> Objekt:
    o = Objekt(aadress=a.aadress, tyyp=ObjektiTyyp.parse(a.tyyp) if a.tyyp else None)
    for k in ("pind_m2", "krundi_pind_m2", "ehitusaasta", "korrus", "korruseid", "tube",
              "energiaklass", "materjal", "sihtotstarve", "maakond", "omavalitsus", "asustusyksus", "lat", "lon"):
        v = getattr(a, k, None)
        if v is not None:
            o.maara(k, v, "sisend")
    if a.seisukord:
        o.maara("seisukord", Seisukord(a.seisukord), "sisend")
    return o


def _salvesta(h, väljund: Path, vormingud: list[str]) -> list[Path]:
    väljund.parent.mkdir(parents=True, exist_ok=True)
    failid = []
    if "md" in vormingud:
        p = väljund.with_suffix(".md")
        p.write_text(aruanne.markdown(h), encoding="utf-8")
        failid.append(p)
    if "docx" in vormingud:
        failid.append(aruanne.docx(h, väljund.with_suffix(".docx")))
    if "json" in vormingud:
        p = väljund.with_suffix(".json")
        p.write_text(json.dumps({
            "objekt": h.objekt.to_dict(), "kuupäev": h.hindamise_kuupäev.isoformat(),
            "turuväärtus": h.turuväärtus, "vahemik": h.vahemik, "kaalud": h.kaalud,
            "meetodid": [{"meetod": t.meetod, "väärtus": t.väärtus, "eur_m2": t.eur_m2, "usaldus": t.usaldus,
                          "vahemik": t.vahemik, "hoiatused": t.hoiatused} for t in h.tulemused],
            "hoiatused": h.hoiatused}, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        failid.append(p)
    return failid


def _kokkuvõte(h) -> str:
    rid = []
    if h.turuväärtus:
        rid.append(f"Hinnanguline turuväärtus: {aruanne.eur(h.turuväärtus)} "
                   f"(vahemik {aruanne.eur(h.vahemik[0])} – {aruanne.eur(h.vahemik[1])})")
    else:
        rid.append("Turuväärtust ei õnnestunud määrata.")
    for t in h.tulemused:
        if t.kehtiv:
            rid.append(f"  {aruanne.MEETODI_NIMI[t.meetod]}: {aruanne.eur(t.väärtus)} "
                       f"(kaal {h.kaalud.get(t.meetod, 0):.0%})")
    if h.hoiatused:
        rid.append("Hoiatused:")
        rid += [f"  - {x}" for x in h.hoiatused]
    return "\n".join(rid)


def _failinimi(aadress: str) -> str:
    return re.sub(r"[^\w]+", "_", aadress.lower()).strip("_")[:60] or "hinnang"


# ------------------------------------------------------------------ vestlusbot
def _küsi(tekst, teisendus=str, valikud=None, kohustuslik=False, sisend=input, väljund=print):
    while True:
        lisa = f" [{'/'.join(valikud)}]" if valikud else ""
        v = sisend(f"{tekst}{lisa}{'' if kohustuslik else ' (Enter = jäta vahele)'}: ").strip()
        if not v:
            if kohustuslik:
                väljund("  See väli on kohustuslik.")
                continue
            return None
        if valikud and v.lower() not in valikud:
            väljund(f"  Vali üks: {', '.join(valikud)}")
            continue
        try:
            return teisendus(v.replace(",", ".") if teisendus in (float, int) else v)
        except ValueError:
            väljund("  Vigane väärtus, proovi uuesti.")


def _arv(t):
    return int(float(t))


def bot(s, vorguta=False, sisend=input, väljund=print) -> None:
    k = lambda *a, **kw: _küsi(*a, sisend=sisend, väljund=väljund, **kw)  # noqa: E731
    väljund("Tere! Olen hindamisbot. Kasutan ainult riigi avaandmeid ja sinu sisestatud võrdlusobjekte.\n"
            "Tulemus on esmane hinnang, mille peab üle kontrollima hindaja.\n")
    h = Hindaja(s, vorguta=vorguta)
    while True:
        aadress = k("Objekti aadress (korteri puhul koos numbriga, nt Ehitajate tee 35-55)", kohustuslik=True)
        o = Objekt(aadress=aadress)
        korter = None
        väljund("Otsin avaandmetest (In-ADS, ehitisregister, maakataster, OpenStreetMap)...")
        hoiatused = h.kogu(o, korter)
        valikud = [t.value for t in ObjektiTyyp]
        if o.tyyp:
            väljund(f"  Objektitüüp: {o.tyyp.value} – {o.tyyp_pohjendus}")
            muuda = k("Muuda tüüpi?", valikud=valikud)
        else:
            muuda = k("Tüüpi ei õnnestunud tuvastada. Objekti liik", valikud=valikud, kohustuslik=True)
        if muuda and (o.tyyp is None or muuda != o.tyyp.value):
            o.tyyp, o.tyyp_pohjendus = ObjektiTyyp(muuda), None
            o.allikad["tyyp"] = "sisend"
            hoiatused = h.kogu(o, korter)
        if o.tyyp == ObjektiTyyp.KORTER and not o.pind_m2 and not o.hooneosa_nr:
            korter = k("Korteri number")
            if korter:
                hoiatused = h.kogu(o, korter)
        if o.hooneosa:
            väljund(f"  Hooneosa: {o.hooneosa}")
        for x in hoiatused:
            väljund(f"  ! {x}")
        if o.normaliseeritud_aadress:
            väljund(f"  Leitud: {o.normaliseeritud_aadress}")

        def täienda(väli, küsimus, t=str, valikud=None):
            praegu = getattr(o, väli)
            if praegu is not None:
                väljund(f"  {küsimus}: {getattr(praegu, 'value', praegu)} ({o.allikad.get(väli, '')})")
                return
            v = k(küsimus, t, valikud)
            if v is not None:
                o.maara(väli, v, "sisend")

        if o.tyyp != ObjektiTyyp.MAA:
            täienda("pind_m2", "Pind m²", float)
            täienda("ehitusaasta", "Ehitusaasta", _arv)
            täienda("energiaklass", "Energiaklass", str.upper, list("abcdefgh"))
            sk = k("Seisukord", valikud=[x.value for x in Seisukord])
            if sk:
                o.maara("seisukord", Seisukord(sk), "sisend")
        if o.tyyp == ObjektiTyyp.KORTER:
            täienda("korrus", "Korrus", _arv)
            täienda("korruseid", "Korruseid majas", _arv)
        if o.tyyp != ObjektiTyyp.KORTER:
            täienda("krundi_pind_m2", "Krundi pind m²", float)
        if o.tyyp == ObjektiTyyp.MAA:
            täienda("sihtotstarve", "Sihtotstarve (nt elamumaa, maatulundusmaa)")
        if not (o.maakond or o.omavalitsus):
            täienda("omavalitsus", "Omavalitsus (nt Tallinn, Tartu linn)")
            täienda("asustusyksus", "Linnaosa/asum")

        hinnang = h.hinda(o, korter=korter)
        väljund("\n" + _kokkuvõte(hinnang) + "\n")
        if (k("Kas salvestan aruande mustandi (md + docx)?", valikud=["j", "e"]) or "e") == "j":
            failid = _salvesta(hinnang, Path("aruanded") / _failinimi(o.aadress), ["md", "docx", "json"])
            väljund("Salvestatud: " + ", ".join(str(f) for f in failid))
        if (k("Hindan veel ühe objekti?", valikud=["j", "e"]) or "e") != "j":
            väljund("Head aega!")
            return


# ------------------------------------------------------------------ käsurida
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="hindamisbot", description="Kinnisvara turuväärtuse esmane hinnang avaandmetest")
    ap.add_argument("--seadistused", help="seadistuste fail (vaikimisi seadistused.toml)")
    ap.add_argument("--vorguta", action="store_true", help="ära tee võrgupäringuid (ainult kohalikud failid)")
    sub = ap.add_subparsers(dest="käsk", required=True)
    sub.add_parser("bot", help="vestluslik režiim")
    h = sub.add_parser("hinda", help="hinda ühte objekti")
    h.add_argument("aadress")
    h.add_argument("--tyyp", choices=[t.value for t in ObjektiTyyp],
                   help="objektitüüp; vaikimisi tuvastatakse automaatselt avaandmetest")
    h.add_argument("--korter", "--osa", dest="korter",
                   help="hooneosa number: korter, äripind vm (võib anda ka aadressis, nt 'Ehitajate tee 35-55')")
    h.add_argument("--pind", dest="pind_m2", type=float)
    h.add_argument("--krunt", dest="krundi_pind_m2", type=float)
    h.add_argument("--ehitusaasta", type=int)
    h.add_argument("--korrus", type=int)
    h.add_argument("--korruseid", type=int)
    h.add_argument("--tube", type=int)
    h.add_argument("--energiaklass")
    h.add_argument("--materjal", choices=["kivi", "paneel", "puit", "muu"])
    h.add_argument("--seisukord", choices=[x.value for x in Seisukord])
    h.add_argument("--sihtotstarve")
    h.add_argument("--maakond")
    h.add_argument("--omavalitsus")
    h.add_argument("--asustusyksus")
    h.add_argument("--lat", type=float)
    h.add_argument("--lon", type=float)
    h.add_argument("--maa-eur-m2", dest="maa_eur_m2", type=float, help="maa ühikuhind kulumeetodile")
    h.add_argument("--kuupaev", type=date.fromisoformat, help="hindamise kuupäev YYYY-MM-DD")
    h.add_argument("--valjund", type=Path, help="aruande failinimi ilma laiendita")
    h.add_argument("--vormingud", default="md,docx,json")
    a = ap.parse_args(argv)

    s = lae(a.seadistused)
    if a.käsk == "bot":
        bot(s, vorguta=a.vorguta)
        return 0
    hindaja = Hindaja(s, vorguta=a.vorguta)
    hinnang = hindaja.hinda(_objekt(a), kuupäev=a.kuupaev, korter=a.korter, maa_eur_m2=a.maa_eur_m2)
    print(_kokkuvõte(hinnang))
    väljund = a.valjund or Path("aruanded") / _failinimi(a.aadress)
    for f in _salvesta(hinnang, väljund, a.vormingud.split(",")):
        print(f"Salvestatud: {f}")
    return 0 if hinnang.turuväärtus else 2


if __name__ == "__main__":
    sys.exit(main())
