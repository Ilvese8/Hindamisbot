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
from hindamisbot.__main__ import _failinimi
from hindamisbot.hindaja import Hindaja
from hindamisbot.mudel import Objekt, ObjektiTyyp, Seisukord
from hindamisbot.seadistused import lae

MAX_HINNANGUID_TUNNIS = 20          # ühe brauserisessiooni piirang – kaitseb avalikke liideseid
TÜÜBID = {"Tuvasta automaatselt": None, "Korter": ObjektiTyyp.KORTER, "Eramu": ObjektiTyyp.ERAMU,
          "Maa": ObjektiTyyp.MAA, "Äripind": ObjektiTyyp.ARIPIND}
ALLIKAD = ("Maa- ja Ruumiamet (In-ADS, maakataster, tehingute andmebaas), ehitisregister, "
           "© OpenStreetMap kaastöötajad")

st.set_page_config(page_title="Kinnisvara esmane hinnang", page_icon="🏠", layout="centered")


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


st.title("Kinnisvara turuväärtuse esmane hinnang")
st.caption("Testversioon. Automaatne hinnang avaandmete põhjal – **ei ole eksperthinnang**. "
           "Tulemuse peab üle kontrollima kutsetunnistusega hindaja.")

with st.form("sisend"):
    aadress = st.text_input("Aadress", placeholder="nt Ehitajate tee 35-55, Tallinn  või  Männi tee 3, Viimsi")
    c1, c2 = st.columns(2)
    tyyp_valik = c1.selectbox("Objekti liik", list(TÜÜBID))
    seisukord = c2.selectbox("Seisukord", ["teadmata"] + [s.value for s in Seisukord])
    with st.expander("Täpsusta (valikuline) – tühjad väljad täidetakse avaandmetest"):
        d1, d2, d3 = st.columns(3)
        pind = d1.number_input("Pind m²", min_value=0.0, value=0.0, step=1.0)
        krunt = d2.number_input("Krundi pind m²", min_value=0.0, value=0.0, step=10.0)
        aasta = d3.number_input("Ehitusaasta", min_value=0, max_value=date.today().year + 3, value=0)
        e1, e2, e3 = st.columns(3)
        korrus = e1.number_input("Korrus", min_value=0, max_value=60, value=0)
        energia = e2.selectbox("Energiaklass", ["teadmata", *"ABCDEFGH"])
        osa = e3.text_input("Hooneosa nr", help="Korteri või äripinna number, kui see pole aadressis")
    saada = st.form_submit_button("Hinda", type="primary", width="stretch")

if saada:
    if len(aadress.strip()) < 4:
        st.warning("Sisesta aadress.")
        st.stop()
    if not piirang_ok():
        st.error(f"Ühest brauserist saab teha kuni {MAX_HINNANGUID_TUNNIS} hinnangut tunnis. Proovi hiljem uuesti.")
        st.stop()
    o = Objekt(aadress=aadress.strip(), tyyp=TÜÜBID[tyyp_valik])
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
            h = hindaja().hinda(o, kuupäev=date.today(), korter=osa.strip() or None)
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
