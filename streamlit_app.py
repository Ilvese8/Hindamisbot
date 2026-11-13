"""Hindamisboti veebiliides (Streamlit). Käivitamine kohalikult: streamlit run streamlit_app.py"""
from __future__ import annotations

import html
import tempfile
import time
from datetime import date
from pathlib import Path

import pandas as pd
import streamlit as st
from streamlit_searchbox import st_searchbox

from hindamisbot import aruanne, i18n
from hindamisbot.__main__ import _failinimi
from hindamisbot.allikad import inads
from hindamisbot.allikad.http import Klient
from hindamisbot.hindaja import Hindaja
from hindamisbot.mudel import Objekt, ObjektiTyyp, Seisukord
from hindamisbot.seadistused import lae

MAX_HINNANGUID_TUNNIS = 20          # ühe brauserisessiooni piirang – kaitseb avalikke liideseid

st.set_page_config(page_title="Sinu kinnisvara turuväärtus · Your property's market value", page_icon="🏡",
                   layout="centered", initial_sidebar_state="collapsed")

# ------------------------------------------------------------------ kujundus
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,600;9..144,700&family=Inter:wght@400;500;600&display=swap');
:root{
  --pine:#12372A; --moss:#436850; --sage:#ADBC9F; --paper:#F7F5EF; --sand:#EDE8DC; --ink:#1B1F1D;
  --amber:#D9902F; --muted:#6B726D; --line:#DDD7C9;
}
html, body, [data-testid="stAppViewContainer"]{background:var(--paper);}
[data-testid="stAppViewContainer"] *{font-family:'Inter',system-ui,sans-serif;}
[data-testid="stIconMaterial"], .material-symbols-rounded, [class*="material-symbols"]{font-family:'Material Symbols Rounded'!important;}
#MainMenu, footer, [data-testid="stToolbar"], [data-testid="stDecoration"], [data-testid="stHeader"]{display:none!important;}
.block-container{padding-top:1.4rem; max-width:860px;}
h1,h2,h3,.serif{font-family:'Fraunces',Georgia,serif!important; color:var(--pine); letter-spacing:-.01em;}

.topbar{display:flex; align-items:center; gap:.6rem; color:var(--pine); font-weight:600; letter-spacing:.02em;}
.topbar .mark{width:30px;height:30px;border-radius:9px;background:var(--pine);display:grid;place-items:center;}
.topbar .mark svg{width:18px;height:18px}
.topbar small{color:var(--muted); font-weight:500; letter-spacing:.06em; text-transform:uppercase; font-size:.68rem}

.hero{margin:2.2rem 0 1.4rem;}
.hero h1{font-size:clamp(2.2rem,5.4vw,3.5rem); line-height:1.02; margin:0 0 .8rem; font-weight:700;}
.hero h1 em{font-style:italic; color:var(--moss); font-weight:600;}
.hero p{color:var(--muted); font-size:1.02rem; max-width:620px; margin:0;}
.hero p strong{color:var(--ink);}

[data-testid="stVerticalBlockBorderWrapper"]{background:#fff; border:1px solid var(--line)!important;
  border-radius:20px!important; box-shadow:0 1px 0 rgba(18,55,42,.04), 0 18px 40px -28px rgba(18,55,42,.35);}
label, [data-testid="stWidgetLabel"] p{color:var(--pine)!important; font-weight:600!important; font-size:.86rem!important;}
[data-baseweb="select"]>div, [data-baseweb="input"]>div{border-radius:12px!important; border-color:var(--line)!important; background:#FCFBF8!important;}
[data-testid="stExpander"] details{border-radius:14px!important; border-color:var(--line)!important; background:#FCFBF8;}

.stButton>button[kind="primary"]{background:var(--pine); border:0; border-radius:14px; height:3.1rem;
  font-weight:600; letter-spacing:.02em; font-size:1rem; transition:transform .12s ease, background .2s ease;}
.stButton>button[kind="primary"]:hover{background:var(--moss); transform:translateY(-1px);}
.stButton>button[kind="primary"]:disabled{background:var(--sand); color:var(--muted);}
.stDownloadButton>button{border-radius:12px; border:1px solid var(--pine); color:var(--pine); background:transparent; font-weight:600;}
.stDownloadButton>button:hover{background:var(--pine); color:#fff;}
[data-testid="stSegmentedControl"] button{border-radius:999px!important;}

.result{margin-top:1.6rem; border-radius:24px; overflow:hidden; background:var(--pine); color:#EEF2EC;
  box-shadow:0 30px 60px -36px rgba(18,55,42,.7);}
.result .head{padding:1.6rem 1.8rem .4rem;}
.result .eyebrow{font-size:.72rem; letter-spacing:.14em; text-transform:uppercase; color:var(--sage);}
.result .addr{font-family:'Fraunces',serif; font-size:1.25rem; margin:.25rem 0 0; color:#fff;}
.result .value{font-family:'Fraunces',serif; font-weight:700; font-size:clamp(2.6rem,7vw,4.2rem); line-height:1; margin:1.2rem 0 .3rem; color:#fff;}
.result .sub{color:var(--sage); font-size:.95rem;}
.range{padding:1.2rem 1.8rem 1.5rem;}
.range .bar{position:relative; height:8px; border-radius:99px; background:linear-gradient(90deg,#2E5A47,#ADBC9F,#2E5A47);}
.range .dot{position:absolute; top:50%; width:18px; height:18px; border-radius:50%; background:var(--amber);
  border:3px solid #fff; transform:translate(-50%,-50%); box-shadow:0 0 0 6px rgba(217,144,47,.25);}
.range .ends{display:flex; justify-content:space-between; font-size:.82rem; color:var(--sage); margin-top:.6rem;}
.chips{display:flex; flex-wrap:wrap; gap:.45rem; padding:0 1.8rem 1.6rem;}
.chip{background:rgba(255,255,255,.08); border:1px solid rgba(255,255,255,.14); color:#EEF2EC; padding:.32rem .7rem;
  border-radius:999px; font-size:.8rem;}
.chip b{color:#fff; font-weight:600;}
.basis{background:#fff; border:1px solid var(--line); border-left:4px solid var(--amber); border-radius:14px;
  padding:1rem 1.2rem; margin:1rem 0; color:var(--ink); font-size:.92rem;}
.basis div{margin:.15rem 0;} .basis span{color:var(--muted);}
.methods{display:grid; grid-template-columns:repeat(auto-fit,minmax(180px,1fr)); gap:.8rem; margin:.4rem 0 1rem;}
.m{background:#fff; border:1px solid var(--line); border-radius:16px; padding:1rem 1.1rem;}
.m .n{font-size:.78rem; color:var(--muted); text-transform:uppercase; letter-spacing:.08em;}
.m .v{font-family:'Fraunces',serif; font-size:1.5rem; color:var(--pine); margin:.3rem 0 .1rem;}
.m .w{height:5px; background:var(--sand); border-radius:9px; overflow:hidden; margin-top:.5rem;}
.m .w i{display:block; height:100%; background:var(--moss);}
.m .k{font-size:.78rem; color:var(--muted); margin-top:.35rem;}
.fail{margin-top:1.6rem; background:#fff; border:1px solid #E6C9C2; border-left:4px solid #B03A2E; border-radius:16px; padding:1.1rem 1.3rem;}
.fail h3{margin:0 0 .3rem; font-size:1.2rem;}
.flabel{color:var(--pine); font-weight:600; font-size:.86rem; margin:0 0 .35rem; display:flex;
  justify-content:space-between; gap:1rem; flex-wrap:wrap;}
.flabel span{color:var(--muted); font-weight:400; font-size:.78rem;}
iframe[title*="searchbox"]{border-radius:12px; background:transparent;}
.foot{color:var(--muted); font-size:.78rem; text-align:center; margin:2.4rem 0 1rem; line-height:1.6;}
</style>
""", unsafe_allow_html=True)


# ------------------------------------------------------------------ keel
if "keel" not in st.session_state:
    st.session_state.keel = "en" if st.query_params.get("lang") == "en" else "et"

vasak, parem = st.columns([5, 1.3], vertical_alignment="center")
with vasak:
    st.markdown("""<div class="topbar"><div class="mark"><svg viewBox="0 0 24 24" fill="none" stroke="#F7F5EF"
      stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 11l9-7 9 7"/><path d="M5 10v10h14V10"/>
      <path d="M10 20v-6h4v6"/></svg></div><div>Hindamisbot<br><small>Avaandmed · Open data</small></div></div>""",
                unsafe_allow_html=True)
with parem:
    valik = st.segmented_control("Keel / Language", ["ET", "EN"], default=st.session_state.keel.upper(),
                                 key="keelevalik", label_visibility="collapsed")
    if valik and valik.lower() != st.session_state.keel:
        st.session_state.keel = valik.lower()
        st.query_params["lang"] = st.session_state.keel
        st.rerun()

K = st.session_state.keel


def T(võti, **kw):
    return i18n.T(võti, K, **kw)


# ------------------------------------------------------------------ abifunktsioonid
@st.cache_resource
def hindaja() -> Hindaja:
    return Hindaja(lae(Path(__file__).parent / "seadistused.toml"))


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


def piirang_ok() -> bool:
    nüüd = time.time()
    ajad = [t for t in st.session_state.get("ajad", []) if nüüd - t < 3600]
    st.session_state["ajad"] = ajad
    if len(ajad) >= MAX_HINNANGUID_TUNNIS:
        return False
    ajad.append(nüüd)
    return True


# Otsingukast elab oma iframe'is – lehe CSS sinna ei ulatu, seega stiil antakse komponendile endale
OTSINGU_STIIL = {
    "wrapper": {"backgroundColor": "transparent"},
    "dropdown": {"width": 0, "height": 0, "fill": "transparent"},
    "clear": {"icon": "cross", "clearable": "always", "width": 14, "height": 14, "stroke": "#6B726D",
              "stroke-width": 2.5},
    "searchbox": {
        "control": {"backgroundColor": "#FCFBF8", "border": "1px solid #DDD7C9", "borderRadius": "12px",
                    "minHeight": "46px", "boxShadow": "none", "paddingLeft": "6px", "cursor": "text",
                    "fontFamily": "Inter, system-ui, -apple-system, sans-serif", "fontSize": "15px"},
        "placeholder": {"color": "#8A908B"},
        "singleValue": {"color": "#12372A", "fontWeight": 500},
        "input": {"color": "#1B1F1D"},
        "menuList": {"backgroundColor": "#FFFFFF", "borderRadius": "12px", "padding": "4px",
                     "fontFamily": "Inter, system-ui, -apple-system, sans-serif", "fontSize": "14px"},
        "option": {"color": "#1B1F1D", "backgroundColor": "#FFFFFF", "highlightColor": "#EDE8DC"},
        "optionEmpty": "hidden",
    },
}

eur = aruanne.eur
e = html.escape

# ------------------------------------------------------------------ päis ja sisend
pealkiri = T("pealkiri")
sõnad = pealkiri.rsplit(" ", 1)
st.markdown(f"""<div class="hero"><h1>{e(sõnad[0])} <em>{e(sõnad[1])}</em></h1>
<p>{T('alapealkiri').replace('**', '<strong>', 1).replace('**', '</strong>', 1)}</p></div>""",
            unsafe_allow_html=True)

with st.container(border=True):
    st.markdown(f'<div class="flabel">{T("aadress")}<span>{T("aadress_abi")}</span></div>', unsafe_allow_html=True)
    valitud = st_searchbox(otsi_aadressi, label=None, key="aadress", placeholder=T("aadress_koht"),
                           debounce=300, style_overrides=OTSINGU_STIIL)
    g = st.session_state.get("aadressid", {}).get(valitud) if valitud else None

    osa_valik = None
    if g:
        osad = sorted({(t_, k_, h_["ehr_kood"]) for h_ in g["hooned"] for t_, k_ in h_["osad"]},
                      key=lambda x: (inads.osa_sort(x[0]), x[2]))
        if osad:
            mitu_hoonet = len({x[2] for x in osad}) > 1
            sildid = [T("terve_hoone")] + [
                t_ + (f"  ({T('hoone')} {e_})" if mitu_hoonet and sum(1 for y in osad if y[0] == t_) > 1 else "")
                for t_, k_, e_ in osad]
            i = st.selectbox(T("osa"), range(len(sildid)), format_func=lambda i: sildid[i],
                             index=1 if len(osad) > 2 else 0, help=T("osa_abi"))
            osa_valik = osad[i - 1] if i else None

    c1, c2 = st.columns(2)
    tyybid = [None, ObjektiTyyp.KORTER, ObjektiTyyp.ERAMU, ObjektiTyyp.MAA, ObjektiTyyp.ARIPIND]
    tyyp = c1.selectbox(T("liik"), tyybid,
                        format_func=lambda x: T("tuvasta") if x is None else i18n.väärtus(x.value, K).capitalize())
    seisukorrad = [None] + list(Seisukord)
    seisukord = c2.selectbox(T("seisukord"), seisukorrad,
                             format_func=lambda x: T("teadmata") if x is None else i18n.väärtus(x.value, K))
    with st.expander(T("täpsusta")):
        d1, d2, d3 = st.columns(3)
        pind = d1.number_input(T("pind"), min_value=0.0, value=0.0, step=1.0)
        krunt = d2.number_input(T("krunt"), min_value=0.0, value=0.0, step=10.0)
        aasta = d3.number_input(T("ehitusaasta"), min_value=0, max_value=date.today().year + 3, value=0)
        e1, e2 = st.columns(2)
        korrus = e1.number_input(T("korrus"), min_value=0, max_value=60, value=0)
        energia = e2.selectbox(T("energiaklass"), [None, *"ABCDEFGH"],
                               format_func=lambda x: T("teadmata") if x is None else x)
    saada = st.button(T("hinda"), type="primary", width="stretch", disabled=g is None)

if saada and g:
    if not piirang_ok():
        st.error(T("piirang", n=MAX_HINNANGUID_TUNNIS))
        st.stop()
    o = Objekt(aadress=g["aadress"], tyyp=tyyp)
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
    if energia:
        o.maara("energiaklass", energia, "sisend")
    if seisukord:
        o.maara("seisukord", seisukord, "sisend")
    with st.spinner(T("arvutan")):
        try:
            h = hindaja().hinda(o, kuupäev=date.today(), korter=korter)
        except Exception as err:  # noqa: BLE001 – testversioonis näitame vea kasutajale
            st.error(T("viga", e=err))
            st.stop()
    st.session_state["hinnang"] = h

# ------------------------------------------------------------------ tulemus
h = st.session_state.get("hinnang")
if h:
    o = h.objekt
    aadr = e(o.normaliseeritud_aadress or o.aadress)
    if h.turuväärtus:
        madal, kõrge = h.vahemik
        asend = 50 if kõrge == madal else max(4, min(96, (h.turuväärtus - madal) / (kõrge - madal) * 100))
        pind_alus = o.krundi_pind_m2 if o.tyyp and o.tyyp.value == "maa" else o.pind_m2
        chips = []
        if o.tyyp:
            chips.append(i18n.väärtus(o.tyyp.value, K).capitalize())
        if o.hooneosa_nr:
            chips.append(f"{'Nr' if K == 'et' else 'No.'} <b>{e(str(o.hooneosa_nr))}</b>")
        if o.pind_m2:
            chips.append(f"<b>{o.pind_m2:g}</b> m²")
        if o.krundi_pind_m2 and o.tyyp and o.tyyp.value in ("eramu", "maa"):
            chips.append(f"{T('krunt').replace(' m²', '')} <b>{o.krundi_pind_m2:,.0f}</b> m²".replace(",", " "))
        if o.ehitusaasta:
            chips.append(f"{T('ehitusaasta')} <b>{o.ehitusaasta}</b>")
        if o.korrus:
            chips.append(f"{T('korrus')} <b>{o.korrus}</b>" + (f" / {o.korruseid}" if o.korruseid else ""))
        if o.energiaklass:
            chips.append(f"{T('energiaklass')} <b>{e(o.energiaklass)}</b>")
        ühik = f" · {eur(h.turuväärtus / pind_alus)}/m²" if pind_alus else ""
        st.markdown(f"""
<div class="result">
  <div class="head">
    <div class="eyebrow">{T('turuväärtus')}</div>
    <div class="addr">{aadr}</div>
    <div class="value">{eur(h.turuväärtus)}</div>
    <div class="sub">{T('vahemik')} {eur(madal)} – {eur(kõrge)}{ühik}</div>
  </div>
  <div class="range"><div class="bar"><div class="dot" style="left:{asend:.0f}%"></div></div>
    <div class="ends"><span>{eur(madal)}</span><span>{eur(kõrge)}</span></div></div>
  <div class="chips">{''.join(f'<span class="chip">{c}</span>' for c in chips)}</div>
</div>""", unsafe_allow_html=True)

        stat = next((t for t in h.tulemused if t.meetod == "statistika" and t.kehtiv), None)
        if stat and stat.andmed.get("võrdlusgrupp"):
            read = [f"<div><span>{T('võrreldi')}:</span> {e(i18n._grupp(stat.andmed['võrdlusgrupp']) if K == 'en' else stat.andmed['võrdlusgrupp'])}</div>"]
            if stat.andmed.get("ehitusaasta_arvestus"):
                read.append(f"<div><span>{T('arvestatud')}:</span> {e(i18n.tõlgi(stat.andmed['ehitusaasta_arvestus'], K))}</div>")
            if stat.andmed.get("ehitusaasta_allikas"):
                read.append(f"<div><span>{T('aasta_allikas')}:</span> {e(i18n.väärtus(stat.andmed['ehitusaasta_allikas'], K))}</div>")
            st.markdown(f'<div class="basis">{"".join(read)}</div>', unsafe_allow_html=True)

        kaardid = "".join(
            f'<div class="m"><div class="n">{e(i18n.meetod(t.meetod, K))}</div><div class="v">{eur(t.väärtus)}</div>'
            f'<div class="k">{eur(t.eur_m2)}/m² · {T("kaal").lower()} {h.kaalud.get(t.meetod, 0):.0%}</div>'
            f'<div class="w"><i style="width:{h.kaalud.get(t.meetod, 0) * 100:.0f}%"></i></div></div>'
            for t in h.tulemused if t.kehtiv)
        st.markdown(f'<div class="methods">{kaardid}</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="fail"><h3>{aadr}</h3>{T("ei_õnnestunud")}</div>', unsafe_allow_html=True)

    with st.expander(T("andmed"), expanded=not h.turuväärtus):
        st.dataframe(pd.DataFrame(aruanne.andmeread(o, K), columns=[T("tunnus"), T("väärtus"), T("allikas")]),
                     hide_index=True, width="stretch")
        if o.kaugused_m:
            st.caption(f"{T('teenused')}: " + ", ".join(f"{i18n.väärtus(k, K)} {v} m"
                                                       for k, v in sorted(o.kaugused_m.items())))
    with st.expander(T("selgitus")):
        for t in h.tulemused:
            if t.kehtiv:
                st.markdown(f"**{i18n.meetod(t.meetod, K)}**")
                for x in t.selgitus:
                    st.markdown(f"- {i18n.tõlgi(x, K)}")
                if t.korrektsioonid:
                    st.dataframe(pd.DataFrame([{T("korrektsioon"): i18n.korrektsioon(k.nimi, K),
                                                T("tegur"): round(k.tegur, 3),
                                                T("põhjendus"): i18n.väärtus(k.põhjendus, K)}
                                               for k in t.korrektsioonid]), hide_index=True, width="stretch")
    if h.hoiatused:
        with st.expander(f"{T('hoiatused')} ({len(h.hoiatused)})", expanded=not h.turuväärtus):
            for x in h.hoiatused:
                st.markdown(f"- {i18n.tõlgi(x, K)}")

    nimi = _failinimi(o.aadress) + ("_en" if K == "en" else "")
    with tempfile.TemporaryDirectory() as tmp:
        docx_bytes = aruanne.docx(h, Path(tmp) / f"{nimi}.docx", K).read_bytes()
    k1, k2 = st.columns(2)
    k1.download_button(T("laadi_word"), docx_bytes, f"{nimi}.docx",
                       "application/vnd.openxmlformats-officedocument.wordprocessingml.document", width="stretch")
    k2.download_button(T("laadi_md"), aruanne.markdown(h, K).encode("utf-8"), f"{nimi}.md", "text/markdown",
                       width="stretch")

st.markdown(f'<div class="foot">{e(T("jalus", a=T("allikad")))}</div>', unsafe_allow_html=True)
