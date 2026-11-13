# Hindamisbot

Kinnisvara turuväärtuse **esmane hinnang** Eesti riigi avaandmete põhjal: korterid, eramud, maa ja äripinnad.
Bot kogub objekti andmed, rakendab kolme hindamismeetodit, lepitab tulemused ja koostab aruande mustandi
(Markdown, Word, JSON).

> Tulemus ei ole eksperthinnang. Eksperthinnangu (EVS 875) allkirjastab kutsetunnistusega hindaja pärast andmete,
> võrdlusobjektide ja järelduste kontrolli. Bot ei kogu andmeid müügiportaalidest (kv.ee, City24, kinnisvara24.ee),
> sest nende kasutustingimused keelavad automaatse andmekogumise.

## Paigaldus

```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-dev.txt && python -m pytest -q   # testid, võrku pole vaja
```

## Veebiversioon

`streamlit_app.py` on veebiliides: aadress → hinnang → Wordi aruanne. Tasuta lingile paigaldamise juhend on failis
[PAIGALDUS.md](PAIGALDUS.md).

## Kasutamine

**Vestlusbot** küsib andmed samm-sammult ja täidab avaandmetest kõik, mis leidub:

```bash
python -m hindamisbot bot
```

**Käsurida** ühe objekti hindamiseks:

```bash
python -m hindamisbot hinda "Ehitajate tee 35-55, Tallinn"          # korter: tüüp, pind, korrus jm avaandmetest
python -m hindamisbot hinda "Männi tee 3, Viimsi" --seisukord hea   # eramu: hoone + krunt
python -m hindamisbot hinda "Viru väljak 4, Tallinn" --osa 2        # üks hooneosa (äripind)
python -m hindamisbot hinda "Männi tee 3, Viimsi" --tyyp maa        # tüübi saab alati üle kirjutada
python -m hindamisbot hinda "Metsa, Saue vald" --tyyp maa --krunt 2200 --sihtotstarve elamumaa
```

Aruanded salvestatakse kausta `aruanded/`. Kui soovid proovida väljamõeldud näidisandmetega ilma võrguta:

```bash
python -m hindamisbot --seadistused seadistused_naidis.toml --vorguta hinda "Näidise tn 1-15, Tallinn" \
  --tyyp korter --pind 51.2 --korrus 3 --korruseid 5 --seisukord hea --energiaklass E \
  --maakond "Harju maakond" --omavalitsus Tallinn --asustusyksus Mustamäe --lat 59.403 --lon 24.697
```

## Objektitüübi tuvastamine

Kui `--tyyp` pole antud, tuvastab bot tüübi (`tuvastus.py`):

| Leitud andmed | Tüüp |
|---|---|
| hooneosa on ehitisregistris eluruum | korter (ühe eluruumiga eramu puhul eramu) |
| hooneosa on mitteeluruum | äripind |
| hoone on üksikelamu, kahe korteriga elamu, ridaelamu, suvila | eramu |
| hoone on kortermaja, aga korteri numbrit pole | korter + hoiatus: anna korteri number |
| hoone on mitteeluhoone | äripind |
| aadressil pole ehitist, on katastriüksus | maa |

Tuvastatud tüüp ja põhjendus on aruandes kirjas. Vestlusbot küsib kinnitust ja laseb tüüpi muuta.

## Andmeallikad

| Allikas | Mida annab | Kuidas | Kus koodis |
|---|---|---|---|
| In-ADS (Maa- ja Ruumiamet) | normaliseeritud aadress, koordinaadid, katastritunnus, EHR-kood | avalik API, automaatne | `allikad/inads.py` |
| Ehitisregister | **kõik ehitised:** ehitusaasta, korruste arv, lift, netopind/eluruumide pind, otstarve, materjal, katastritunnus, energiamärgis; **hooneosad** (korterid, äripinnad): pind, tubade arv, korrus | **automaatne**, ehitisregistri avaliku vaate liidesest; varuvariant CSV-väljavõte `andmed/ehitisregister.csv` | `allikad/ehr_api.py`, `allikad/ehr.py` |
| Hinnastatistika (Maa- ja Ruumiamet) | ostu-müügitehingute €/m² mediaan, hajuvus ja tehingute arv asumi/omavalitsuse/maakonna kaupa; korterid ja eramud ehitusperioodi järgi, maa sihtotstarbe järgi | **automaatne**, päringukeskkonna statistika.kataster.ee liidesest; varuvariant CSV-fail `andmed/hinnastatistika.csv` | `allikad/kataster_stat.py`, `allikad/hinnastatistika.py` |
| Hinnaindeks (Maa- ja Ruumiamet) | kvartaalne indeks hindade ajakorrektsiooniks | CSV → `andmed/hinnaindeks.csv` | `allikad/hinnastatistika.py` |
| Maakataster (Maa- ja Ruumiamet, WFS) | krundi pindala, sihtotstarve(d), omandivorm, kinnistu number, maa maksustamishind, katastri märked | **automaatne**, avalik WFS `gsavalik.envir.ee/geoserver/kataster` (sama andmestik mis X-GIS-is) | `allikad/kataster.py` |
| OpenStreetMap (Overpass) | kaugus ühistranspordi, kooli, poe ja veekoguni | avalik API, automaatne | `allikad/osm.py` |
| **Infopank: turuülevaated** | Maa- ja Ruumiameti aastaülevaate (2025) hinnatasemed maakonna, asula, Tallinna/Tartu/Pärnu linnaosa ja Tallinna asumi kaupa; hinnaindeksid kuni 2026 III; Uus Maa, 1Partneri ja Pindi kuuülevaated; Pindi uusarenduste monitooring (Tallinn + Harjumaa); Newsec/Colliers/Inreal büroo-, kaubandus- ja laopindade vakants, üürid ja tootlused | `tools/ehita_turuulevaated.py` → `andmed/turuulevaated.csv` (ainult arvud + allikas, periood ja link) | `turuulevaated.py` |
| Hindaja võrdlusobjektid | tehingud või käsitsi üle vaadatud pakkumised | käsitsi täidetud CSV → `andmed/vordlusobjektid.csv` | `allikad/vordlusobjektid.py` |

Failide veerunimed vastendatakse paindlikult (vt `ALIASED` iga mooduli alguses), seega sobivad ka
veidi erineva päisega väljavõtted. Näidisfailid veergude kujuga on kaustas `andmed/naidis/`.
**Need sisaldavad väljamõeldud numbreid ja on mõeldud ainult testimiseks.**

Võrdlusobjektide failis on veerg `allika_tyyp`: tehingu korral `tehing`, kuulutuse korral `pakkumine`.
Pakkumishinda korrigeeritakse tegur `vordlus.pakkumise_korrektsioon` abil.

### Turu kontekst ja usutavuskontroll

Iga hinnangu juurde lisatakse **Turu kontekst**: piirkonna hinnatase kõige täpsemast olemasolevast
piirkonnast (asum → linnaosa → asula → maakond → Eesti), kinnisvarafirmade värskeim kuuülevaade ja
korteriindeksi aastamuutus. Korteri puhul arvutatakse **võrdlustase täna** = aastaülevaate mediaan ×
(viimane korteriindeks / aastaülevaate aasta keskmine indeks). Kui hinnangu €/m² erineb sellest üle 25%,
lisatakse hoiatus `[turg]`. Uue ülevaate lisamiseks täienda tabeleid failis `tools/ehita_turuulevaated.py`
ja käivita `python tools/ehita_turuulevaated.py`.

## Mida bot ei kogu: omanik ja koormatised

Omaniku andmed (kinnistusraamatu II jagu), servituudid (III jagu) ja hüpoteegid (IV jagu) on ainult
kinnistusraamatus. RIK-i kinnistusraamatu XML-teenus nõuab kasutajanime ja parooli ning detailandmete päring
on tasuline. Bot näitab aruandes kinnistu numbrit ja hindaja kontrollnimekirjas on kinnistusraamatu kontroll.
Katastrist tuleb ainult omandivorm (eraomand, riigiomand jne), mitte omaniku nimi.

## Meetodid

1. **Turustatistika meetod.** Bot pärib Maa- ja Ruumiameti päringukeskkonnast viimase 12 kuu ostu-müügitehingud
   (kui tehinguid napib, siis 24 kuu omad). Ta otsib kõige täpsemat piirkonda (asum/linnaosa → omavalitsus → maakond)
   ja kõige sarnasemat gruppi:
   - korterid: hoone ehitusperiood; kui ehitusaasta pole teada, siis pinnavahemik;
   - eramud: hoone ehitusperiood, varuvariandina kõik elamud;
   - maa: sihtotstarve.

   Grupi mediaan €/m² viiakse hinnaindeksiga hindamise kuupäeva. Seejärel rakendatakse objekti korrektsioonid
   (seisukord, energiaklass, korrus, lähedus teenustele). Vahemik arvutatakse grupi standardhälbest.
   Alla 5 tehinguga grupid on liideses peidetud, sel juhul laiendab bot perioodi või piirkonda.
   Viide andmetele: *Maa- ja Ruumiamet, tehingute andmebaas*.
2. **Võrdlusmeetod.** Valitakse kuni `k` kõige sarnasemat võrdlusobjekti (kaugus, pind, vanus). Igaühe €/m²
   korrigeeritakse aja, seisukorra, energiaklassi, ehitusperioodi, korruse ja pakkumise/tehingu erinevuse järgi.
   Tulemus on sarnasusega kaalutud keskmine. Hajuvus (CV) mõjutab usaldust ja vahemikku.
3. **Kulumeetod** (eramud, äripinnad). Arvutatakse maa väärtus (hoonestamata maa statistikast või
   `--maa-eur-m2`), millele liidetakse hoone taastamismaksumus miinus kulum ja arendaja kasum.
4. **Lepitamine.** Iga meetodi kaal = objektitüübi baaskaal × meetodi usaldus, normaliseeritud.
   Kui meetodite tulemused lahknevad üle 20%, lisatakse hoiatus ja vahemikku laiendatakse.

## Seadistused

Kõik korrektsioonitegurid, kulumeetodi eeldused ja lepitamise kaalud asuvad failis `seadistused.toml`.
Need on **hindaja otsustatavad eeldused**. Märkega „NÄIDIS“ väärtused on algseaded, mis tuleb enne
tegelikku kasutamist üle vaadata ja põhjendada.

## Avalike teenuste kasutamine

- Ehitisregistri liides (livekluster.ehr.ee/api/building/v3/buildingData) on sama, mida kasutab ehitisregistri
  avalik ehitise vaade. Ühe hinnangu jaoks teeb bot kaks päringut: ehitise andmed ja energiamärgised.
  Üle 10 aasta vana energiamärgist hinnangus ei kasutata.

- Statistika päringukeskkonna liides (statistika.kataster.ee/api/tehingud) on sama, mida kasutab avalik veebileht.
  Liides ei ole ametlikult dokumenteeritud ja võib muutuda. Kui päring ebaõnnestub, kasutab bot kohalikku faili ja
  lisab aruandesse hoiatuse. Ühe hinnangu jaoks teeb bot paar kuni kümme päringut ja hoiab vastuseid 7 päeva vahemälus.
  Kui plaanid suuri mahte, küsi Maa- ja Ruumiametilt (maaruum@maaruum.ee), kas neil on selleks eelistatud kanal.

- In-ADS-il on päringulimiidid (vt In-ADS kasutustingimused). Massiliseks töötluseks kasuta ADS-i
  avaandmete CSV-väljavõtet.
- Overpassi avalikku serverit ei tohi koormata. Suurte mahtude jaoks paigalda oma Overpassi server.
- Bot ootab päringute vahel `viivitus_s` sekundit ja salvestab vastused kausta `.vahemalu/`.

## Laiendamine

- Uus andmeallikas: lisa moodul kausta `hindamisbot/allikad/` ja kutsu see välja `Hindaja.kogu()` meetodis.
- Kui saad portaalidelt ametliku andmevoo (leping), lisa see võrdlusobjektide allikana. Võrdlusmeetod
  on juba olemas.
- Teised liidesed (Telegram, veebivorm) saavad kasutada sama `Hindaja.hinda()` funktsiooni.
