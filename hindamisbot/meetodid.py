"""Hindamismeetodid: turustatistika meetod, võrdlusmeetod ja kulumeetod."""
from __future__ import annotations

import math
from datetime import date

from . import korrektsioonid as kr
from .allikad.hinnastatistika import Hinnaindeks, Hinnastatistika, kvartal_kuupaevast
from .allikad.koordinaadid import kaugus_m
from .allikad.vordlusobjektid import Vordlusobjekt
from .mudel import Korrektsioon, MeetodiTulemus, Objekt, Seisukord

TASE = {"asustusyksus": "asumi", "omavalitsus": "omavalitsuse", "maakond": "maakonna"}


_GRUPP = {
    "korterid_ehitusaasta": "korterid majades, mis on ehitatud {nimi}",
    "korteriomand": "korterid pinnaga {nimi} m² (kõik ehitusaastad)",
    "eluhooned_ehitusaasta": "elamud, mis on ehitatud {nimi}",
    "ehitise_liik": "elamud (kõik ehitusaastad)",
    "hoonestamata_maa": "hoonestamata maa, sihtotstarve {nimi_v}",
    "hoonestatud_maa": "hoonestatud maa, sihtotstarve {nimi_v}",
}


def võrdlusgrupp(liik, nimi) -> str:
    mall = _GRUPP.get(str(liik), "{nimi}")
    return mall.format(nimi=str(nimi).replace("-", "–"), nimi_v=str(nimi).lower())


def n(x: float) -> str:
    """1234.5 -> '1 235'"""
    return f"{x:,.0f}".replace(",", " ")


def _pinna_alus(o: Objekt) -> tuple[float | None, str]:
    if o.tyyp.value == "maa":
        return o.krundi_pind_m2, "krundi pind"
    return o.pind_m2, "üldpind"


# --------------------------------------------------------------------------- statistika
def statistika_meetod(o: Objekt, stat, indeks: Hinnaindeks, s, kuupäev: date) -> MeetodiTulemus:
    t = MeetodiTulemus("statistika", None)
    pind, alus = _pinna_alus(o)
    if not stat.olemas:
        t.hoiatused.append("Hinnastatistika fail puudub – meetodit ei rakendatud.")
        return t
    if not pind:
        t.hoiatused.append(f"Puudub {alus} – meetodit ei saa rakendada.")
        return t
    kv = kvartal_kuupaevast(kuupäev)
    r = stat.leia(o.tyyp.value, o.maakond, o.omavalitsus, o.asustusyksus, pind=pind,
                  sihtotstarve=o.sihtotstarve if o.tyyp.value == "maa" else ("ärimaa" if o.tyyp.value == "aripind" else None),
                  kuni_kvartal=kv, max_kvartaleid=s.get_path("statistika.max_kvartaleid_tagasi", 8),
                  min_tehinguid=s.get_path("statistika.min_tehinguid", 5), ehitusaasta=o.ehitusaasta, kuupäev=kuupäev)
    if r is None:
        t.hoiatused.append("Sobivat hinnastatistika lahtrit ei leitud (piirkond/pinnavahemik/periood).")
        return t
    if r.pinna_alus == "krunt" and o.tyyp.value != "maa":
        pind, alus = o.krundi_pind_m2, "krundi pind"
        if not pind:
            t.hoiatused.append("Statistika on krundi €/m² kohta, aga krundi pind puudub.")
            return t
    rida = r.read[0] if r.read else {}

    baas = r.eur_m2
    if r.allikas == "api":
        grupp = võrdlusgrupp(rida.get("liik"), rida.get("nimi"))
        t.andmed["võrdlusgrupp"] = f"{grupp}, {rida.get('piirkond')}, {r.perioodid[0]}"
        t.andmed.update(grupp=grupp, grupp_piirkond=rida.get("piirkond"), grupp_periood=r.perioodid[0],
                        grupp_tehinguid=r.tehinguid)
        t.selgitus.append(f"Võrdlusgrupp: {grupp} – {rida.get('piirkond')}, {r.perioodid[0]}, "
                          f"{r.tehinguid} ostu-müügitehingut, mediaan {n(baas)} €/m² ({alus}). "
                          f"Allikas: Maa- ja Ruumiamet, tehingute andmebaas ({rida.get('liik')}).")
    else:
        t.selgitus.append(f"Maa- ja Ruumiameti hinnastatistika ({TASE[r.tase]} tasemel, {r.tehinguid} tehingut, "
                          f"perioodid {', '.join(r.perioodid)}): {n(baas)} €/m².")
    # Ajakorrektsioon: statistika keskmisest perioodist hindamise kuupäevani
    if r.perioodid:
        alg = r.read[len(r.read) // 2]["_kv"]  # valimi keskmine periood
        tegur = indeks.tegur(alg, kv)
        if tegur and abs(tegur - 1) > 1e-6:
            t.korrektsioonid.append(Korrektsioon("Aeg (hinnaindeks)", tegur, f"{alg[0]} Q{alg[1]} → {kv[0]} Q{kv[1]}"))
    # Kui võrdlusgrupp on juba sama ehitusperioodi tehingud, ei korrigeerita ehitusaasta järgi uuesti.
    # Kui grupp hõlmab kõiki ehitusaastaid (nt pinnavahemiku statistika), arvestatakse ehitusaastat korrektsiooniga.
    grupp_ehitusaasta_järgi = str(rida.get("liik", "")).endswith("_ehitusaasta")
    rakenda_aasta = s.get_path("statistika.rakenda_ehitusperioodi", False) or \
        (bool(o.ehitusaasta) and not grupp_ehitusaasta_järgi)
    t.korrektsioonid += kr.objekti_korrektsioonid(s, o, ehitusperiood=rakenda_aasta)
    if o.ehitusaasta and o.tyyp.value != "maa":
        aasta_allikas = o.allikad.get("ehitusaasta", "sisend").replace("Ehitisregister: ", "EHR – ")
        t.andmed["ehitusaasta_allikas"] = aasta_allikas
        t.andmed["ehitusaasta_arvestus"] = (
            f"ehitusaasta {o.ehitusaasta}: võrreldi sama ehitusperioodi ({rida.get('nimi')}) tehingutega"
            if grupp_ehitusaasta_järgi else
            f"ehitusaasta {o.ehitusaasta}: arvestatud ehitusperioodi korrektsiooniga")
    elif o.tyyp.value != "maa":
        t.hoiatused.append("Ehitusaasta pole teada – hinnang ei arvesta hoone vanust. Lisa ehitusaasta väljale „Täpsusta“.")
    eur_m2 = baas * kr.korruta(t.korrektsioonid)
    t.eur_m2 = eur_m2
    t.väärtus = eur_m2 * pind

    # Vahemik: standardhälbest, kui olemas; muidu min/max-ist (äärmused, mitte usaldusvahemik)
    sd = rida.get("standardhälve")
    if sd:
        laius = min(0.25, max(0.06, 0.5 * sd / baas))
    elif r.min_eur_m2 and r.max_eur_m2 and r.max_eur_m2 > r.min_eur_m2:
        laius = min(0.25, max(0.08, (r.max_eur_m2 - r.min_eur_m2) / (4 * baas)))
    else:
        laius = 0.15
    t.vahemik = (t.väärtus * (1 - laius), t.väärtus * (1 + laius))
    tasemekaal = {"asustusyksus": 1.0, "omavalitsus": 0.8, "maakond": 0.55}[r.tase]
    t.usaldus = round(min(1.0, math.sqrt(r.tehinguid / 30)) * tasemekaal, 2)
    if o.asustusyksus and r.tase != "asustusyksus":
        t.hoiatused.append(f"Asumi tasemel andmeid polnud piisavalt – kasutati {TASE[r.tase]} taset.")
    t.andmed["statistika_read"] = len(r.read)
    return t


# --------------------------------------------------------------------------- võrdlus
def _sarnasus(o: Objekt, v: Vordlusobjekt, kaugus: float | None, s) -> float:
    """0..1 sarnasusskoor."""
    skoor = 1.0
    if kaugus is not None:
        skoor *= math.exp(-kaugus / max(1.0, s.get_path("vordlus.max_kaugus_m", 3000) / 2))
    pind_o, _ = _pinna_alus(o)
    pind_v = v.krundi_pind_m2 if o.tyyp.value == "maa" else v.pind_m2
    if pind_o and pind_v:
        skoor *= math.exp(-abs(math.log(pind_o / pind_v)) * 2)
    if o.ehitusaasta and v.ehitusaasta:
        skoor *= math.exp(-abs(o.ehitusaasta - v.ehitusaasta) / 25)
    return skoor


def vordlus_meetod(o: Objekt, vordlus: list[Vordlusobjekt], indeks: Hinnaindeks, s, kuupäev: date) -> MeetodiTulemus:
    t = MeetodiTulemus("võrdlus", None)
    pind, alus = _pinna_alus(o)
    if not vordlus:
        t.hoiatused.append("Võrdlusobjektide fail puudub või on tühi – meetodit ei rakendatud.")
        return t
    if not pind:
        t.hoiatused.append(f"Puudub {alus} – meetodit ei saa rakendada.")
        return t
    max_kaugus = s.get_path("vordlus.max_kaugus_m", 3000)
    max_vanus = s.get_path("vordlus.max_vanus_kuud", 24)
    kv = kvartal_kuupaevast(kuupäev)

    kandidaadid = []
    for v in vordlus:
        if v.tyyp != o.tyyp.value:
            continue
        pind_v = v.krundi_pind_m2 if o.tyyp.value == "maa" else v.pind_m2
        if not pind_v:
            continue
        if v.kuupaev and (kuupäev - v.kuupaev).days > max_vanus * 30.5:
            continue
        d = None
        if None not in (o.lat, o.lon, v.lat, v.lon):
            d = kaugus_m(o.lat, o.lon, v.lat, v.lon)
            if d > max_kaugus:
                continue
        kandidaadid.append((_sarnasus(o, v, d, s), v, d, pind_v))
    kandidaadid.sort(key=lambda x: -x[0])
    valitud = kandidaadid[: s.get_path("vordlus.k", 6)]
    if len(valitud) < 3:
        t.hoiatused.append(f"Sobivaid võrdlusobjekte on {len(valitud)} (vaja vähemalt 3).")
        if not valitud:
            return t

    read, hinnad, kaalud = [], [], []
    for skoor, v, d, pind_v in valitud:
        eur_m2 = v.hind / pind_v
        k = []
        if v.allika_tyyp.startswith("pakk"):
            k.append(("pakkumine→tehing", s.get_path("vordlus.pakkumise_korrektsioon", 0.95)))
        if v.kuupaev:
            tg = indeks.tegur(kvartal_kuupaevast(v.kuupaev), kv)
            if tg:
                k.append(("aeg", tg))
        if o.tyyp.value != "maa":
            so, sv = o.seisukord, (Seisukord(v.seisukord) if v.seisukord in [x.value for x in Seisukord] else None)
            if so and sv:
                k.append(("seisukord", kr.seisukorra_tegur(s, so) / kr.seisukorra_tegur(s, sv)))
            if o.energiaklass and v.energiaklass:
                k.append(("energiaklass", kr.energiaklassi_tegur(s, o.energiaklass) / kr.energiaklassi_tegur(s, v.energiaklass)))
            if o.ehitusaasta and v.ehitusaasta:
                k.append(("ehitusperiood", kr.ehitusaasta_tegur(s, o.ehitusaasta) / kr.ehitusaasta_tegur(s, v.ehitusaasta)))
        if o.tyyp.value == "korter" and o.korrus is not None and v.korrus is not None:
            k.append(("korrus", kr.korruse_tegur(s, o.korrus, o.korruseid, o.lift) / kr.korruse_tegur(s, v.korrus, v.korruseid)))
        k = [x for x in k if abs(x[1] - 1) > 0.0005]
        kordaja = math.prod(x[1] for x in k)
        korr = eur_m2 * kordaja
        hinnad.append(korr)
        kaalud.append(skoor)
        read.append({"aadress": v.aadress, "kaugus_m": round(d) if d is not None else None,
                     "kuupäev": v.kuupaev.isoformat() if v.kuupaev else "", "liik": v.allika_tyyp,
                     "pind_m2": pind_v, "hind": v.hind, "eur_m2": round(eur_m2),
                     "korrektsioonid": ", ".join(f"{n} {x:+.1%}".replace("+-", "-") for n, x in
                                                  [(n, x - 1) for n, x in k]) or "–",
                     "korr_eur_m2": round(korr), "sarnasus": round(skoor, 3), "allikas": v.allikas})

    w = sum(kaalud) or 1.0
    eur_m2 = sum(h * k for h, k in zip(hinnad, kaalud)) / w
    var = sum(k * (h - eur_m2) ** 2 for h, k in zip(hinnad, kaalud)) / w
    cv = math.sqrt(var) / eur_m2 if eur_m2 else 1.0
    t.eur_m2 = eur_m2
    t.väärtus = eur_m2 * pind
    laius = min(0.25, max(0.06, cv))
    t.vahemik = (t.väärtus * (1 - laius), t.väärtus * (1 + laius))
    t.usaldus = round(min(1.0, len(valitud) / 6) * max(0.2, 1 - cv * 2) * min(1.0, sum(kaalud) / len(kaalud) * 2), 2)
    t.andmed["võrdlusobjektid"] = read
    t.selgitus.append(f"{len(valitud)} võrdlusobjekti, korrigeeritud kaalutud keskmine {n(eur_m2)} €/m², "
                      f"hajuvus (CV) {cv:.0%}.")
    if cv > 0.2:
        t.hoiatused.append("Võrdlusobjektide korrigeeritud hinnad hajuvad tugevalt (CV > 20%) – kontrolli valikut.")
    return t


# --------------------------------------------------------------------------- kulu
def kulu_meetod(o: Objekt, stat, indeks: Hinnaindeks, s, kuupäev: date,
                maa_eur_m2: float | None = None) -> MeetodiTulemus:
    """Maa väärtus + (taastamismaksumus − kulum) + arendaja kasum. Eramutele ja äripindadele."""
    t = MeetodiTulemus("kulu", None)
    if o.tyyp.value not in ("eramu", "aripind"):
        return t
    if not o.pind_m2:
        t.hoiatused.append("Puudub hoone pind – kulumeetodit ei rakendatud.")
        return t
    if not o.krundi_pind_m2:
        t.hoiatused.append("Puudub krundi pind – kulumeetodit ei rakendatud.")
        return t
    # Maa väärtus: käsitsi antud või hoonestamata maa statistikast
    if maa_eur_m2 is None and stat.olemas:
        r = stat.leia("maa", o.maakond, o.omavalitsus, o.asustusyksus, pind=o.krundi_pind_m2,
                      sihtotstarve="elamumaa" if o.tyyp.value == "eramu" else "ärimaa",
                      kuni_kvartal=kvartal_kuupaevast(kuupäev), kuupäev=kuupäev,
                      max_kvartaleid=s.get_path("statistika.max_kvartaleid_tagasi", 8),
                      min_tehinguid=s.get_path("statistika.min_tehinguid", 5))
        if r:
            maa_eur_m2 = r.eur_m2
            t.selgitus.append(f"Maa €/m² hoonestamata maa statistikast ({r.tase}, {r.tehinguid} tehingut).")
    if maa_eur_m2 is None:
        t.hoiatused.append("Maa väärtust ei õnnestunud leida – kulumeetodit ei rakendatud.")
        return t
    maa = maa_eur_m2 * o.krundi_pind_m2

    taast = s.get_path(f"kulu.taastamismaksumus_eur_m2.{o.tyyp.value}")
    eluiga = s.get_path(f"kulu.eluiga.{o.materjal or 'muu'}", s.get_path("kulu.eluiga.muu", 80))
    vanus = o.vanus(kuupäev)
    if vanus is None:
        t.hoiatused.append("Ehitusaasta puudub – kulum eeldatud 30%.")
        kulum = 0.30
    else:
        kulum = min(s.get_path("kulu.max_kulum", 0.8), vanus / eluiga)
    # Seisukord nihutab kulumit: hea = 0, parem vähendab, halvem suurendab
    st = kr.seisukorra_tegur(s, o.seisukord) if o.seisukord else 1.0
    hoone = taast * o.pind_m2 * (1 - kulum) * st
    kasum = s.get_path("kulu.arendaja_kasum", 0.0)
    t.väärtus = (maa + hoone) * (1 + kasum)
    t.eur_m2 = t.väärtus / o.pind_m2
    t.vahemik = (t.väärtus * 0.85, t.väärtus * 1.15)
    t.usaldus = 0.5 if vanus is not None and vanus < 40 else 0.3
    t.selgitus += [
        f"Maa: {n(o.krundi_pind_m2)} m² × {n(maa_eur_m2)} €/m² = {n(maa)} €",
        f"Hoone: {n(o.pind_m2)} m² × {n(taast)} €/m² × (1 − kulum {kulum:.0%}) × seisukord {st:.2f} = "
        f"{n(hoone)} €",
        f"Arendaja kasum {kasum:.0%}.",
    ]
    t.hoiatused.append("Kulumeetodi taastamismaksumus ja eluiga on seadistuste eeldused – kontrolli neid.")
    return t
