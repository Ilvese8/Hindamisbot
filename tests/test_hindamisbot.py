"""Testid töötavad ilma võrguta: kasutatakse näidisandmeid ja salvestatud vastuste kujusid."""
from datetime import date
from pathlib import Path

import pytest

from hindamisbot.__main__ import bot, main
from hindamisbot.allikad import inads, osm
from hindamisbot.allikad.ehr import Ehitisregister
from hindamisbot.allikad.hinnastatistika import Hinnaindeks, Hinnastatistika, kvartal, pinnavahemik
from hindamisbot.allikad.koordinaadid import kaugus_m, lest97_wgs84
from hindamisbot import i18n
from hindamisbot.hindaja import Hindaja
from hindamisbot.lepitamine import lepita, ümarda
from hindamisbot.mudel import MeetodiTulemus, Objekt, ObjektiTyyp, Seisukord
from hindamisbot.seadistused import lae

JUUR = Path(__file__).resolve().parent.parent
KP = date(2026, 11, 13)


@pytest.fixture
def s():
    return lae(JUUR / "seadistused_naidis.toml")


def korter():
    o = Objekt("Näidise tn 1-15, Tallinn", ObjektiTyyp.KORTER, maakond="Harju maakond", omavalitsus="Tallinn",
               asustusyksus="Mustamäe", pind_m2=51.2, korrus=3, korruseid=5, ehitusaasta=1968,
               energiaklass="E", seisukord=Seisukord.HEA, lat=59.4030, lon=24.6970)
    return o


# ---------------------------------------------------------------- abifunktsioonid
@pytest.mark.parametrize("sisend,oodatud", [
    ("2026 III", (2026, 3)), ("2026-Q2", (2026, 2)), ("III kv 2025", (2025, 3)),
    ("2024/1", (2024, 1)), ("2023", (2023, 4)), ("", None),
])
def test_kvartal(sisend, oodatud):
    assert kvartal(sisend) == oodatud


@pytest.mark.parametrize("sisend,oodatud", [
    ("40-54,99", (40, 54.99)), ("<30", (None, 30)), (">100", (100, None)), ("100+", (100, None)), ("", (None, None)),
])
def test_pinnavahemik(sisend, oodatud):
    assert pinnavahemik(sisend) == oodatud


def test_lest97_tartu_raekoda():
    lat, lon = lest97_wgs84(659200, 6474500)
    assert kaugus_m(lat, lon, 58.3802, 26.7224) < 250


def test_ümardamine():
    assert ümarda(99_740) == 99_500
    assert ümarda(118_742) == 119_000
    assert ümarda(328_400) == 328_000
    assert ümarda(1_234_000) == 1_235_000


# ---------------------------------------------------------------- avaandmete parserid
def test_inads_rikasta():
    kirje = {"pikkaadress": "Harju maakond, Tallinn, Mustamäe linnaosa, Näidise tn 1-15",
             "maakond": "Harju maakond", "omavalitsus": "Tallinn", "asustusyksus": "Mustamäe linnaosa",
             "viitepunkt_x": "537500.00", "viitepunkt_y": "6584600.00", "ads_oid": "ME00000000",
             "seosed": [{"liik": "EHITISHOONE", "tunnus": "101034567"}, {"liik": "KATASTRIYKSUS", "tunnus": "78401:101:0001"}]}
    o = Objekt("x", ObjektiTyyp.KORTER)
    hoiatused = inads.rikasta(o, kirje)
    assert o.ehr_kood == "101034567" and o.katastritunnus == "78401:101:0001"
    assert 59.3 < o.lat < 59.5 and 24.6 < o.lon < 24.8
    assert o.allikad["maakond"] == "In-ADS" and not hoiatused


def test_inads_ei_kirjuta_sisendit_yle():
    o = Objekt("x", ObjektiTyyp.KORTER, maakond="Käsitsi")
    inads.rikasta(o, {"maakond": "Harju maakond"})
    assert o.maakond == "Käsitsi"


def test_osm_kaugused():
    vastus = {"elements": [
        {"type": "node", "lat": 59.4035, "lon": 24.6970, "tags": {"highway": "bus_stop"}},
        {"type": "way", "tags": {"amenity": "school"}, "center": {"lat": 59.4080, "lon": 24.6970}},
        {"type": "way", "tags": {"natural": "coastline"}, "geometry": [{"lat": 59.43, "lon": 24.69}, {"lat": 59.42, "lon": 24.70}]},
    ]}
    k = osm.arvuta_kaugused(vastus, 59.4030, 24.6970)
    assert 50 < k["ühistransport"] < 60
    assert 550 < k["kool"] < 570
    assert k["veekogu"] < 2000


def test_ehr_vastendus(s):
    e = Ehitisregister(s.fail("ehitisregister"))
    assert e.leia(ehr_kood="104055501")["esmane_kasutus"] == "2008"
    assert e.leia(aadress="Näidise tn 1-15, Tallinn")["ehr_kood"] == "101034567"
    assert e.leia(aadress="Näidise tn 11") is None


# ---------------------------------------------------------------- statistika
def test_statistika_taseme_langus(s):
    st = Hinnastatistika(s.fail("hinnastatistika"))
    r = st.leia("korter", "Harju maakond", "Tallinn", "Mustamäe", pind=51, kuni_kvartal=(2026, 4))
    assert r.tase == "asustusyksus" and r.eur_m2 == pytest.approx(2350, abs=60)
    r2 = st.leia("korter", "Harju maakond", "Tallinn", "Kristiine", pind=51, kuni_kvartal=(2026, 4))
    assert r2.tase == "omavalitsus" and r2.eur_m2 == pytest.approx(2890)
    assert st.leia("korter", "Harju maakond", "Tallinn", None, pind=51, kuni_kvartal=(2030, 1)) is None


def test_hinnaindeks(s):
    i = Hinnaindeks(s.fail("hinnaindeks"))
    assert i.tegur((2025, 1), (2026, 3)) == pytest.approx(5.63 / 5.35)
    assert i.tegur((2026, 3), (2027, 2)) == pytest.approx(1.0045, abs=0.001)  # puuduv periood → viimane teadaolev


# ---------------------------------------------------------------- terviktöövoog
def test_korter(s):
    h = Hindaja(s, vorguta=True).hinda(korter(), kuupäev=KP)
    assert 100_000 < h.turuväärtus < 140_000
    assert h.vahemik[0] < h.turuväärtus < h.vahemik[1]
    assert set(h.kaalud) == {"statistika", "võrdlus"} and sum(h.kaalud.values()) == pytest.approx(1)


def test_eramu_kolm_meetodit(s):
    o = Objekt("Proovi tn 7, Tartu", ObjektiTyyp.ERAMU, maakond="Tartu maakond", omavalitsus="Tartu linn",
               krundi_pind_m2=950, seisukord=Seisukord.HEA, lat=58.3705, lon=26.7420)
    h = Hindaja(s, vorguta=True).hinda(o, kuupäev=KP)
    assert o.ehitusaasta == 2008 and o.allikad["ehitusaasta"] == "Ehitisregister"
    assert set(h.kaalud) == {"statistika", "võrdlus", "kulu"}
    assert 250_000 < h.turuväärtus < 400_000


def test_maa(s):
    o = Objekt("Metsa, Saue vald", ObjektiTyyp.MAA, maakond="Harju maakond", omavalitsus="Saue vald",
               krundi_pind_m2=2200, sihtotstarve="elamumaa")
    h = Hindaja(s, vorguta=True).hinda(o, kuupäev=KP)
    assert h.turuväärtus == pytest.approx(2200 * 34, rel=0.1)


def test_andmete_puudumisel_turuväärtust_ei_anta(s):
    o = Objekt("Tundmatu 1", ObjektiTyyp.ARIPIND)
    h = Hindaja(s, vorguta=True).hinda(o, kuupäev=KP)
    assert h.turuväärtus is None and any("Ühtegi meetodit" in x for x in h.hoiatused)


def test_lahknevus_hoiatab(s):
    a = MeetodiTulemus("statistika", 100_000, usaldus=1, vahemik=(90_000, 110_000))
    b = MeetodiTulemus("võrdlus", 150_000, usaldus=1, vahemik=(140_000, 160_000))
    h = lepita(korter(), [a, b], s, KP)
    assert any("lahknevad" in x for x in h.hoiatused) and h.vahemik[0] <= 100_000


def test_cli_ja_aruanded(tmp_path):
    rc = main(["--seadistused", str(JUUR / "seadistused_naidis.toml"), "--vorguta", "hinda", "Näidise tn 1-15, Tallinn",
               "--tyyp", "korter", "--pind", "51.2", "--korrus", "3", "--korruseid", "5", "--seisukord", "hea",
               "--maakond", "Harju maakond", "--omavalitsus", "Tallinn", "--asustusyksus", "Mustamäe",
               "--lat", "59.403", "--lon", "24.697", "--kuupaev", "2026-11-13", "--valjund", str(tmp_path / "a")])
    assert rc == 0
    md = (tmp_path / "a.md").read_text(encoding="utf-8")
    assert "MUSTAND" in md and "Võrdlusmeetod" in md and "EVS 875" in md
    assert (tmp_path / "a.docx").stat().st_size > 5000 and (tmp_path / "a.json").exists()


def test_vestlusbot(s, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    vastused = iter(["Näidise tn 1-15, Tallinn", "korter", "51,2", "1968", "e", "hea", "3", "5",
                     "Tallinn", "Mustamäe", "j", "e"])
    väljund = []
    bot(s, vorguta=True, sisend=lambda _: next(vastused), väljund=väljund.append)
    tekst = "\n".join(väljund)
    assert "Hinnanguline turuväärtus" in tekst and "Head aega" in tekst
    assert list((tmp_path / "aruanded").glob("*.docx"))


# ---------------------------------------------------------------- Maa- ja Ruumiameti statistika liides
import json  # noqa: E402
from hindamisbot.allikad.kataster_stat import KatasterStatistika, StatAllikas, vahemik  # noqa: E402

FIKS = json.loads((Path(__file__).parent / "fikstuurid" / "kataster_api.json").read_text(encoding="utf-8"))


class FakeKlient:
    """Asendab HTTP-kliendi: vastab fikstuurist, jätab päringud meelde."""

    def __init__(self, maha=False):
        self.paringud = []
        self.maha = maha

    def json(self, url, params=None, **_):
        if self.maha:
            raise ConnectionError("test")
        tee = url.split("/api/tehingud/")[1]
        self.paringud.append((tee, dict(params or {})))
        if tee == "hinnad":
            p = params
            kood = f"asum={p['asumKood']}" if p["asumKood"] else f"ov={p['ovKood']}" if p["ovKood"] else f"mk={p['mkKood']}"
            assert p["tehinguLiik"] == "OSTM"
            return FIKS.get(f"hinnad|{p['statistikaLiik']}|{kood}", [])
        võti = tee + ("?" + "&".join(f"{k}={v}" for k, v in params.items()) if params else "")
        return FIKS.get(võti, [])


@pytest.mark.parametrize("nimi,oodatud", [
    ("41-54,99", (41, 54.99)), ("<1939", (None, 1939)), ("2026 ...", (2026, None)), ("1940-1970", (1940, 1970)),
])
def test_api_vahemik(nimi, oodatud):
    assert vahemik(nimi) == oodatud


def test_api_korter_ehitusaasta_jargi(s):
    api = KatasterStatistika(FakeKlient(), s)
    r = api.leia("korter", "Harju maakond", "Tallinn", "Mustamäe linnaosa", pind=51.2, ehitusaasta=1968,
                 kuupäev=KP)
    assert r.allikas == "api" and r.tase == "asustusyksus"
    assert r.eur_m2 == pytest.approx(2511.42) and r.tehinguid == 697
    assert r.read[0]["liik"] == "korterid_ehitusaasta" and r.perioodid == ["11.2025–10.2026"]


def test_api_korter_pinna_jargi_kui_ehitusaasta_puudub(s):
    r = KatasterStatistika(FakeKlient(), s).leia("korter", "Harju maakond", "Tallinn", "Mustamäe", pind=51.2,
                                                 kuupäev=KP)
    assert r.eur_m2 == pytest.approx(2587.80) and r.read[0]["nimi"] == "41-54,99"


def test_api_peidetud_lahter_laiendab(s):
    # 1991-2000 on peidetud (<5 tehingut) – kõik tasemed tühjad → None, mitte viga
    r = KatasterStatistika(FakeKlient(), s).leia("korter", "Harju maakond", "Tallinn", "Mustamäe", pind=51,
                                                 ehitusaasta=1995, kuupäev=KP)
    assert r is not None and r.read[0]["liik"] == "korteriomand"  # langes pinnavahemiku statistikale


def test_api_eramu_ja_maa(s):
    k = FakeKlient()
    api = KatasterStatistika(k, s)
    r = api.leia("eramu", "Tartu maakond", "Tartu linn", None, pind=164.5, ehitusaasta=2008, kuupäev=KP)
    assert r.eur_m2 == pytest.approx(1303.21) and r.pinna_alus == "hoone pind"
    m = api.leia("maa", "Tartu maakond", "Tartu linn", None, pind=950, sihtotstarve="elamumaa", kuupäev=KP)
    assert m.eur_m2 == pytest.approx(100.36) and m.pinna_alus == "krunt"
    # Piirkonnakoodid küsitakse vahemälust ühe korra
    assert sum(1 for t, _ in k.paringud if t == "filter/omavalitsused") == 1


def test_api_maas_fallback_failile(s):
    st = StatAllikas(KatasterStatistika(FakeKlient(maha=True), s), Hinnastatistika(s.fail("hinnastatistika")))
    r = st.leia("korter", "Harju maakond", "Tallinn", "Mustamäe", pind=51, kuni_kvartal=(2026, 4), kuupäev=KP)
    assert r.allikas == "fail" and st.hoiatused


def test_terviktoovoog_api_ga(s, monkeypatch):
    h = Hindaja(s, vorguta=True)
    h.stat = StatAllikas(KatasterStatistika(FakeKlient(), s), h.stat.fail)
    o = korter()
    o.asustusyksus = "Mustamäe linnaosa"
    hinnang = h.hinda(o, kuupäev=KP)
    stat = next(t for t in hinnang.tulemused if t.meetod == "statistika")
    assert "tehingute andmebaas" in stat.selgitus[0] and "1940–1970" in stat.selgitus[0]
    assert 115_000 < stat.väärtus < 135_000          # 2511 €/m² × 51,2 m² × korrektsioonid
    assert 0.06 <= (stat.vahemik[1] / stat.väärtus - 1) <= 0.25


# ---------------------------------------------------------------- ehitisregistri liides (kõik ehitised)
from hindamisbot.allikad import ehr_api  # noqa: E402
from hindamisbot.allikad.inads import eralda_hooneosa  # noqa: E402

FDIR = Path(__file__).parent / "fikstuurid"
EHR_JSON = json.loads((FDIR / "ehr_101019881.json").read_text(encoding="utf-8"))
EHR_ENERGIA = json.loads((FDIR / "ehr_101019881_energia.json").read_text(encoding="utf-8"))
EHR_DOK = json.loads((FDIR / "ehr_dokumendid.json").read_text(encoding="utf-8"))
INADS_JSON = json.loads((FDIR / "inads_ehitajate35.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("sisend,oodatud", [
    ("Ehitajate tee 35-55, Tallinn", ("Ehitajate tee 35, Tallinn", "55")),
    ("Ehitajate tee 35-55", ("Ehitajate tee 35", "55")),
    ("Pärnu mnt 12A-3", ("Pärnu mnt 12A", "3")),
    ("Kase tn 7, Tartu", ("Kase tn 7, Tartu", None)),
])
def test_eralda_hooneosa(sisend, oodatud):
    assert eralda_hooneosa(sisend) == oodatud


def test_ehr_parsi_hoone_ja_osad():
    e = ehr_api.parsi(EHR_JSON, EHR_ENERGIA)
    assert e.ehitusaasta == 1964 and e.korruseid == 5 and e.lift is False
    assert e.materjal == "paneel" and e.katastritunnused == ["78405:501:2928"]
    assert e.energiaklass == "E" and e.energiamargise_kp.year == 2010
    assert e.eluruume == 3
    osa = e.leia_osa("55")
    assert (osa.pind_m2, osa.tube, osa.korrus) == (45.7, 2, 4)
    assert e.leia_osa(osa_ehr_kood="101019881-2140708").tahis == "17"


def test_ehr_rikasta_korter():
    e = ehr_api.parsi(EHR_JSON, EHR_ENERGIA)
    o = Objekt("x", ObjektiTyyp.KORTER)
    hoiatused = ehr_api.rikasta(o, e, e.leia_osa("17"), KP)
    assert o.pind_m2 == 44.1 and o.korrus == 5 and o.korruseid == 5 and o.lift is False
    assert o.energiaklass is None and any("10 aastat" in h for h in hoiatused)   # 2010 märgis aegunud
    assert o.allikad["pind_m2"].startswith("Ehitisregister (eluruum 17)")


def test_ehr_rikasta_terve_hoone():
    e = ehr_api.parsi(EHR_JSON, [])
    o = Objekt("x", ObjektiTyyp.ARIPIND)
    ehr_api.rikasta(o, e, None, KP)
    assert o.pind_m2 == 4529.8 and "suletud netopind" in o.allikad["pind_m2"]
    o2 = Objekt("x", ObjektiTyyp.KORTER)
    assert any("Korterit ei leitud" in h for h in ehr_api.rikasta(o2, e, None, KP))


def test_inads_ehitishoone_tunnus_on_ehr_kood():
    o = Objekt("x", ObjektiTyyp.KORTER, hooneosa_nr="55")
    inads.rikasta(o, INADS_JSON["addresses"][0])
    assert o.ehr_kood == "101019881" and o.katastritunnus is None
    assert o.osa_ehr_kood == "101019881-2140142"
    assert o.lat == pytest.approx(59.401086) and o.lon == pytest.approx(24.668053)


class KoguKlient(FakeKlient):
    """In-ADS + EHR + statistika + OSM ühes."""

    def json(self, url, params=None, **kw):
        if "inaadress" in url:
            assert params["address"] == "Ehitajate tee 35, Tallinn" and params["appartment"] == "55"
            return INADS_JSON
        if url.endswith("/building/v3/buildingData"):
            assert params == {"ehr_code": "101019881"}
            return EHR_JSON
        if "buildingRelatedEnergyCertificates" in url:
            return EHR_ENERGIA
        if "/document/v1/document/building/" in url:
            return EHR_DOK["101019881"]
        if "overpass" in url:
            return {"elements": [{"type": "node", "lat": 59.4015, "lon": 24.6690, "tags": {"highway": "bus_stop"}}]}
        return super().json(url, params, **kw)


def test_ainult_aadressist_korteri_hinnang(s, tmp_path):
    """Kasutaja annab ainult aadressi ja tüübi – kõik muu tuleb avaandmetest."""
    h = Hindaja(s, vorguta=True, vahemalu=tmp_path)
    h.vorguta = False
    h.klient = KoguKlient()
    h.ehr_api = ehr_api.EhrApi(h.klient, s)
    h.stat = StatAllikas(KatasterStatistika(h.klient, s), h.stat.fail)
    o = Objekt("Ehitajate tee 35-55, Tallinn", ObjektiTyyp.KORTER)
    hinnang = h.hinda(o, kuupäev=KP)
    assert o.pind_m2 == 45.7 and o.ehitusaasta == 1964 and o.korrus == 4 and o.asustusyksus == "Mustamäe linnaosa"
    assert o.kaugused_m["ühistransport"] < 100
    stat = next(t for t in hinnang.tulemused if t.meetod == "statistika")
    assert "ehitatud 1940–1970" in stat.selgitus[0]
    assert 100_000 < hinnang.turuväärtus < 140_000


# ---------------------------------------------------------------- maakataster (WFS)
from hindamisbot.allikad import kataster  # noqa: E402

KY_JSON = json.loads((FDIR / "kataster_89001_010_9900.json").read_text(encoding="utf-8"))
# Eramu EHR-vastus (kuju päris liidesest, väärtused Männi tee 3, Viimsi)
EHR_ERAMU = {"ehitis": {"ehitiseAndmed": {"ehrKood": "116012345", "nimetus": "Elamu", "kaosIdTxt": "Üksikelamu",
                                          "esmaneKasutus": "2001", "taisaadress": "Harju maakond, Viimsi vald, Haabneeme alevik, Männi tee 3"},
                        "ehitisePohiandmed": {"lift": "0", "maxKorrusteArv": "2", "suletud_netopind": "268.4"},
                        "ehitiseKasutusotstarbed": {"kasutusotstarve": [{"kaosIdTxt": "Üksikelamu", "eluruumidePind": "227.0"}]},
                        "ehitiseKatastriyksused": {"ehitiseKatastriyksus": [{"katastritunnus": "89001:010:9900"}]},
                        "ehitiseTehnilisedNaitajad": {"tehnilineNaitaja": [{"klKood": "KONS_KKONSTR", "nimetus": "kergplokk"}]},
                        "ehitiseKehand": {"kehand": [{"esmane_kasutus": "2001", "ehitiseOsad": {"ehitiseOsa": [
                            {"liik": "K", "tahis": "1", "ehrKood": "116012345-1", "ehitiseOsaPohiandmed": {"pind": "227.0"}}]}}]}}}


def test_kataster_parsi():
    ky = kataster.parsi(KY_JSON["features"][0]["properties"])
    assert ky.pindala_m2 == 1194 and ky.peamine_sihtotstarve == "elamumaa" and ky.sihtotstarbed_tekst == "elamumaa 100%"
    assert ky.omandivorm == "Eraomand" and ky.kinnistu_nr == "2707602" and ky.maks_hind == 148868
    o = Objekt("x", ObjektiTyyp.ERAMU)
    hoiatused = kataster.rikasta(o, ky)
    assert o.krundi_pind_m2 == 1194 and o.allikad["krundi_pind_m2"] == "Maakataster"
    assert any("ebatäpne" in h for h in hoiatused)


def test_kataster_vigane_tunnus_ei_tee_paringut(s):
    k = FakeKlient()
    assert kataster.Kataster(k, s).yksus("1' OR '1'='1") is None and not k.paringud


class EramuKlient(FakeKlient):
    def __init__(self, maa=False):
        super().__init__()
        self.maa = maa

    def json(self, url, params=None, **kw):
        if "inaadress" in url:
            if self.maa or params.get("features") == "KATASTRIYKSUS":
                return {"addresses": [{"liikVal": "KATASTRIYKSUS", "tunnus": "89001:010:9900",
                                       "maakond": "Harju maakond", "omavalitsus": "Viimsi vald",
                                       "asustusyksus": "Haabneeme alevik", "viitepunkt_b": "59.514344", "viitepunkt_l": "24.822230"}]}
            return {"addresses": [{"liikVal": "EHITISHOONE", "tunnus": "116012345", "maakond": "Harju maakond",
                                   "omavalitsus": "Viimsi vald", "asustusyksus": "Haabneeme alevik",
                                   "viitepunkt_b": "59.514344", "viitepunkt_l": "24.822230"}]}
        if url.endswith("/building/v3/buildingData"):
            return EHR_ERAMU
        if "buildingRelatedEnergyCertificates" in url:
            return []
        if "geoserver/kataster" in url:
            assert params["cql_filter"] == "tunnus='89001:010:9900'"
            return KY_JSON
        if "overpass" in url:
            return {"elements": []}
        return []


def _hindaja(s, tmp_path, klient):
    h = Hindaja(s, vorguta=True, vahemalu=tmp_path)
    h.vorguta = False
    h.klient = klient
    h.ehr_api = ehr_api.EhrApi(klient, s)
    h.kataster = kataster.Kataster(klient, s)
    return h


def test_eramu_ainult_aadressist(s, tmp_path):
    h = _hindaja(s, tmp_path, EramuKlient())
    o = Objekt("Männi tee 3, Viimsi", ObjektiTyyp.ERAMU)
    h.kogu(o, kuupäev=KP)
    assert o.pind_m2 == 227.0 and o.ehitusaasta == 2001 and o.krundi_pind_m2 == 1194
    assert o.katastritunnus == "89001:010:9900" and o.kinnistu_nr == "2707602" and o.omandivorm == "Eraomand"
    assert o.materjal == "kivi"


def test_maa_ainult_aadressist(s, tmp_path):
    h = _hindaja(s, tmp_path, EramuKlient(maa=True))
    o = Objekt("Männi tee 3, Viimsi", ObjektiTyyp.MAA)
    h.kogu(o, kuupäev=KP)
    assert o.krundi_pind_m2 == 1194 and o.sihtotstarve == "elamumaa" and o.maa_maksustamishind == 148868


# ---------------------------------------------------------------- objektitüübi tuvastamine
from hindamisbot.tuvastus import tuvasta  # noqa: E402


@pytest.mark.parametrize("kw,oodatud", [
    (dict(osa_liik="eluruum", osa_nr="55", otstarve="Muu kolme või enama korteriga elamu", eluruume=80), "korter"),
    (dict(osa_liik="mitteeluruum", osa_nr="2", otstarve="Hotell, motell, külalistemaja"), "aripind"),
    (dict(otstarve="Üksikelamu", eluruume=1), "eramu"),
    (dict(otstarve="Kahe korteriga elamu", eluruume=2), "eramu"),
    (dict(otstarve="Ridaelamu", eluruume=4), "eramu"),
    (dict(otstarve="Muu kolme või enama korteriga elamu", eluruume=80), "korter"),
    (dict(otstarve="Hotell, motell, külalistemaja"), "aripind"),
    (dict(otstarve="Büroohoone", kaos_kood="12201"), "aripind"),
    (dict(inads_liik="KATASTRIYKSUS", on_katastriyksus=True), "maa"),
])
def test_tuvasta(kw, oodatud):
    tyyp, põhjus, _ = tuvasta(**kw)
    assert tyyp.value == oodatud and põhjus


def test_tuvasta_kortermaja_ilma_numbrita_hoiatab():
    _, _, h = tuvasta(otstarve="Muu kolme või enama korteriga elamu", eluruume=80)
    assert any("korteri number" in x for x in h)


def test_tuvasta_ebaonnestub():
    tyyp, _, h = tuvasta()
    assert tyyp is None and h


def test_tuvastus_terviktoovoos(s, tmp_path):
    # korter: ainult aadress, tüüpi ei anta
    h = Hindaja(s, vorguta=True, vahemalu=tmp_path)
    h.vorguta = False
    h.klient = KoguKlient()
    h.ehr_api = ehr_api.EhrApi(h.klient, s)
    h.stat = StatAllikas(KatasterStatistika(h.klient, s), h.stat.fail)
    o = Objekt("Ehitajate tee 35-55, Tallinn")
    hinnang = h.hinda(o, kuupäev=KP)
    assert o.tyyp == ObjektiTyyp.KORTER and "eluruum" in o.tyyp_pohjendus and hinnang.turuväärtus
    # eramu ja maa
    o2 = Objekt("Männi tee 3, Viimsi")
    _hindaja(s, tmp_path, EramuKlient()).kogu(o2, kuupäev=KP)
    assert o2.tyyp == ObjektiTyyp.ERAMU and o2.krundi_pind_m2 == 1194
    o3 = Objekt("Männi tee 3, Viimsi")
    _hindaja(s, tmp_path, EramuKlient(maa=True)).kogu(o3, kuupäev=KP)
    assert o3.tyyp == ObjektiTyyp.MAA


def test_kasutaja_tyyp_on_ulimuslik(s, tmp_path):
    o = Objekt("Männi tee 3, Viimsi", ObjektiTyyp.ARIPIND)
    _hindaja(s, tmp_path, EramuKlient()).kogu(o, kuupäev=KP)
    assert o.tyyp == ObjektiTyyp.ARIPIND and o.tyyp_pohjendus is None


# ---------------------------------------------------------------- mitu hoonet samal aadressil + aadressisoovitused
HEKI = json.loads((FDIR / "inads_heki6.json").read_text(encoding="utf-8"))


class HekiKlient:
    def __init__(self):
        self.params = []

    def json(self, url, params=None, **_):
        self.params.append(params)
        return HEKI


def test_otsi_valib_hoone_kuhu_korter_kuulub():
    k = HekiKlient()
    kirje = inads.otsi(k, "https://inads", "Heki tee 6, Haabneeme", "68")
    assert kirje["tunnus"] == "120310725" and k.params[0]["results"] == 10
    assert inads.otsi(k, "https://inads", "Heki tee 6, Haabneeme", "1")["tunnus"] == "120310708"


def test_rikasta_heki_korter_68():
    o = Objekt("Heki tee 6-68, Haabneeme", hooneosa_nr="68")
    inads.rikasta(o, inads.otsi(HekiKlient(), "u", "Heki tee 6, Haabneeme", "68"))
    assert o.ehr_kood == "120310725" and o.osa_ehr_kood == "120310725-2546400"


def test_soovitused_liidavad_hooned_ja_katastri():
    s_ = inads.soovitused(HekiKlient(), "u", "Heki tee 6")
    assert len(s_) == 1
    g = s_[0]
    assert g["aadress"].endswith("Heki tee 6") and g["katastritunnus"] == "89001:010:1841"
    assert [h["ehr_kood"] for h in g["hooned"]] == ["120310708", "120310725"]
    assert ("68", "120310725-2546400") in g["hooned"][1]["osad"]
    assert inads.soovitused(HekiKlient(), "u", "He") == []


def test_osa_sort():
    assert sorted(["10", "2", "10A", "1"], key=inads.osa_sort) == ["1", "2", "10", "10A"]


def test_ehitusaasta_arvestus(s):
    # ehitusperioodi grupp → korrektsiooni ei lisata, aga see on kirjas
    api = KatasterStatistika(FakeKlient(), s)
    h = Hindaja(s, vorguta=True)
    h.stat = StatAllikas(api, h.stat.fail)
    o = korter(); o.asustusyksus = "Mustamäe linnaosa"
    t = next(x for x in h.hinda(o, kuupäev=KP).tulemused if x.meetod == "statistika")
    assert "1940–1970" in t.andmed["võrdlusgrupp"] and "sama ehitusperioodi" in t.andmed["ehitusaasta_arvestus"]
    assert not any(k.nimi == "Ehitusperiood" for k in t.korrektsioonid)
    # pinnavahemiku grupp (ehitusperioodi lahter peidetud) → ehitusaasta läheb korrektsiooniks
    o2 = korter(); o2.asustusyksus = "Mustamäe linnaosa"; o2.ehitusaasta = 1995
    t2 = next(x for x in h.hinda(o2, kuupäev=KP).tulemused if x.meetod == "statistika")
    assert "kõik ehitusaastad" in t2.andmed["võrdlusgrupp"]
    assert any(k.nimi == "Ehitusperiood" for k in t2.korrektsioonid)



# ---------------------------------------------------------------- ehitusaasta dokumentidest
@pytest.mark.parametrize("kood,esmane,oodatud_aasta,allikas_sisaldab,rek", [
    # 1964 paneelmaja: hilisemad kasutusload on rekonstrueerimise/ümberehituse omad → ehitusaasta jääb 1964
    ("101019881", 1964, 1964, "esmase kasutuselevõtu", 2026),
    # uusehitis: kasutusluba ehitise püstitamisel 2007 (ka siis, kui esmane kasutuselevõtt on puudu)
    # 2018 täpsustuseta kasutusteatis on 11 aastat hilisem → muudatus, mitte ehitusaasta
    ("120310725", None, 2007, "Kasutusluba ehitise püstitamisel nr 9410", 2018),
    ("120310725", 2006, 2007, "Kasutusluba ehitise püstitamisel", 2018),
    # dokumente pole → esmane kasutuselevõtt
    ("116012345", 2001, 2001, "esmase kasutuselevõtu", None),
])
def test_ehitusaasta_dokumentidest(kood, esmane, oodatud_aasta, allikas_sisaldab, rek):
    from hindamisbot.allikad.ehr_api import ehitusaasta_dokumentidest
    aasta, allikas, r = ehitusaasta_dokumentidest(EHR_DOK[kood], esmane)
    assert aasta == oodatud_aasta and allikas_sisaldab in allikas and r == rek


def test_ehitusaasta_ehitusloast_kui_kasutusluba_puudub():
    from hindamisbot.allikad.ehr_api import ehitusaasta_dokumentidest
    dok = [d for d in EHR_DOK["120310725"] if "Kasutusluba" not in d["documentType"]
           and d["documentType"] != "Kasutusteatis"]
    aasta, allikas, _ = ehitusaasta_dokumentidest(dok, None)
    assert aasta == 2004 and "Ehitusluba ehitise püstitamiseks nr 2295" in allikas


def test_aastavahetus_eesti_ajas():
    from hindamisbot.allikad.ehr_api import ehitusaasta_dokumentidest
    d = [{"documentType": "Kasutusluba ehitise püstitamisel", "date": "2009-12-31T22:30:00.000+00:00",
          "documentState": "DO_DOKUSEIS_REG_KANTUD", "documentNumber": "1"}]
    assert ehitusaasta_dokumentidest(d, None)[0] == 2010


def test_rikasta_ehitusaasta_allikas_ja_rekonstrueerimine():
    from hindamisbot.allikad.ehr_api import rakenda_dokumendid
    e = ehr_api.parsi(EHR_JSON, [])
    rakenda_dokumendid(e, EHR_DOK["101019881"])
    o = Objekt("x", ObjektiTyyp.KORTER)
    h = ehr_api.rikasta(o, e, e.leia_osa("17"), KP)
    assert o.ehitusaasta == 1964 and "esmase kasutuselevõtu" in o.allikad["ehitusaasta"]
    assert o.rekonstrueeritud == 2026 and any("ümberehituse" in x for x in h)


def test_kasitsi_ehitusaasta_kasutatakse_kui_registris_puudub(s):
    hj = Hindaja(s, vorguta=True)

    def uus():
        return Objekt("Puuduva tn 99-1, Tallinn", ObjektiTyyp.KORTER, maakond="Harju maakond",
                      omavalitsus="Tallinn", asustusyksus="Mustamäe", pind_m2=51.2, korrus=3, korruseid=5)
    ilma = hj.hinda(uus(), KP)
    assert ilma.objekt.ehitusaasta is None
    teade = next(x for x in ilma.hoiatused if "ehitusaasta puudub" in x)
    assert "Refine" in i18n.tõlgi(teade, "en")
    o = uus()
    o.maara("ehitusaasta", 2015, "sisend")
    h = hj.hinda(o, KP)
    assert not any("ehitusaasta puudub" in x for x in h.hoiatused)
    assert any(t.andmed.get("ehitusaasta_allikas") == "sisend" for t in h.tulemused)
    assert h.turuväärtus != ilma.turuväärtus
