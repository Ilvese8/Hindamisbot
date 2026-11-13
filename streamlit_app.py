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

from hindamisbot import aruanne, i18n, joonis
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
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
:root{
  --navy:#1E2B3A; --navy2:#273A4F; --lime:#D7FF6E; --lime2:#C6F24F; --tint:#F1F7FD; --sky:#CFE6F5;
  --tekst:#1E2B3A; --hall:#5D6B7A; --joon:#E3EAF1; --valge:#FFFFFF;
}
html, body, [data-testid="stAppViewContainer"]{
  background:linear-gradient(180deg, var(--navy) 0, var(--navy) 470px, var(--tint) 470px, var(--tint) 100%);
}
[data-testid="stAppViewContainer"] *{font-family:'Inter',system-ui,-apple-system,sans-serif;}
[data-testid="stIconMaterial"], [class*="material-symbols"]{font-family:'Material Symbols Rounded'!important;}
#MainMenu, footer, [data-testid="stToolbar"], [data-testid="stDecoration"], [data-testid="stHeader"]{display:none!important;}
.block-container{padding-top:1.1rem; max-width:1080px;}
:focus-visible{outline:2px solid var(--lime)!important; outline-offset:2px;}

.topbar{display:flex; align-items:center; gap:.6rem; color:#fff; font-weight:700; font-size:1.08rem;}
.topbar svg{width:28px; height:28px}
[data-testid="stButtonGroup"] button{border-radius:8px!important; border:1px solid rgba(255,255,255,.35)!important;
  background:transparent!important; color:#fff!important; font-weight:600; min-width:2.8rem;}
[data-testid="stButtonGroup"] button[aria-checked="true"]{background:#fff!important; color:var(--navy)!important;
  border-color:#fff!important;}

.hero{margin:3rem 0 2.2rem; max-width:720px;}
.hero h1{font-family:'Inter',sans-serif!important; font-weight:800; color:#F2F7FB!important;
  font-size:clamp(2.3rem,5.6vw,3.9rem); line-height:1.05; letter-spacing:-.03em; margin:0 0 1rem;}
.hero p{color:#C9D6E3; font-size:1.12rem; line-height:1.55; max-width:56ch; margin:0;}

.st-key-vorm{background:var(--valge); border:0!important; border-radius:18px!important; padding:1.5rem 1.5rem 1.2rem!important;
  box-shadow:0 24px 60px -24px rgba(16,28,42,.45), 0 2px 6px rgba(16,28,42,.06);}
label, [data-testid="stWidgetLabel"] p{color:var(--tekst)!important; font-weight:600!important; font-size:.88rem!important;}
[data-baseweb="select"]>div, [data-baseweb="input"]>div{border-radius:10px!important; border-color:#D5DEE7!important; background:#fff!important;}
[data-testid="stExpander"] details{border-radius:10px!important; border-color:var(--joon)!important; background:#FAFCFE;}
.flabel{color:var(--tekst); font-weight:600; font-size:.88rem; margin:0 0 .4rem;}
.flabel span{color:var(--hall); font-weight:400; margin-left:.4rem;}
.stButton>button[kind="primary"]{background:var(--lime); color:var(--navy); border:0; border-radius:999px; height:3.2rem;
  font-weight:700; font-size:1.05rem; box-shadow:0 8px 20px -10px rgba(150,190,40,.9);}
.stButton>button[kind="primary"] p{color:var(--navy)!important; font-weight:700;}
.stButton>button[kind="primary"]:hover{background:var(--lime2); color:var(--navy);}
.stButton>button[kind="primary"]:disabled{background:#EDF1F5; color:#93A0AD; box-shadow:none;}
.stButton>button[kind="primary"]:disabled p{color:#93A0AD!important;}
.lahtiytlus{color:var(--hall); font-size:.8rem; margin:.3rem 0 0; text-align:center;}
.stDownloadButton>button{border-radius:999px; border:1.5px solid var(--navy); color:var(--navy); background:#fff; font-weight:600;}
.stDownloadButton>button:hover{background:var(--navy); color:#fff;}

.result{margin:2.2rem 0 1rem; background:#fff; border-radius:22px; overflow:hidden;
  box-shadow:0 30px 70px -36px rgba(16,28,42,.45); display:grid; grid-template-columns:minmax(0,1.1fr) minmax(0,.9fr);}
.plaanikoht{background:var(--navy); padding:14px; display:flex; flex-direction:column; justify-content:center; position:relative;}
.plaanikoht figcaption{font-size:.74rem; color:#8FA5BA; margin:6px 4px 0;}
.plaan{width:100%; height:auto; display:block; border-radius:12px;}
.plaan .koord{font-size:9px;} .plaan .mõõt{font-size:10.5px; font-weight:600;} .plaan .n{font-size:11px; font-weight:800;}
.plaan .tunnus{font-size:12px; font-weight:700;}
.plaan .piir{stroke-dasharray:1; stroke-dashoffset:1; animation:joonista 1.8s cubic-bezier(.6,.05,.3,1) .15s forwards;}
.plaan .hoone, .plaan .punkt{opacity:0; animation:ilmu .5s ease 1.7s forwards;}
@keyframes joonista{to{stroke-dashoffset:0}} @keyframes ilmu{to{opacity:1}}
@media (prefers-reduced-motion:reduce){.plaan .piir{animation:none; stroke-dashoffset:0} .plaan .hoone,.plaan .punkt{animation:none; opacity:1}}
.puudub{display:grid; place-items:center; min-height:300px; color:#8FA5BA; font-size:.9rem;}

.tempel{padding:26px 26px 20px; display:flex; flex-direction:column;}
.tempel .silt{color:var(--hall); font-size:.92rem; font-weight:500;}
.tempel .v{font-weight:800; color:var(--navy); font-size:clamp(2.4rem,5vw,3.4rem); letter-spacing:-.035em; line-height:1;
  margin:.4rem 0 .35rem;}
.tempel .yhik{display:inline-block; background:var(--lime); color:var(--navy); font-weight:700; font-size:.84rem;
  padding:.28rem .7rem; border-radius:999px; margin-bottom:.9rem;}
.mõõtjoon{width:100%; height:auto; display:block;}
.tempel .vahemik{display:flex; justify-content:space-between; font-size:.84rem; color:var(--hall); font-weight:600; margin-top:-2px;}
.tempel dl{margin:1.1rem 0 0; display:grid; grid-template-columns:auto 1fr; border-top:1px solid var(--joon);}
.tempel dt, .tempel dd{margin:0; padding:9px 0; border-bottom:1px solid var(--joon); font-size:.86rem;}
.tempel dt{color:var(--hall); padding-right:18px; white-space:nowrap;}
.tempel dd{color:var(--tekst); font-weight:600; overflow-wrap:anywhere; text-align:right;}
.tempel dd small{display:block; font-weight:400; color:var(--hall); font-size:.76rem;}

.methods{display:grid; grid-template-columns:repeat(auto-fit,minmax(200px,1fr)); gap:14px; margin:0 0 1.2rem;}
.methods .m{background:#fff; border-radius:16px; padding:16px 18px; box-shadow:0 1px 3px rgba(16,28,42,.06);}
.methods .n{font-size:.84rem; color:var(--hall); font-weight:500;}
.methods .v{font-weight:800; color:var(--navy); font-size:1.4rem; margin:.25rem 0 .55rem; letter-spacing:-.02em;}
.methods .w{height:6px; background:var(--tint); border-radius:9px; overflow:hidden;}
.methods .w i{display:block; height:100%; background:var(--navy); border-radius:9px;}
.methods .k{font-size:.78rem; color:var(--hall); margin-top:.45rem;}

.tyhi{margin:2.2rem 0 1rem; border-radius:22px; background:#fff; padding:2.4rem 1rem; text-align:center; color:var(--hall);
  box-shadow:0 1px 3px rgba(16,28,42,.06); font-weight:500;}
.tyhi svg{width:150px; height:auto; display:block; margin:0 auto 1rem;}
.fail{margin:2.2rem 0 1rem; background:#fff; border-radius:18px; padding:1.2rem 1.4rem; border-left:6px solid #E5484D;}
.fail h3{margin:0 0 .3rem; font-size:1.1rem; color:var(--navy)!important;}
.foot{color:var(--hall); font-size:.78rem; margin:2.6rem 0 1rem; line-height:1.6; max-width:72ch;}
@media (max-width:760px){
  .result{grid-template-columns:1fr}
  html, body, [data-testid="stAppViewContainer"]{background:linear-gradient(180deg, var(--navy) 0, var(--navy) 420px, var(--tint) 420px);}
  .tempel dd{text-align:left}
}
</style>
""", unsafe_allow_html=True)


# ------------------------------------------------------------------ keel
if "keel" not in st.session_state:
    st.session_state.keel = "en" if st.query_params.get("lang") == "en" else "et"

vasak, parem = st.columns([5, 1.3], vertical_alignment="center")
with vasak:
    st.markdown("""<div class="topbar"><svg viewBox="0 0 30 30" aria-hidden="true">
      <path d="M4 22 L9 6 L25 9 L22 25 Z" fill="rgba(215,255,110,.12)" stroke="#D7FF6E" stroke-width="2" stroke-linejoin="round"/>
      <rect x="11" y="12" width="8" height="7" fill="#F2F7FB"/></svg>
      <span>Hindamisbot</span></div>""", unsafe_allow_html=True)
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
        "control": {"backgroundColor": "#FFFFFF", "border": "1px solid #B9C1BA", "borderRadius": "8px",
                    "minHeight": "46px", "boxShadow": "none", "paddingLeft": "6px", "cursor": "text",
                    "fontFamily": "Inter, system-ui, -apple-system, sans-serif", "fontSize": "15px"},
        "placeholder": {"color": "#8A908B"},
        "singleValue": {"color": "#18222D", "fontWeight": 600},
        "input": {"color": "#1B1F1D"},
        "menuList": {"backgroundColor": "#FFFFFF", "borderRadius": "8px", "padding": "4px",
                     "fontFamily": "Inter, system-ui, -apple-system, sans-serif", "fontSize": "14px"},
        "option": {"color": "#18222D", "backgroundColor": "#FFFFFF", "highlightColor": "#EEF0EC"},
        "optionEmpty": "hidden",
    },
}

eur = aruanne.eur
e = html.escape

# ------------------------------------------------------------------ päis ja sisend
st.markdown(f"""<div class="hero"><h1>{e(T('pealkiri'))}</h1><p>{e(T('sissejuhatus'))}</p></div>""",
            unsafe_allow_html=True)

with st.container(border=True, key="vorm"):
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
    st.markdown(f'<p class="lahtiytlus">{e(T("lahtiütlus"))}</p>', unsafe_allow_html=True)

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
if not h:
    st.markdown(f"""<div class="tyhi"><svg viewBox="0 0 120 90" aria-hidden="true">
      <rect width="120" height="90" rx="12" fill="#1E2B3A"/>
      <path d="M18 72 L30 16 L100 24 L92 76 Z" fill="rgba(215,255,110,.08)" stroke="#D7FF6E" stroke-width="2" stroke-dasharray="5 5"/>
      <rect x="46" y="36" width="26" height="20" fill="none" stroke="#F2F7FB" stroke-width="1.6" stroke-dasharray="4 4"/>
    </svg>{e(T('tühi_plaan'))}</div>""", unsafe_allow_html=True)
if h:
    o = h.objekt
    aadr = e(o.normaliseeritud_aadress or o.aadress)
    if h.turuväärtus:
        madal, kõrge = h.vahemik
        pind_alus = o.krundi_pind_m2 if o.tyyp and o.tyyp.value == "maa" else o.pind_m2
        plaan = joonis.plaan_svg(o.krundi_kuju, o.hoone_kuju, o.katastritunnus, K, teema="tume")
        plaan_html = (f'<figure style="margin:0">{plaan}<figcaption>{e(T("mõõtkavas"))}</figcaption></figure>'
                      if plaan else f'<div class="puudub">{e(T("plaan_puudub"))}</div>')
        read = [(T("aadress"), aadr, "")]
        if o.tyyp:
            read.append((T("liik"), e(i18n.väärtus(o.tyyp.value, K).capitalize())
                         + (f" {e(str(o.hooneosa_nr))}" if o.hooneosa_nr else ""), ""))
        if o.pind_m2:
            read.append((T("pind").replace(" m²", ""), f"{o.pind_m2:g} m²", e(i18n.väärtus(o.allikad.get('pind_m2', ''), K))))
        if o.krundi_pind_m2:
            read.append((T("krundi_pind"), f"{o.krundi_pind_m2:,.0f} m²".replace(",", " "), e(o.katastritunnus or "")))
        if o.ehitusaasta:
            read.append((T("ehitusaasta"), str(o.ehitusaasta),
                         e(i18n.väärtus(o.allikad.get("ehitusaasta", ""), K).replace("Ehitisregister: ", "")
                           .replace("Building Register: ", ""))))
        if o.korrus:
            read.append((T("korrus"), f"{o.korrus}" + (f" / {o.korruseid}" if o.korruseid else ""), ""))
        if o.energiaklass:
            read.append((T("energiaklass"), e(o.energiaklass), ""))
        stat = next((t for t in h.tulemused if t.meetod == "statistika" and t.kehtiv), None)
        if stat and stat.andmed.get("grupp"):
            grupp = stat.andmed["grupp"]
            read.append((T("võrreldi"), e(i18n._grupp(grupp) if K == "en" else grupp),
                         e(f"{stat.andmed['grupp_piirkond']}, {stat.andmed['grupp_periood']}, "
                           f"{stat.andmed['grupp_tehinguid']} " + ("tehingut" if K == "et" else "transactions"))))
        read.append((T("hinnatud"), h.hindamise_kuupäev.strftime("%d.%m.%Y"), ""))
        dl = "".join(f"<dt>{a_}</dt><dd>{b_}{f'<small>{c_}</small>' if c_ else ''}</dd>" for a_, b_, c_ in read)
        meetodid = "".join(
            f'<div class="m"><div class="n">{e(i18n.meetod(t.meetod, K))}</div><div class="v">{eur(t.väärtus)}</div>'
            f'<div class="w"><i style="width:{h.kaalud.get(t.meetod, 0) * 100:.0f}%"></i></div>'
            f'<div class="k">{T("kaal")} {h.kaalud.get(t.meetod, 0):.0%}</div></div>'
            for t in h.tulemused if t.kehtiv)
        ühik = f"{eur(h.turuväärtus / pind_alus)}/m²" if pind_alus else ""
        st.markdown(f"""<section class="result" aria-label="{e(T('turuväärtus'))}">
  <div class="plaanikoht">{plaan_html}</div>
  <div class="tempel">
    <div class="silt">{e(T('turuväärtus'))}</div>
    <div class="v">{eur(h.turuväärtus)}</div>
    {f'<div><span class="yhik">{ühik}</span></div>' if ühik else ''}
    {joonis.mõõtjoon_svg(madal, h.turuväärtus, kõrge, joon="#9AAAB9", märk="#1E2B3A")}
    <div class="vahemik"><span>{eur(madal)}</span><span>{eur(kõrge)}</span></div>
    <dl>{dl}</dl>
  </div></section>
<div class="methods">{meetodid}</div>""", unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="fail"><h3>{aadr}</h3>{e(T("ei_õnnestunud"))}</div>', unsafe_allow_html=True)

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

st.markdown(f'<div class="foot">{e(T("jalus", a=T("allikad")))}<br>{e(T("lahtiütlus"))}</div>',
            unsafe_allow_html=True)
