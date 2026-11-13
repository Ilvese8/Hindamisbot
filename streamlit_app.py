"""Hindamisboti veebiliides (Streamlit). Käivitamine kohalikult: streamlit run streamlit_app.py"""
from __future__ import annotations

import json
import tempfile
import time
from datetime import date
from pathlib import Path

import pandas as pd
import streamlit as st

from hindamisbot import aruanne
from streamlit_searchbox import st_searchbox

from hindamisbot.__main__ import _failinimi
from hindamisbot.allikad import inads
from hindamisbot.allikad.http import Klient
from hindamisbot.hindaja import Hindaja
from hindamisbot.mudel import Objekt, ObjektiTyyp, Seisukord
from hindamisbot.seadistused import lae

MAX_HINNANGUID_TUNNIS = 20          # ühe brauserisessiooni piirang – kaitseb avalikke liideseid
TÜÜBID = {"Tuvasta automaatselt": None, "Korter": ObjektiTyyp.KORTER, "Eramu": ObjektiTyyp.ERAMU,
          "Maa": ObjektiTyyp.MAA, "Äripind": ObjektiTyyp.ARIPIND}
ALLIKAD = ("Maa- ja Ruumiamet (In-ADS, maakataster, tehingute andmebaas), ehitisregister, "
           "© OpenStreetMap kaastöötajad")

st.set_page_config(page_title="Sinu kinnisvara turuväärtus", page_icon="🏠", layout="centered")


@st.cache_resource
def hindaja() -> Hindaja:
    return Hindaja(lae(Path(__file__).parent / "seadistused.toml"))


def eur(v) -> str:
    return aruanne.eur(v)


def piirang_ok() -> bool:
    nüüd = time.time()
    ajad = [t for t in st.session_state.get("ajad", []) if nüüd - t < 3600]
    st.session_state["ajad"] = ajad
    if len(ajad) >= MAX_HINNANGUID_TUNNIS:
        return False
    ajad.append(nüüd)
    return True


st.title("Sinu kinnisvara turuväärtus")
st.caption("Testversioon. Automaatne hinnang avaandmete põhjal – **ei ole eksperthinnang**. "
           "Tulemuse peab üle kontrollima kutsetunnistusega hindaja.")


@st.cache_resource
def otsingu_klient() -> Klient:
    li = lae(Path(__file__).parent / "seadistused.toml")["liidesed"]
    return Klient(li["kasutajaagent"], viivitus_s=0.2, timeout_s=10)


@st.cache_data(ttl=86400, show_spinner=False)
def _soovitused(tekst: str) -> list[dict]:
    try:
        return inads.soovitused(otsingu_klient(), hindaja().s["liidesed"]["inads_url"], tekst)
    except ConnectionError:
        return []


def otsi_aadressi(tekst: str) -> list[tuple[str, str]]:
    tulemused = _soovitused(tekst)
    st.session_state.setdefault("aadressid", {}).update({g["aadress"]: g for g in tulemused})
    return [(g["aadress"], g["aadress"]) for g in tulemused]


valitud = st_searchbox(otsi_aadressi, label="Aadress", key="aadress",
                       placeholder="Hakka trükkima, nt Heki tee 6 Haabneeme", debounce=300,
                       help="Vali aadress pakutud valikutest – nii on aadress kindlasti õige.")
g = st.session_state.get("aadressid", {}).get(valitud) if valitud else None

osa_valik = None
if g:
    osad = sorted({(t_, k_, h_["ehr_kood"]) for h_ in g["hooned"] for t_, k_ in h_["osad"]},
                  key=lambda x: (inads.osa_sort(x[0]), x[2]))
    if osad:
        mitu_hoonet = len({x[2] for x in osad}) > 1
        sildid = ["Terve hoone / krunt"] + [f"{t_}" + (f"  (hoone {e_})" if mitu_hoonet and
                                                      sum(1 for y in osad if y[0] == t_) > 1 else "")
                                             for t_, k_, e_ in osad]
        i = st.selectbox("Korter / hooneosa", range(len(sildid)), format_func=lambda i: sildid[i],
                         index=1 if len(osad) > 2 else 0,
                         help="Kortermajas vali korteri number. Eramu või terve hoone puhul jäta „Terve hoone / krunt“.")
        osa_valik = osad[i - 1] if i else None

c1, c2 = st.columns(2)
tyyp_valik = c1.selectbox("Objekti liik", list(TÜÜBID))
seisukord = c2.selectbox("Seisukord", ["teadmata"] + [s.value for s in Seisukord])
with st.expander("Täpsusta (valikuline) – tühjad väljad täidetakse avaandmetest"):
    d1, d2, d3 = st.columns(3)
    pind = d1.number_input("Pind m²", min_value=0.0, value=0.0, step=1.0)
    krunt = d2.number_input("Krundi pind m²", min_value=0.0, value=0.0, step=10.0)
    aasta = d3.number_input("Ehitusaasta", min_value=0, max_value=date.today().year + 3, value=0)
    e1, e2 = st.columns(2)
    korrus = e1.number_input("Korrus", min_value=0, max_value=60, value=0)
    energia = e2.selectbox("Energiaklass", ["teadmata", *"ABCDEFGH"])
saada = st.button("Hinda", type="primary", width="stretch", disabled=g is None)

if saada and g:
    if not piirang_ok():
        st.error(f"Ühest brauserist saab teha kuni {MAX_HINNANGUID_TUNNIS} hinnangut tunnis. Proovi hiljem uuesti.")
        st.stop()
    o = Objekt(aadress=g["aadress"], tyyp=TÜÜBID[tyyp_valik])
    # Valitud aadressi andmed on In-ADS-ist – bot ei pea aadressi enam ära arvama
    o.maara("normaliseeritud_aadress", g["aadress"], "In-ADS")
    o.maara("lat", g["lat"], "In-ADS")
    o.maara("lon", g["lon"], "In-ADS")
    korter = None
    if osa_valik:
        korter, osa_kood, ehr_kood = osa_valik
        o.maara("hooneosa_nr", korter, "valik")
        o.maara("osa_ehr_kood", osa_kood, "In-ADS")
        o.maara("ehr_kood", ehr_kood, "In-ADS")
    elif len(g["hooned"]) == 1:
        o.maara("ehr_kood", g["hooned"][0]["ehr_kood"], "In-ADS")
    if g["katastritunnus"]:
        o.maara("katastritunnus", g["katastritunnus"], "In-ADS")
    for väli, v in (("pind_m2", pind), ("krundi_pind_m2", krunt), ("ehitusaasta", int(aasta)),
                    ("korrus", int(korrus))):
        if v:
            o.maara(väli, v, "sisend")
    if energia != "teadmata":
        o.maara("energiaklass", energia, "sisend")
    if seisukord != "teadmata":
        o.maara("seisukord", Seisukord(seisukord), "sisend")
    with st.spinner("Otsin avaandmetest ja arvutan…"):
        try:
            h = hindaja().hinda(o, kuupäev=date.today(), korter=korter)
        except Exception as e:  # noqa: BLE001 – testversioonis näitame vea kasutajale
            st.error(f"Hindamine ebaõnnestus: {e}")
            st.stop()
    st.session_state["hinnang"] = h

h = st.session_state.get("hinnang")
if h:
    o = h.objekt
    st.divider()
    st.subheader(o.normaliseeritud_aadress or o.aadress)
    if o.tyyp:
        st.caption(f"Objekti liik: **{o.tyyp.value}**" + (f" – {o.tyyp_pohjendus}" if o.tyyp_pohjendus else ""))
    if h.turuväärtus:
        pind = o.krundi_pind_m2 if o.tyyp and o.tyyp.value == "maa" else o.pind_m2
        m1, m2, m3 = st.columns(3)
        m1.metric("Hinnanguline turuväärtus", eur(h.turuväärtus))
        m2.metric("Vahemik", f"{eur(h.vahemik[0])} – {eur(h.vahemik[1])}".replace(" €", "") + " €")
        if pind:
            m3.metric("Ühikuhind", f"{eur(h.turuväärtus / pind)}/m²")
        stat = next((t for t in h.tulemused if t.meetod == "statistika" and t.kehtiv), None)
        if stat and stat.andmed.get("võrdlusgrupp"):
            st.info(f"**Võrreldi:** {stat.andmed['võrdlusgrupp']}"
                    + (f"  \n**Arvestatud:** {stat.andmed['ehitusaasta_arvestus']}"
                       if stat.andmed.get("ehitusaasta_arvestus") else ""))
        read = [{"Meetod": aruanne.MEETODI_NIMI[t.meetod], "Väärtus": eur(t.väärtus), "€/m²": eur(t.eur_m2),
                 "Kaal": f"{h.kaalud.get(t.meetod, 0):.0%}"} for t in h.tulemused if t.kehtiv]
        st.dataframe(pd.DataFrame(read), hide_index=True, width="stretch")
    else:
        st.error("Turuväärtust ei õnnestunud määrata – vaata hoiatusi allpool.")

    andmed = [{"Tunnus": n, "Väärtus": str(aruanne._väli(o, k)), "Allikas": o.allikad.get(k, "sisend")}
              for k, n in aruanne.VÄLJAD if aruanne._väli(o, k) not in (None, "")]
    with st.expander("Objekti andmed ja allikad", expanded=not h.turuväärtus):
        st.dataframe(pd.DataFrame(andmed), hide_index=True, width="stretch")
        if o.kaugused_m:
            st.write("Lähimad teenused: " + ", ".join(f"{k} {v} m" for k, v in sorted(o.kaugused_m.items())))
    with st.expander("Meetodite selgitus"):
        for t in h.tulemused:
            if t.kehtiv:
                st.markdown(f"**{aruanne.MEETODI_NIMI[t.meetod]}**")
                for x in t.selgitus:
                    st.markdown(f"- {x}")
                if t.korrektsioonid:
                    st.dataframe(pd.DataFrame([{"Korrektsioon": k.nimi, "Tegur": round(k.tegur, 3),
                                                "Põhjendus": k.põhjendus} for k in t.korrektsioonid]),
                                 hide_index=True, width="stretch")
    if h.hoiatused:
        with st.expander(f"Hoiatused ({len(h.hoiatused)})"):
            for x in h.hoiatused:
                st.markdown(f"- {x}")

    nimi = _failinimi(o.aadress)
    with tempfile.TemporaryDirectory() as tmp:
        docx_bytes = aruanne.docx(h, Path(tmp) / f"{nimi}.docx").read_bytes()
    k1, k2 = st.columns(2)
    k1.download_button("Laadi alla aruanne (Word)", docx_bytes, f"{nimi}.docx",
                       "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                       width="stretch")
    k2.download_button("Laadi alla aruanne (Markdown)", aruanne.markdown(h).encode("utf-8"), f"{nimi}.md",
                       "text/markdown", width="stretch")

st.divider()
st.caption(f"Andmed: {ALLIKAD}. Müügiportaalide andmeid ei kasutata.")
