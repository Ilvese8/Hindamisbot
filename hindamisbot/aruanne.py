"""Hinnangu aruande mustand: Markdown ja Word (.docx)."""
from __future__ import annotations

from pathlib import Path

from .mudel import Hinnang

MEETODI_NIMI = {"statistika": "Turustatistika meetod", "võrdlus": "Võrdlusmeetod", "kulu": "Kulumeetod"}
VÄLJAD = [
    ("normaliseeritud_aadress", "Aadress"), ("tyyp", "Objekti liik"), ("maakond", "Maakond"),
    ("omavalitsus", "Omavalitsus"), ("asustusyksus", "Asustusüksus"), ("katastritunnus", "Katastritunnus"),
    ("ehr_kood", "EHR kood"), ("hooneosa", "Hooneosa"), ("ehitise_otstarve", "Ehitise otstarve"),
    ("pind_m2", "Pind (m²)"), ("krundi_pind_m2", "Krundi pind (m²)"),
    ("sihtotstarbed", "Sihtotstarve"), ("omandivorm", "Omandivorm"), ("kinnistu_nr", "Kinnistu (registriosa nr)"),
    ("maa_maksustamishind", "Maa maksustamishind (€)"), ("katastri_markus", "Katastri märge"), ("ehitusaasta", "Ehitusaasta"), ("rekonstrueeritud", "Hilisem ümberehitus/muudatus (kasutusluba)"), ("korruseid", "Korruseid"),
    ("korrus", "Korrus"), ("tube", "Tube"), ("materjal", "Materjal"), ("lift", "Lift"), ("energiaklass", "Energiaklass"),
    ("seisukord", "Seisukord"), ("lat", "Laiuskraad"), ("lon", "Pikkuskraad"),
]
KONTROLL = [
    "Objekt on paikvaatlusel üle vaadatud ja seisukord vastab sisendile.",
    "Kinnistusraamatu väljavõte on kontrollitud: II jagu (omanik), III jagu (servituudid, kasutusõigused), "
    "IV jagu (hüpoteegid, märked). Bot neid andmeid ei kogu.",
    "Ehitisregistri andmed (pind, kasutusluba, otstarve) vastavad tegelikkusele.",
    "Planeeringud ja kitsendused on kontrollitud (Geoportaal, KOV).",
    "Võrdlusobjektid on üle vaadatud ja sobivad; korrektsioonid on põhjendatud.",
    "Seadistuste korrektsioonitegurid on hindaja poolt üle vaadatud ja põhjendatud.",
    "Lõplik turuväärtus ja selle põhjendus on hindaja otsus (EVS 875).",
]
PIIRANGUD = (
    "See dokument on automaatselt koostatud esmase hinnangu mustand. See ei ole eksperthinnang "
    "EVS 875 tähenduses enne, kui kutsetunnistusega hindaja on andmed ja järeldused üle kontrollinud ning "
    "aruande allkirjastanud. Kasutatud on avalikke koondandmeid (Maa- ja Ruumiameti hinnastatistika ja "
    "hinnaindeks, In-ADS, ehitisregister, OpenStreetMap) ning hindaja sisestatud võrdlusobjekte. "
    "Müügiportaalide andmeid automaatselt ei koguta."
)


def eur(v) -> str:
    return "–" if v is None else f"{v:,.0f} €".replace(",", " ")


def _väli(o, k):
    v = getattr(o, k)
    if hasattr(v, "value"):
        v = v.value
    if k == "tyyp" and v and o.tyyp_pohjendus:
        v = f"{v} (tuvastatud: {o.tyyp_pohjendus})"
    return v


def markdown(h: Hinnang) -> str:
    o = h.objekt
    L = [f"# Kinnisvara turuväärtuse esmane hinnang", "",
         f"**MUSTAND – automaatne hinnang, vajab hindaja kontrolli**", "",
         f"Hindamise kuupäev: {h.hindamise_kuupäev.isoformat()}  ", f"Objekt: {o.normaliseeritud_aadress or o.aadress}",
         "", "## Kokkuvõte", ""]
    if h.turuväärtus:
        L += [f"| Näitaja | Väärtus |", "|---|---|",
              f"| Hinnanguline turuväärtus | **{eur(h.turuväärtus)}** |",
              f"| Vahemik | {eur(h.vahemik[0])} – {eur(h.vahemik[1])} |"]
        pind = o.krundi_pind_m2 if o.tyyp and o.tyyp.value == "maa" else o.pind_m2
        if pind:
            L.append(f"| Ühikuhind | {eur(h.turuväärtus / pind)}/m² |")
    else:
        L.append("Turuväärtust ei õnnestunud määrata – vt hoiatusi.")
    L += ["", "## Hinnatav objekt", "", "| Tunnus | Väärtus | Allikas |", "|---|---|---|"]
    for k, nimi in VÄLJAD:
        v = _väli(o, k)
        if v not in (None, ""):
            L.append(f"| {nimi} | {v} | {o.allikad.get(k, 'sisend')} |")
    if o.kaugused_m:
        L += ["", "### Asukoht (lähimad teenused, OpenStreetMap)", "", "| Kategooria | Kaugus |", "|---|---|"]
        L += [f"| {k} | {v} m |" for k, v in sorted(o.kaugused_m.items())]
    L += ["", "## Meetodid", ""]
    for t in h.tulemused:
        if not (t.kehtiv or t.hoiatused):
            continue
        L += [f"### {MEETODI_NIMI.get(t.meetod, t.meetod)}", ""]
        if t.kehtiv:
            L.append(f"Tulemus: **{eur(t.väärtus)}** ({eur(t.eur_m2)}/m²), vahemik "
                     f"{eur(t.vahemik[0])} – {eur(t.vahemik[1])}, usaldus {t.usaldus:.2f}, "
                     f"kaal lepitamisel {h.kaalud.get(t.meetod, 0):.0%}.")
            L.append("")
        L += [f"- {x}" for x in t.selgitus]
        if t.korrektsioonid:
            L += ["", "| Korrektsioon | Tegur | Põhjendus |", "|---|---|---|"]
            L += [f"| {k.nimi} | {k.tegur:.3f} | {k.põhjendus} |" for k in t.korrektsioonid]
        vo = t.andmed.get("võrdlusobjektid")
        if vo:
            L += ["", "| Aadress | Kaugus | Kuupäev | Liik | m² | Hind | €/m² | Korrektsioonid | Korr. €/m² | Allikas |",
                  "|---|---|---|---|---|---|---|---|---|---|"]
            for r in vo:
                L.append(f"| {r['aadress']} | {r['kaugus_m'] if r['kaugus_m'] is not None else '–'} m | "
                         f"{r['kuupäev']} | {r['liik']} | {r['pind_m2']:.0f} | {eur(r['hind'])} | {r['eur_m2']} | "
                         f"{r['korrektsioonid']} | {r['korr_eur_m2']} | {r['allikas']} |")
        L.append("")
    if h.hoiatused:
        L += ["## Hoiatused", ""] + [f"- {x}" for x in h.hoiatused] + [""]
    L += ["## Hindaja kontrollnimekiri", ""] + [f"- [ ] {x}" for x in KONTROLL]
    L += ["", "## Eeldused ja piirangud", "", PIIRANGUD, ""]
    return "\n".join(L)


def docx(h: Hinnang, tee: Path) -> Path:
    from docx import Document
    from docx.shared import Pt, RGBColor

    o = h.objekt
    d = Document()
    st = d.styles["Normal"]
    st.font.name = "Calibri"
    st.font.size = Pt(10.5)
    d.add_heading("Kinnisvara turuväärtuse esmane hinnang", 0)
    p = d.add_paragraph()
    r = p.add_run("MUSTAND – automaatne hinnang, vajab hindaja kontrolli")
    r.bold = True
    r.font.color.rgb = RGBColor(0xB0, 0x3A, 0x2E)
    d.add_paragraph(f"Hindamise kuupäev: {h.hindamise_kuupäev.isoformat()}\nObjekt: {o.normaliseeritud_aadress or o.aadress}")

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

    d.add_heading("Kokkuvõte", 1)
    if h.turuväärtus:
        read = [["Hinnanguline turuväärtus", eur(h.turuväärtus)],
                ["Vahemik", f"{eur(h.vahemik[0])} – {eur(h.vahemik[1])}"]]
        pind = o.krundi_pind_m2 if o.tyyp and o.tyyp.value == "maa" else o.pind_m2
        if pind:
            read.append(["Ühikuhind", f"{eur(h.turuväärtus / pind)}/m²"])
        tabel(["Näitaja", "Väärtus"], read)
    else:
        d.add_paragraph("Turuväärtust ei õnnestunud määrata – vt hoiatusi.")

    d.add_heading("Hinnatav objekt", 1)
    tabel(["Tunnus", "Väärtus", "Allikas"],
          [[n, _väli(o, k), o.allikad.get(k, "sisend")] for k, n in VÄLJAD if _väli(o, k) not in (None, "")])
    if o.kaugused_m:
        d.add_heading("Asukoht (lähimad teenused, OpenStreetMap)", 2)
        tabel(["Kategooria", "Kaugus (m)"], sorted(o.kaugused_m.items()))

    d.add_heading("Meetodid", 1)
    for t in h.tulemused:
        if not (t.kehtiv or t.hoiatused):
            continue
        d.add_heading(MEETODI_NIMI.get(t.meetod, t.meetod), 2)
        if t.kehtiv:
            d.add_paragraph(f"Tulemus {eur(t.väärtus)} ({eur(t.eur_m2)}/m²), vahemik {eur(t.vahemik[0])} – "
                            f"{eur(t.vahemik[1])}, usaldus {t.usaldus:.2f}, kaal {h.kaalud.get(t.meetod, 0):.0%}.")
        for x in t.selgitus:
            d.add_paragraph(x, style="List Bullet")
        if t.korrektsioonid:
            tabel(["Korrektsioon", "Tegur", "Põhjendus"], [[k.nimi, f"{k.tegur:.3f}", k.põhjendus] for k in t.korrektsioonid])
        vo = t.andmed.get("võrdlusobjektid")
        if vo:
            tabel(["Aadress", "Kaugus m", "Kuupäev", "Liik", "m²", "Hind", "€/m²", "Korrektsioonid", "Korr. €/m²"],
                  [[r["aadress"], r["kaugus_m"], r["kuupäev"], r["liik"], f"{r['pind_m2']:.0f}", eur(r["hind"]),
                    r["eur_m2"], r["korrektsioonid"], r["korr_eur_m2"]] for r in vo])
    if h.hoiatused:
        d.add_heading("Hoiatused", 1)
        for x in h.hoiatused:
            d.add_paragraph(x, style="List Bullet")
    d.add_heading("Hindaja kontrollnimekiri", 1)
    for x in KONTROLL:
        d.add_paragraph("☐ " + x)
    d.add_heading("Eeldused ja piirangud", 1)
    d.add_paragraph(PIIRANGUD)
    d.save(tee)
    return tee
