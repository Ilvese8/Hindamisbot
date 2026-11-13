"""Hinnangu aruande mustand: Markdown ja Word (.docx)."""
from __future__ import annotations

from pathlib import Path

from . import i18n
from .mudel import Hinnang

MEETODI_NIMI = {"statistika": "Turustatistika meetod", "võrdlus": "Võrdlusmeetod", "kulu": "Kulumeetod"}
VÄLJAD = [(k, i18n.väli(k)) for k in (
    "normaliseeritud_aadress", "tyyp", "maakond", "omavalitsus", "asustusyksus", "katastritunnus", "ehr_kood",
    "hooneosa", "ehitise_otstarve", "pind_m2", "krundi_pind_m2", "sihtotstarbed", "omandivorm", "kinnistu_nr",
    "maa_maksustamishind", "katastri_markus", "ehitusaasta", "rekonstrueeritud", "korruseid", "korrus", "tube",
    "materjal", "lift", "energiaklass", "seisukord", "lat", "lon")]
KONTROLL = i18n.kontroll("et")
PIIRANGUD = i18n.piirangud("et")


def eur(v) -> str:
    return "–" if v is None else f"{v:,.0f} €".replace(",", " ")


def _väli(o, k, keel="et"):
    v = getattr(o, k)
    if hasattr(v, "value"):
        v = v.value
    if v is None or v == "":
        return v
    if keel == "en":
        if k == "tyyp":
            v = i18n.väärtus(v, "en") + (f" (detected: {i18n.tõlgi(o.tyyp_pohjendus, 'en')})" if o.tyyp_pohjendus else "")
        elif k in ("seisukord", "materjal", "lift", "omandivorm", "sihtotstarbed", "katastri_markus", "hooneosa"):
            v = i18n.väärtus(v, "en")
        return v
    if k == "tyyp" and o.tyyp_pohjendus:
        v = f"{v} (tuvastatud: {o.tyyp_pohjendus})"
    if k == "lift":
        v = i18n.väärtus(v, "et")
    return v


def andmeread(o, keel="et") -> list[tuple[str, str, str]]:
    """(tunnus, väärtus, allikas) – veebiliidese ja aruande jaoks."""
    return [(i18n.väli(k, keel), str(_väli(o, k, keel)), i18n.väärtus(o.allikad.get(k, "sisend"), keel))
            for k, _ in VÄLJAD if _väli(o, k, keel) not in (None, "")]


def markdown(h: Hinnang, keel: str = "et") -> str:
    T, tr = (lambda _võti, **kw: i18n.T(_võti, keel, **kw)), (lambda s: i18n.tõlgi(s, keel))
    o = h.objekt
    L = [f"# {T('ar_pealkiri')}", "", f"**{T('ar_mustand')}**", "",
         f"{T('ar_kuupäev')}: {h.hindamise_kuupäev.isoformat()}  ", f"{T('ar_objekt')}: {o.normaliseeritud_aadress or o.aadress}",
         "", f"## {T('ar_kokkuvõte')}", ""]
    if h.turuväärtus:
        L += [f"| {T('ar_näitaja')} | {T('väärtus')} |", "|---|---|",
              f"| {T('turuväärtus')} | **{eur(h.turuväärtus)}** |",
              f"| {T('vahemik')} | {eur(h.vahemik[0])} – {eur(h.vahemik[1])} |"]
        pind = o.krundi_pind_m2 if o.tyyp and o.tyyp.value == "maa" else o.pind_m2
        if pind:
            L.append(f"| {T('ühikuhind')} | {eur(h.turuväärtus / pind)}/m² |")
    else:
        L.append(T("ei_õnnestunud"))
    L += ["", f"## {T('ar_hinnatav')}", "", f"| {T('tunnus')} | {T('väärtus')} | {T('allikas')} |", "|---|---|---|"]
    L += [f"| {a} | {b} | {c} |" for a, b, c in andmeread(o, keel)]
    if o.kaugused_m:
        L += ["", f"### {T('ar_asukoht')}", "", f"| {T('ar_kategooria')} | {T('ar_kaugus')} |", "|---|---|"]
        L += [f"| {i18n.väärtus(k, keel)} | {v} m |" for k, v in sorted(o.kaugused_m.items())]
    L += ["", f"## {T('ar_meetodid')}", ""]
    for t in h.tulemused:
        if not (t.kehtiv or t.hoiatused):
            continue
        L += [f"### {i18n.meetod(t.meetod, keel)}", ""]
        if t.kehtiv:
            L += [T("ar_tulemus", v=eur(t.väärtus), m2=eur(t.eur_m2), a=eur(t.vahemik[0]), b=eur(t.vahemik[1]),
                    u=t.usaldus, k=h.kaalud.get(t.meetod, 0)), ""]
        L += [f"- {tr(x)}" for x in t.selgitus]
        if t.korrektsioonid:
            L += ["", f"| {T('korrektsioon')} | {T('tegur')} | {T('põhjendus')} |", "|---|---|---|"]
            L += [f"| {i18n.korrektsioon(k.nimi, keel)} | {k.tegur:.3f} | {i18n.väärtus(k.põhjendus, keel)} |"
                  for k in t.korrektsioonid]
        vo = t.andmed.get("võrdlusobjektid")
        if vo:
            L += ["", "| " + " | ".join(T("ar_vo_päis").split("|")) + " |", "|---" * 10 + "|"]
            for r in vo:
                L.append(f"| {r['aadress']} | {r['kaugus_m'] if r['kaugus_m'] is not None else '–'} m | "
                         f"{r['kuupäev']} | {i18n.väärtus(r['liik'], keel)} | {r['pind_m2']:.0f} | {eur(r['hind'])} | "
                         f"{r['eur_m2']} | {i18n.vo_korrektsioonid(r['korrektsioonid'], keel)} | {r['korr_eur_m2']} | "
                         f"{r['allikas']} |")
        L.append("")
    tk = (h.turg or {}).get(keel)
    if tk and not tk.tyhi:
        L += [f"## {T('turu_kontekst')}", "", f"| {T('näitaja')} | {T('väärtus')} | {T('allikas')} |", "|---|---|---|"]
        L += [f"| {r.silt} | {r.väärtus} | {f'[{r.allikas}]({r.url})' if r.url else r.allikas} |" for r in tk.read]
        L.append("")
    if h.hoiatused:
        L += [f"## {T('hoiatused')}", ""] + [f"- {tr(x)}" for x in h.hoiatused] + [""]
    L += [f"## {T('ar_kontroll')}", ""] + [f"- [ ] {x}" for x in i18n.kontroll(keel)]
    L += ["", f"## {T('ar_piirangud')}", "", i18n.piirangud(keel), ""]
    return "\n".join(L)


def docx(h: Hinnang, tee: Path, keel: str = "et") -> Path:
    from docx import Document
    from docx.shared import Pt, RGBColor

    T, tr = (lambda _võti, **kw: i18n.T(_võti, keel, **kw)), (lambda s: i18n.tõlgi(s, keel))
    o = h.objekt
    d = Document()
    st = d.styles["Normal"]
    st.font.name = "Calibri"
    st.font.size = Pt(10.5)
    d.add_heading(T("ar_pealkiri"), 0)
    p = d.add_paragraph()
    r = p.add_run(T("ar_mustand"))
    r.bold = True
    r.font.color.rgb = RGBColor(0xB0, 0x3A, 0x2E)
    d.add_paragraph(f"{T('ar_kuupäev')}: {h.hindamise_kuupäev.isoformat()}\n"
                    f"{T('ar_objekt')}: {o.normaliseeritud_aadress or o.aadress}")

    def tabel(päis, read):
        t = d.add_table(rows=1, cols=len(päis))
        t.style = "Light Grid Accent 1"
        for i, x in enumerate(päis):
            t.rows[0].cells[i].text = str(x)
        for rida in read:
            c = t.add_row().cells
            for i, x in enumerate(rida):
                c[i].text = "" if x is None else str(x)
        d.add_paragraph()

    d.add_heading(T("ar_kokkuvõte"), 1)
    if h.turuväärtus:
        read = [[T("turuväärtus"), eur(h.turuväärtus)], [T("vahemik"), f"{eur(h.vahemik[0])} – {eur(h.vahemik[1])}"]]
        pind = o.krundi_pind_m2 if o.tyyp and o.tyyp.value == "maa" else o.pind_m2
        if pind:
            read.append([T("ühikuhind"), f"{eur(h.turuväärtus / pind)}/m²"])
        tabel([T("ar_näitaja"), T("väärtus")], read)
    else:
        d.add_paragraph(T("ei_õnnestunud"))

    d.add_heading(T("ar_hinnatav"), 1)
    tabel([T("tunnus"), T("väärtus"), T("allikas")], andmeread(o, keel))
    if o.kaugused_m:
        d.add_heading(T("ar_asukoht"), 2)
        tabel([T("ar_kategooria"), T("ar_kaugus") + " (m)"],
              [(i18n.väärtus(k, keel), v) for k, v in sorted(o.kaugused_m.items())])

    d.add_heading(T("ar_meetodid"), 1)
    for t in h.tulemused:
        if not (t.kehtiv or t.hoiatused):
            continue
        d.add_heading(i18n.meetod(t.meetod, keel), 2)
        if t.kehtiv:
            d.add_paragraph(T("ar_tulemus_docx", v=eur(t.väärtus), m2=eur(t.eur_m2), a=eur(t.vahemik[0]),
                              b=eur(t.vahemik[1]), u=t.usaldus, k=h.kaalud.get(t.meetod, 0)))
        for x in t.selgitus:
            d.add_paragraph(tr(x), style="List Bullet")
        if t.korrektsioonid:
            tabel([T("korrektsioon"), T("tegur"), T("põhjendus")],
                  [[i18n.korrektsioon(k.nimi, keel), f"{k.tegur:.3f}", i18n.väärtus(k.põhjendus, keel)]
                   for k in t.korrektsioonid])
        vo = t.andmed.get("võrdlusobjektid")
        if vo:
            tabel(T("ar_vo_päis").split("|")[:9],
                  [[r["aadress"], r["kaugus_m"], r["kuupäev"], i18n.väärtus(r["liik"], keel), f"{r['pind_m2']:.0f}",
                    eur(r["hind"]), r["eur_m2"], i18n.vo_korrektsioonid(r["korrektsioonid"], keel), r["korr_eur_m2"]]
                   for r in vo])
    tk = (h.turg or {}).get(keel)
    if tk and not tk.tyhi:
        d.add_heading(T("turu_kontekst"), 1)
        tabel([T("näitaja"), T("väärtus"), T("allikas")], [[r.silt, r.väärtus, r.allikas] for r in tk.read])
    if h.hoiatused:
        d.add_heading(T("hoiatused"), 1)
        for x in h.hoiatused:
            d.add_paragraph(tr(x), style="List Bullet")
    d.add_heading(T("ar_kontroll"), 1)
    for x in i18n.kontroll(keel):
        d.add_paragraph("☐ " + x)
    d.add_heading(T("ar_piirangud"), 1)
    d.add_paragraph(i18n.piirangud(keel))
    d.save(tee)
    return tee
