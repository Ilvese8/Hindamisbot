"""Tõlked (eesti / inglise). Hindamisloogika töötab eesti keeles; kasutajale näidatav tekst tõlgitakse siin.

- T(võti, keel)           – liidese ja aruande fikseeritud tekstid
- väli(võti, keel)        – andmeväljade nimed
- väärtus(tekst, keel)    – lühikesed väärtused (objekti liik, seisukord, allikad …)
- tõlgi(tekst, keel)      – dünaamilised hoiatused ja selgitused mustrite järgi (numbrid ja nimed säilivad)
Tõlketa tekst jääb eesti keelde – ükski hoiatus ei kao.
"""
from __future__ import annotations

import re

KEELED = {"et": "Eesti", "en": "English"}

_T = {
    # --- veebiliides
    "pealkiri": ("Sinu kinnisvara turuväärtus", "Your property's market value"),
    "alanimi": ("Hindamisbot – sisekoolitus", "Valuation bot – internal training"),
    "sissejuhatus": ("Vali aadress. Kogume kinnistu andmed maakatastrist ja ehitisregistrist, võrdleme neid "
                     "piirkonna tehingutega ning joonistame sinu krundi plaani.",
                     "Pick an address. We gather the property's data from the land cadastre and the Building Register, "
                     "compare it with local transactions and draw your plot plan."),
    "lahtiütlus": ("Automaatne hinnang avaandmete põhjal, mitte eksperthinnang. Tulemuse peab üle vaatama "
                   "kutsetunnistusega hindaja.",
                   "Automated estimate from open data, not an expert valuation. A certified valuer must review "
                   "the result."),
    "tühi_plaan": ("Siia joonistub sinu krundi plaan", "Your plot plan will be drawn here"),
    "plaan_puudub": ("Krundi kuju pole saadaval", "Plot outline not available"),
    "krundi_pind": ("Krundi pind", "Plot area"),
    "hinnatud": ("Hinnatud", "Valued"),
    "mõõtkavas": ("Mõõtkavas plaan: krundi piir maakatastrist, hoone ehitisregistrist",
                  "Plan to scale: plot boundary from the land cadastre, building from the Building Register"),
    "alapealkiri": ("Testversioon. Automaatne hinnang avaandmete põhjal – **ei ole eksperthinnang**. "
                    "Tulemuse peab üle kontrollima kutsetunnistusega hindaja.",
                    "Test version. Automated estimate based on Estonian open data – **not an expert valuation**. "
                    "The result must be reviewed by a certified valuer."),
    "aadress": ("Aadress", "Address"),
    "aadress_koht": ("Objekti aadress", "Property address"),
    "aadress_abi": ("Hakka trükkima ja vali pakutud aadress", "Start typing and pick a suggested address"),
    "osa": ("Korter / hooneosa", "Apartment / building unit"),
    "osa_abi": ("Kortermajas vali korteri number. Eramu või terve hoone puhul jäta „Terve hoone / krunt“.",
                "In an apartment building choose the apartment number. For a house or a whole building keep "
                "“Whole building / plot”."),
    "terve_hoone": ("Terve hoone / krunt", "Whole building / plot"),
    "hoone": ("hoone", "building"),
    "liik": ("Objekti liik", "Property type"),
    "tuvasta": ("Tuvasta automaatselt", "Detect automatically"),
    "seisukord": ("Seisukord", "Condition"),
    "teadmata": ("teadmata", "unknown"),
    "täpsusta": ("Täpsusta (valikuline) – tühjad väljad täidetakse avaandmetest",
                 "Refine (optional) – empty fields are filled from open data"),
    "pind": ("Pind m²", "Area m²"),
    "krunt": ("Krundi pind m²", "Plot area m²"),
    "ehitusaasta": ("Ehitusaasta", "Year built"),
    "korrus": ("Korrus", "Floor"),
    "energiaklass": ("Energiaklass", "Energy class"),
    "hinda": ("Hinda", "Estimate"),
    "piirang": ("Ühest brauserist saab teha kuni {n} hinnangut tunnis. Proovi hiljem uuesti.",
                "One browser can run up to {n} estimates per hour. Please try again later."),
    "arvutan": ("Otsin avaandmetest ja arvutan…", "Searching open data and calculating…"),
    "viga": ("Hindamine ebaõnnestus: {e}", "Valuation failed: {e}"),
    "objekti_liik": ("Objekti liik", "Property type"),
    "turuväärtus": ("Hinnanguline turuväärtus", "Estimated market value"),
    "vahemik": ("Vahemik", "Range"),
    "ühikuhind": ("Ühikuhind", "Price per m²"),
    "võrreldi": ("Võrreldi", "Compared with"),
    "arvestatud": ("Arvestatud", "Taken into account"),
    "aasta_allikas": ("Ehitusaasta allikas", "Source of year built"),
    "meetod": ("Meetod", "Method"),
    "väärtus": ("Väärtus", "Value"),
    "kaal": ("Kaal", "Weight"),
    "ei_õnnestunud": ("Turuväärtust ei õnnestunud määrata – vaata hoiatusi allpool.",
                      "The market value could not be determined – see the warnings below."),
    "andmed": ("Objekti andmed ja allikad", "Property data and sources"),
    "tunnus": ("Tunnus", "Attribute"),
    "allikas": ("Allikas", "Source"),
    "teenused": ("Lähimad teenused", "Nearest services"),
    "selgitus": ("Meetodite selgitus", "How the methods worked"),
    "korrektsioon": ("Korrektsioon", "Adjustment"),
    "tegur": ("Tegur", "Factor"),
    "põhjendus": ("Põhjendus", "Reason"),
    "hoiatused": ("Hoiatused", "Warnings"),
    "laadi_word": ("Laadi alla aruanne (Word)", "Download report (Word)"),
    "laadi_md": ("Laadi alla aruanne (Markdown)", "Download report (Markdown)"),
    "jalus": ("Andmed: {a}. Müügiportaalide andmeid ei kasutata.",
              "Data: {a}. No data from property sales portals is used."),
    "allikad": ("Maa- ja Ruumiamet (In-ADS, maakataster, tehingute andmebaas), ehitisregister, "
                "© OpenStreetMap kaastöötajad",
                "Estonian Land and Spatial Development Board (In-ADS, land cadastre, transaction database), "
                "Building Register, © OpenStreetMap contributors"),
    # --- aruanne
    "ar_pealkiri": ("Kinnisvara turuväärtuse esmane hinnang", "Preliminary property market value estimate"),
    "ar_mustand": ("MUSTAND – automaatne hinnang, vajab hindaja kontrolli",
                   "DRAFT – automated estimate, requires review by a valuer"),
    "ar_kuupäev": ("Hindamise kuupäev", "Valuation date"),
    "ar_objekt": ("Objekt", "Property"),
    "ar_kokkuvõte": ("Kokkuvõte", "Summary"),
    "ar_näitaja": ("Näitaja", "Indicator"),
    "ar_hinnatav": ("Hinnatav objekt", "Subject property"),
    "ar_asukoht": ("Asukoht (lähimad teenused, OpenStreetMap)", "Location (nearest services, OpenStreetMap)"),
    "ar_kategooria": ("Kategooria", "Category"),
    "ar_kaugus": ("Kaugus", "Distance"),
    "ar_meetodid": ("Meetodid", "Methods"),
    "ar_tulemus": ("Tulemus: **{v}** ({m2}/m²), vahemik {a} – {b}, usaldus {u:.2f}, kaal lepitamisel {k:.0%}.",
                   "Result: **{v}** ({m2}/m²), range {a} – {b}, confidence {u:.2f}, reconciliation weight {k:.0%}."),
    "ar_tulemus_docx": ("Tulemus {v} ({m2}/m²), vahemik {a} – {b}, usaldus {u:.2f}, kaal {k:.0%}.",
                        "Result {v} ({m2}/m²), range {a} – {b}, confidence {u:.2f}, weight {k:.0%}."),
    "ar_vo_päis": ("Aadress|Kaugus|Kuupäev|Liik|m²|Hind|€/m²|Korrektsioonid|Korr. €/m²|Allikas",
                   "Address|Distance|Date|Type|m²|Price|€/m²|Adjustments|Adj. €/m²|Source"),
    "ar_kontroll": ("Hindaja kontrollnimekiri", "Valuer's checklist"),
    "ar_piirangud": ("Eeldused ja piirangud", "Assumptions and limitations"),
}

_KONTROLL = [
    ("Objekt on paikvaatlusel üle vaadatud ja seisukord vastab sisendile.",
     "The property has been inspected on site and its condition matches the input."),
    ("Kinnistusraamatu väljavõte on kontrollitud: II jagu (omanik), III jagu (servituudid, kasutusõigused), "
     "IV jagu (hüpoteegid, märked). Bot neid andmeid ei kogu.",
     "The land register extract has been checked: part II (owner), part III (easements, rights of use), "
     "part IV (mortgages, notes). The bot does not collect these data."),
    ("Ehitisregistri andmed (pind, kasutusluba, otstarve) vastavad tegelikkusele.",
     "Building Register data (area, occupancy permit, use) match reality."),
    ("Planeeringud ja kitsendused on kontrollitud (Geoportaal, KOV).",
     "Spatial plans and restrictions have been checked (Geoportal, local government)."),
    ("Võrdlusobjektid on üle vaadatud ja sobivad; korrektsioonid on põhjendatud.",
     "Comparables have been reviewed and are suitable; adjustments are justified."),
    ("Seadistuste korrektsioonitegurid on hindaja poolt üle vaadatud ja põhjendatud.",
     "The adjustment factors in the settings have been reviewed and justified by the valuer."),
    ("Lõplik turuväärtus ja selle põhjendus on hindaja otsus (EVS 875).",
     "The final market value and its justification are the valuer's decision (EVS 875)."),
]

_PIIRANGUD = (
    "See dokument on automaatselt koostatud esmase hinnangu mustand. See ei ole eksperthinnang "
    "EVS 875 tähenduses enne, kui kutsetunnistusega hindaja on andmed ja järeldused üle kontrollinud ning "
    "aruande allkirjastanud. Kasutatud on avalikke koondandmeid (Maa- ja Ruumiameti hinnastatistika ja "
    "hinnaindeks, In-ADS, ehitisregister, OpenStreetMap) ning hindaja sisestatud võrdlusobjekte. "
    "Müügiportaalide andmeid automaatselt ei koguta.",
    "This document is an automatically generated draft of a preliminary estimate. It is not an expert valuation "
    "within the meaning of the Estonian standard EVS 875 until a certified valuer has reviewed the data and "
    "conclusions and signed the report. It uses public aggregated data (price statistics and price index of the "
    "Estonian Land and Spatial Development Board, In-ADS, Building Register, OpenStreetMap) and comparables "
    "entered by the valuer. Data from property sales portals is not collected automatically.",
)

_VÄLJAD = {
    "normaliseeritud_aadress": ("Aadress", "Address"), "tyyp": ("Objekti liik", "Property type"),
    "maakond": ("Maakond", "County"), "omavalitsus": ("Omavalitsus", "Municipality"),
    "asustusyksus": ("Asustusüksus", "Settlement / district"), "katastritunnus": ("Katastritunnus", "Cadastral number"),
    "ehr_kood": ("EHR kood", "Building Register code"), "hooneosa": ("Hooneosa", "Building unit"),
    "ehitise_otstarve": ("Ehitise otstarve", "Building use"), "pind_m2": ("Pind (m²)", "Area (m²)"),
    "krundi_pind_m2": ("Krundi pind (m²)", "Plot area (m²)"), "sihtotstarbed": ("Sihtotstarve", "Land use"),
    "omandivorm": ("Omandivorm", "Form of ownership"), "kinnistu_nr": ("Kinnistu (registriosa nr)", "Land register unit no."),
    "maa_maksustamishind": ("Maa maksustamishind (€)", "Land tax value (€)"),
    "katastri_markus": ("Katastri märge", "Cadastral note"), "ehitusaasta": ("Ehitusaasta", "Year built"),
    "rekonstrueeritud": ("Hilisem ümberehitus/muudatus (kasutusluba)", "Later alteration (occupancy permit)"),
    "korruseid": ("Korruseid", "Floors"), "korrus": ("Korrus", "Floor"), "tube": ("Tube", "Rooms"),
    "materjal": ("Materjal", "Structure"), "lift": ("Lift", "Lift"), "energiaklass": ("Energiaklass", "Energy class"),
    "seisukord": ("Seisukord", "Condition"), "lat": ("Laiuskraad", "Latitude"), "lon": ("Pikkuskraad", "Longitude"),
}

_MEETODID = {"statistika": ("Turustatistika meetod", "Market statistics method"),
             "võrdlus": ("Võrdlusmeetod", "Comparison method"),
             "kulu": ("Kulumeetod", "Cost method")}

# Lühikesed väärtused (täpne vaste, tõstutundetu)
_VÄÄRTUSED = {
    "korter": "apartment", "eramu": "house", "maa": "land", "aripind": "commercial",
    "uus": "new", "väga hea": "very good", "hea": "good", "rahuldav": "satisfactory",
    "remondivajadus": "needs repair", "kapitaalremont": "needs major renovation",
    "kivi": "masonry", "paneel": "panel", "puit": "timber", "muu": "other",
    "true": "yes", "false": "no",
    "ühistransport": "public transport", "kool": "school", "pood": "shop", "veekogu": "water",
    "sisend": "input", "valik": "selection", "in-ads": "In-ADS", "maakataster": "Land cadastre",
    "ehitisregister": "Building Register", "openstreetmap": "OpenStreetMap",
    "tuvastatud automaatselt": "detected automatically", "eraomand": "private property",
    "munitsipaalomand": "municipal property", "riigiomand": "state property",
    "pindala on ebatäpne": "area is imprecise",
    "üldpind": "floor area", "hoone pind": "building area", "krunt": "plot", "krundi pind": "plot area",
    "tehing": "sale", "pakkumine": "asking price",
}


def vo_korrektsioonid(t: str, keel: str = "et") -> str:
    """Võrdlusobjekti korrektsioonide rida, nt 'aeg +0.5%, korrus +3.1%'."""
    if keel != "en":
        return t
    for et, en in (("pakkumine→tehing", "asking→sale"), ("aeg", "time"), ("seisukord", "condition"),
                   ("energiaklass", "energy class"), ("ehitusperiood", "construction period"), ("korrus", "floor")):
        t = t.replace(et, en)
    return t

# Sõnad/fraasid väärtuste sees (nt "elamumaa 100%", "Ehitisregister (eluruum 55)")
_FRAASID = [
    ("Ehitisregister (väljavõte)", "Building Register (extract)"), ("Ehitisregister", "Building Register"),
    ("Maakataster", "Land cadastre"), ("In-ADS (hooneosa)", "In-ADS (building unit)"),
    ("esmase kasutuselevõtu aasta", "year of first use"),
    ("Kasutusluba ehitise püstitamisel", "Occupancy permit for construction"),
    ("Kasutusteatis ehitise püstitamisel", "Notice of use for construction"),
    ("Ehitusluba ehitise püstitamiseks", "Building permit for construction"),
    ("Kasutusluba", "Occupancy permit"), ("Kasutusteatis", "Notice of use"),
    ("eluruumide pind", "residential area"), ("suletud netopind", "closed net area"),
    ("mitteeluruum", "non-residential unit"), ("eluruum", "residential unit"),
    ("elamumaa", "residential land"), ("ärimaa", "commercial land"), ("tootmismaa", "industrial land"),
    ("maatulundusmaa", "profit-yielding land"), ("sotsiaalmaa", "social land"), ("transpordimaa", "transport land"),
    ("nr ", "no. "),
]

_TASE = {"asumi": "district", "omavalitsuse": "municipality", "maakonna": "county"}

# Dünaamilised laused: (muster, asendus). Rühmad säilitavad numbrid ja nimed.
_MUSTRID = [
    (r"^Võrdlusgrupp: (.+?) – (.+?), (\S+), (\d+) ostu-müügitehingut, mediaan (.+?) €/m² \((.+?)\)\. "
     r"Allikas: Maa- ja Ruumiamet, tehingute andmebaas \((.+?)\)\.$",
     lambda m: f"Comparison group: {_grupp(m[1])} – {m[2]}, {m[3]}, {m[4]} sale transactions, median {m[5]} €/m² "
               f"({väärtus(m[6], 'en')}). Source: Estonian Land and Spatial Development Board, transaction database "
               f"({m[7]})."),
    (r"^Maa- ja Ruumiameti hinnastatistika \((\S+) tasemel, (\d+) tehingut, perioodid (.+?)\): (.+?) €/m²\.$",
     lambda m: f"Land Board price statistics ({_TASE.get(m[1], m[1])} level, {m[2]} transactions, periods {m[3]}): "
               f"{m[4]} €/m²."),
    (r"^(\d+) võrdlusobjekti, korrigeeritud kaalutud keskmine (.+?) €/m², hajuvus \(CV\) (.+?)\.$",
     lambda m: f"{m[1]} comparables, adjusted weighted average {m[2]} €/m², dispersion (CV) {m[3]}."),
    (r"^Maa €/m² hoonestamata maa statistikast \((.+?), (\d+) tehingut\)\.$",
     lambda m: f"Land €/m² from vacant land statistics ({m[1]}, {m[2]} transactions)."),
    (r"^Maa: (.+?) m² × (.+?) €/m² = (.+?) €$", lambda m: f"Land: {m[1]} m² × {m[2]} €/m² = {m[3]} €"),
    (r"^Hoone: (.+?) m² × (.+?) €/m² × \(1 − kulum (.+?)\) × seisukord (.+?) = (.+?) €$",
     lambda m: f"Building: {m[1]} m² × {m[2]} €/m² × (1 − depreciation {m[3]}) × condition {m[4]} = {m[5]} €"),
    (r"^Arendaja kasum (.+?)\.$", lambda m: f"Developer's profit {m[1]}."),
    (r"^ehitusaasta (\d+): võrreldi sama ehitusperioodi \((.+?)\) tehingutega$",
     lambda m: f"year built {m[1]}: compared with transactions from the same construction period ({m[2]})"),
    (r"^ehitusaasta (\d+): arvestatud ehitusperioodi korrektsiooniga$",
     lambda m: f"year built {m[1]}: applied as a construction-period adjustment"),
    # objektitüübi põhjendused
    (r"^hooneosa (.+?) on eluruum hoones „(.+?)“$", lambda m: f"unit {m[1]} is a residential unit in “{m[2]}”"),
    (r"^hooneosa (.+?) on eluruum \(ehitisregister\)$", lambda m: f"unit {m[1]} is a residential unit (Building Register)"),
    (r"^hooneosa (.+?) on mitteeluruum \(ehitisregister\)$", lambda m: f"unit {m[1]} is a non-residential unit (Building Register)"),
    (r"^aadressil on hooneosa number ja hoone on „(.+?)“$", lambda m: f"the address has a unit number and the building is “{m[1]}”"),
    (r"^hoone on mitteeluhoone „(.+?)“$", lambda m: f"the building is non-residential: “{m[1]}”"),
    (r"^hoone on „(.+?)“$", lambda m: f"the building is “{m[1]}”"),
    (r"^aadressil ei ole ehitist, leiti katastriüksus$", lambda m: "no building at this address, a cadastral unit was found"),
    # hoiatused
    (r"^\[(andmed|statistika|võrdlus|kulu)\] (.+)$",
     lambda m: f"[{ {'andmed': 'data', 'statistika': 'statistics', 'võrdlus': 'comparison', 'kulu': 'cost'}[m[1]] }] "
               f"{tõlgi(m[2], 'en')}"),
    (r"^Ehitusaasta pole teada – hinnang ei arvesta hoone vanust\.$",
     lambda m: "Year built is unknown – the estimate does not account for the building's age."),
    (r"^Ehitusaasta puudub – kulum eeldatud 30%\.$", lambda m: "Year built missing – depreciation assumed at 30%."),
    (r"^Hinnastatistika fail puudub – meetodit ei rakendatud\.$", lambda m: "Price statistics file missing – method not applied."),
    (r"^In-ADS ei leidnud aadressi – kontrolli kirjapilti\.$", lambda m: "In-ADS did not find the address – check the spelling."),
    (r"^In-ADS ei tagastanud koordinaate\.$", lambda m: "In-ADS returned no coordinates."),
    (r"^Katastriandmeid ei leitud – krundi pind tuleb sisestada käsitsi\.$",
     lambda m: "No cadastral data found – enter the plot area manually."),
    (r"^Korterit ei leitud ehitisregistri hooneosade hulgast.*$",
     lambda m: "The apartment was not found among the building units in the Building Register – check the "
               "apartment number or enter the area manually."),
    (r"^Kulumeetodi taastamismaksumus ja eluiga on seadistuste eeldused – kontrolli neid\.$",
     lambda m: "Replacement cost and service life in the cost method are settings assumptions – review them."),
    (r"^Maa väärtust ei õnnestunud leida – kulumeetodit ei rakendatud\.$",
     lambda m: "Land value could not be found – cost method not applied."),
    (r"^Puudub hoone pind – kulumeetodit ei rakendatud\.$", lambda m: "Building area missing – cost method not applied."),
    (r"^Puudub krundi pind – kulumeetodit ei rakendatud\.$", lambda m: "Plot area missing – cost method not applied."),
    (r"^Puudub (.+?) – meetodit ei saa rakendada\.$", lambda m: f"Missing {_ala(m[1])} – method cannot be applied."),
    (r"^Rakendati ainult üks meetod – tulemus on vähem kindel\.$",
     lambda m: "Only one method could be applied – the result is less certain."),
    (r"^Ridaelamu – .*$", lambda m: "Terraced house – if the units are separate apartment ownerships, give the unit number."),
    (r"^Suvila/aiamaja – .*$", lambda m: "Summer house – market statistics compare with dwellings, check suitability."),
    (r"^Aadress on kortermaja – .*$",
     lambda m: "The address is an apartment building – give the apartment number (e.g. “Ehitajate tee 35-55”) "
               "to value one apartment."),
    (r"^Sobivat hinnastatistika lahtrit ei leitud.*$",
     lambda m: "No suitable price statistics cell found (area/size range/period)."),
    (r"^Statistika on krundi €/m² kohta, aga krundi pind puudub\.$",
     lambda m: "Statistics are per m² of plot, but the plot area is missing."),
    (r"^Võrdlusobjektide fail puudub või on tühi – meetodit ei rakendatud\.$",
     lambda m: "No comparables file (or it is empty) – method not applied."),
    (r"^Võrdlusobjektide korrigeeritud hinnad hajuvad tugevalt.*$",
     lambda m: "Adjusted comparable prices vary widely (CV > 20%) – check the selection."),
    (r"^Sobivaid võrdlusobjekte on (\d+) \(vaja vähemalt 3\)\.$",
     lambda m: f"Only {m[1]} suitable comparables (at least 3 needed)."),
    (r"^Asumi tasemel andmeid polnud piisavalt – kasutati (\S+) taset\.$",
     lambda m: f"Not enough data at district level – {_TASE.get(m[1], m[1])} level used."),
    (r"^Meetodite tulemused lahknevad (\S+) – .*$",
     lambda m: f"Method results differ by {m[1]} – the valuer must justify the final weighting."),
    (r"^Energiamärgis \((\S+), (\d+)\) on vanem kui 10 aastat – ei kasutatud\.$",
     lambda m: f"Energy certificate ({m[1]}, {m[2]}) is older than 10 years – not used."),
    (r"^Hoonel on hilisem \((\d+)\) .*$",
     lambda m: f"The building has a later ({m[1]}) occupancy permit or notice for reconstruction/alteration or other "
               "works – check in the Building Register what was done and consider it when assessing condition."),
    (r"^Hooneosa (.+?) ei leitud ehitisregistrist – eeldatud korterit\.$",
     lambda m: f"Unit {m[1]} not found in the Building Register – assumed to be an apartment."),
    (r"^Hoones on (\d+) eluruumi – .*$",
     lambda m: f"The building has {m[1]} residential units – if you are valuing one of them (e.g. a terraced unit), "
               "give the unit number."),
    (r"^Katastri märge: (.+?)\.$", lambda m: f"Cadastral note: {väärtus(m[1], 'en')}."),
    (r"^Katastriüksusel on mitu sihtotstarvet \((.+?)\)\.$",
     lambda m: f"The cadastral unit has several land uses ({väärtus(m[1], 'en')})."),
    (r"^Katastriüksust (\S+) ei leitud katastrist\.$", lambda m: f"Cadastral unit {m[1]} not found in the cadastre."),
    (r"^Omandivorm: (.+?) – kontrolli kinnistusraamatust\.$",
     lambda m: f"Form of ownership: {väärtus(m[1], 'en')} – check the land register."),
    (r"^(In-ADS|OpenStreetMap|Ehitisregistri liides|Katastriteenus) pole kättesaadav: (.+)$",
     lambda m: f"{ {'Ehitisregistri liides': 'Building Register API', 'Katastriteenus': 'Cadastre service'}.get(m[1], m[1]) } "
               f"is not available: {m[2]}"),
    (r"^Statistika liides pole kättesaadav \((.+?)\) – kasutan kohalikku faili\.$",
     lambda m: f"Statistics API not available ({m[1]}) – using the local file."),
    (r"^EHR-koodi ei leitud.*$", lambda m: "Building Register code not found – enter building data manually."),
    (r"^Ehitist ei leitud EHR-i väljavõttest\.$", lambda m: "Building not found in the Building Register extract."),
    (r"^Ühtegi meetodit ei õnnestunud rakendada.*$",
     lambda m: "No method could be applied – a market value cannot be given."),
    (r"^Objektitüüpi ei õnnestunud tuvastada.*$", lambda m: "The property type could not be detected – please choose it."),
]
_MUSTRID = [(re.compile(p), f) for p, f in _MUSTRID]

_KORREKTSIOONID = {"Aeg (hinnaindeks)": "Time (price index)", "Seisukord": "Condition", "Energiaklass": "Energy class",
                   "Ehitusperiood": "Construction period", "Korrus": "Floor"}


def _grupp(t: str) -> str:
    asendused = [
        (r"^korterid majades, mis on ehitatud (.+)$", r"apartments in buildings built \1"),
        (r"^korterid pinnaga (.+) m² \(kõik ehitusaastad\)$", r"apartments of \1 m² (all construction years)"),
        (r"^elamud, mis on ehitatud (.+)$", r"houses built \1"),
        (r"^elamud \(kõik ehitusaastad\)$", r"houses (all construction years)"),
        (r"^hoonestamata maa, sihtotstarve (.+)$", r"vacant land, land use \1"),
        (r"^hoonestatud maa, sihtotstarve (.+)$", r"built-up land, land use \1"),
    ]
    for p, r in asendused:
        if re.match(p, t):
            return _fraasid(re.sub(p, r, t))
    return t


def _ala(t: str) -> str:
    return {"krundi pind": "plot area", "üldpind": "floor area"}.get(t, t)


def _fraasid(t: str) -> str:
    for et, en in _FRAASID:
        t = t.replace(et, en)
    return t


def T(võti: str, keel: str = "et", **kw) -> str:
    et, en = _T[võti]
    s = en if keel == "en" else et
    return s.format(**kw) if kw else s


def väli(võti: str, keel: str = "et") -> str:
    et, en = _VÄLJAD.get(võti, (võti, võti))
    return en if keel == "en" else et


def meetod(võti: str, keel: str = "et") -> str:
    et, en = _MEETODID.get(võti, (võti, võti))
    return en if keel == "en" else et


def kontroll(keel: str = "et") -> list[str]:
    return [en if keel == "en" else et for et, en in _KONTROLL]


def piirangud(keel: str = "et") -> str:
    return _PIIRANGUD[1] if keel == "en" else _PIIRANGUD[0]


def korrektsioon(nimi: str, keel: str = "et") -> str:
    if keel != "en":
        return nimi
    if nimi.startswith("Lähedus: "):
        return "Proximity: " + väärtus(nimi.split(": ", 1)[1], "en")
    return _KORREKTSIOONID.get(nimi, nimi)


def väärtus(v, keel: str = "et") -> str:
    """Lühike väärtus (objekti liik, seisukord, allikas, sihtotstarve …)."""
    if v is None:
        return ""
    s = str(v)
    if keel != "en":
        return {"True": "jah", "False": "ei"}.get(s, s)
    otse = _VÄÄRTUSED.get(s.strip().lower())
    if otse:
        return otse
    m = re.match(r"^(\w+) \(tuvastatud: (.+)\)$", s)
    if m:
        return f"{väärtus(m[1], 'en')} (detected: {tõlgi(m[2], 'en')})"
    return _fraasid(s)


def tõlgi(tekst: str, keel: str = "et") -> str:
    """Dünaamiline lause (hoiatus, selgitus). Tõlketa jääb eesti keelde."""
    if keel != "en" or not tekst:
        return tekst
    for muster, f in _MUSTRID:
        m = muster.match(tekst)
        if m:
            return f(m)
    return _fraasid(tekst)
