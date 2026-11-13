"""Infopank (andmed/turuulevaated.csv): piirkonna sobitamine, indekseerimine ja usutavuskontroll."""
import csv
from datetime import date
from pathlib import Path

import pytest

from hindamisbot import aruanne
from hindamisbot.hindaja import Hindaja
from hindamisbot.mudel import Objekt, ObjektiTyyp
from hindamisbot.seadistused import lae
from hindamisbot.turuulevaated import Turuulevaated, _sama

JUUR = Path(__file__).resolve().parent.parent
CSV = JUUR / "andmed" / "turuulevaated.csv"


@pytest.fixture(scope="module")
def tu():
    return Turuulevaated(CSV)


def kor(**kw):
    d = dict(maakond="Harju maakond", omavalitsus="Tallinn", asustusyksus="Mustamäe linnaosa", pind_m2=50)
    d.update(kw)
    return Objekt("X 1-1", ObjektiTyyp.KORTER, **d)


def test_csv_veerud_ja_allikad():
    with open(CSV, encoding="utf-8") as f:
        read = list(csv.DictReader(f))
    assert len(read) > 1000
    for r in read:
        assert r["allikas"] and r["url"].startswith("https://") and r["periood"] and r["väärtus"]
    assert {"Maa- ja Ruumiamet", "Uus Maa", "1Partner", "Pindi Kinnisvara", "Newsec"} <= {r["allikas"] for r in read}


def test_nimede_sobitamine():
    assert _sama("Põhja-Tallinna linnaosa", "Põhja-Tallinn")
    assert _sama("Mustamäe linnaosa", "Mustamäe")
    assert not _sama("Tallinn", "Tartu linn")


def test_indeksi_tegur(tu):
    tegur, per = tu.indeksi_tegur()
    assert per == "2026-III"
    # 2026 III / 2025 kvartalite keskmine
    assert tegur == pytest.approx(5.97677 / ((5.49706 + 5.64280 + 5.67886 + 5.73695) / 4), rel=1e-6)


def test_tallinna_asum_on_tapseim(tu):
    o = kor()
    o.allikad["asum"] = "Mustamäe"
    k = tu.kontekst(o, 2500)
    assert k.viide_piirkond.startswith("Mustamäe asum 2025")
    assert k.viide_eur_m2 == pytest.approx(2359 * tu.indeksi_tegur()[0])
    assert k.hoiatus is None
    assert any("1Partner" in r.allikas for r in k.read)
    assert any("Uus Maa" in r.allikas for r in k.read)


def test_linnaosa_kui_asumit_pole(tu):
    k = tu.kontekst(kor(asustusyksus="Põhja-Tallinna linnaosa"), 3100)
    assert k.viide_piirkond.startswith("Põhja-Tallinn linnaosa 2025")


def test_hoiatus_suure_korvalekalde_korral(tu):
    k = tu.kontekst(kor(), 5000)
    assert k.kõrvalekalle > 0.25 and "erineb" in k.hoiatus


def test_vaike_asula_kasutab_maakonda(tu):
    o = kor(maakond="Jõgeva maakond", omavalitsus="Jõgeva vald", asustusyksus="Kuremaa alevik")
    k = tu.kontekst(o, 400)
    assert k.viide_piirkond.startswith("Jõgeva maakond")


def test_tartu_linnaosa(tu):
    o = kor(maakond="Tartu maakond", omavalitsus="Tartu linn", asustusyksus="Tartu linn")
    o.allikad["asum"] = "Karlova"
    k = tu.kontekst(o, 2900)
    assert k.viide_piirkond.startswith("Karlova")


def test_eramu_ja_maa(tu):
    e = Objekt("Y", ObjektiTyyp.ERAMU, maakond="Harju maakond", omavalitsus="Viimsi vald", asustusyksus="Haabneeme alevik")
    assert any("Viimsi vald" in r.silt for r in tu.kontekst(e).read)
    m = Objekt("Z", ObjektiTyyp.MAA, maakond="Tartu maakond", omavalitsus="Tartu vald", sihtotstarve="maatulundusmaa")
    silt = " ".join(r.silt for r in tu.kontekst(m).read)
    assert "Haritava" in silt and "Metsamaa" in silt


def test_aripind_tallinn(tu):
    a = Objekt("B", ObjektiTyyp.ARIPIND, maakond="Harju maakond", omavalitsus="Tallinn", asustusyksus="Kesklinna linnaosa")
    v = " ".join(r.silt for r in tu.kontekst(a, keel="en").read)
    assert "vacancy" in v and "yield" in v


def test_hinnang_ja_aruanne_sisaldavad_konteksti():
    s = lae(JUUR / "seadistused_naidis.toml")
    hj = Hindaja(s, vorguta=True)
    o = kor(asustusyksus="Mustamäe", ehitusaasta=1968, korrus=3, korruseid=5)
    h = hj.hinda(o, date(2026, 11, 13))
    assert h.turg and not h.turg["et"].tyhi
    md = aruanne.markdown(h, "et")
    assert "Turu kontekst" in md and "Maa- ja Ruumiamet" in md
    assert "Market context" in aruanne.markdown(h, "en")


def test_uusarendus_pindi(tu):
    o = kor(asustusyksus="Kesklinna linnaosa", ehitusaasta=2025)
    v = {r.silt: r.väärtus for r in tu.kontekst(o, 4500).read}
    assert any("Uusarendused Tallinn ja Harjumaa" in s for s in v)
    assert any("väljamüügi keskmine" in s and "Tallinn" in s for s in v)
    vana = kor(maakond="Tartu maakond", omavalitsus="Tartu linn", asustusyksus="Tartu linn", ehitusaasta=1975)
    assert not any("Uusarendused" in r.silt for r in tu.kontekst(vana, 2000).read)
