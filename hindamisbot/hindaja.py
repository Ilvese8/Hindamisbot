"""Töövoog: andmete kogumine avaandmetest → meetodid → lepitamine."""
from __future__ import annotations

from datetime import date
from pathlib import Path

from .allikad import ehr, ehr_api, inads, kataster, osm
from .allikad.hinnastatistika import Hinnaindeks, Hinnastatistika
from .allikad.http import Klient
from .allikad.kataster_stat import KatasterStatistika, StatAllikas
from .allikad.vordlusobjektid import lae as lae_vordlus
from .lepitamine import lepita
from .meetodid import kulu_meetod, statistika_meetod, vordlus_meetod
from .mudel import Hinnang, Objekt
from .tuvastus import tuvasta
from .turuulevaated import Turuulevaated


class Hindaja:
    def __init__(self, s, vorguta: bool = False, vahemalu: Path | None = None):
        self.s = s
        self.vorguta = vorguta
        li = s["liidesed"]
        self.klient = Klient(li["kasutajaagent"], li["viivitus_s"], li["timeout_s"],
                             vahemalu or s.juur / ".vahemalu", li.get("vahemalu_paevi", 7))
        api = None
        if not vorguta and s.get_path("statistika.allikas", "api") == "api":
            api = KatasterStatistika(self.klient, s)
        self.stat = StatAllikas(api, Hinnastatistika(s.fail("hinnastatistika")))
        self.indeks = Hinnaindeks(s.fail("hinnaindeks"))
        self.ehr = ehr.Ehitisregister(s.fail("ehitisregister"))
        self.ehr_api = None if vorguta else ehr_api.EhrApi(self.klient, s)
        self.kataster = None if vorguta else kataster.Kataster(self.klient, s)
        self.vordlus = lae_vordlus(s.fail("vordlusobjektid"))
        tu = s.get("andmefailid", {}).get("turuulevaated")
        self.turg = Turuulevaated(s.fail("turuulevaated") if tu else None)
        self.logi: list[str] = []

    def kogu(self, o: Objekt, korter: str | None = None, kuupäev: date | None = None) -> list[str]:
        """Täidab objekti avaandmetest ja tuvastab vajadusel tüübi. Käsitsi antud väljad jäävad alles."""
        hoiatused = []
        hoone_aadress, nr = inads.eralda_hooneosa(o.aadress)
        korter = korter or nr
        if korter:
            o.maara("hooneosa_nr", str(korter), "sisend")
        li = self.s["liidesed"]
        tyyp_teada = o.tyyp is not None

        # 1. Aadress
        inads_liik = None
        if not self.vorguta:
            try:
                kirje = inads.otsi(self.klient, li["inads_url"], hoone_aadress, korter)
                if kirje:
                    inads_liik = str(kirje.get("liikVal") or "")
                    hoiatused += inads.rikasta(o, kirje)
                    self.logi.append("In-ADS: aadress leitud.")
                else:
                    hoiatused.append("In-ADS ei leidnud aadressi – kontrolli kirjapilti.")
            except ConnectionError as e:
                hoiatused.append(f"In-ADS pole kättesaadav: {e}")

        # Hooneosa kood algab hoone EHR-koodiga – kui need ei klapi, kuulub osa teise hoonesse
        if o.osa_ehr_kood and "-" in o.osa_ehr_kood:
            hoone = o.osa_ehr_kood.split("-")[0]
            if o.ehr_kood != hoone:
                o.maara("ehr_kood", hoone, "In-ADS (hooneosa)", kirjuta_yle=True)

        # 2. Ehitis (ka siis, kui tüüp on veel teadmata)
        e = osa = None
        ehr_kirje = None
        if not (tyyp_teada and o.tyyp.value == "maa"):
            if self.ehr_api and o.ehr_kood:
                try:
                    e = self.ehr_api.ehitis(o.ehr_kood)
                    if e and (o.hooneosa_nr or o.osa_ehr_kood):
                        osa = e.leia_osa(o.hooneosa_nr, o.osa_ehr_kood)
                except ConnectionError as err:
                    hoiatused.append(f"Ehitisregistri liides pole kättesaadav: {err}")
            if e is None:
                ehr_kirje = self.ehr.leia(o.ehr_kood, o.normaliseeritud_aadress or o.aadress)

        # 3. Katastriüksus
        if self.kataster and not o.katastritunnus and e and e.katastritunnused:
            o.maara("katastritunnus", e.katastritunnused[0], "Ehitisregister")
        if self.kataster and not o.katastritunnus:
            try:
                k = inads.otsi(self.klient, li["inads_url"], hoone_aadress, features="KATASTRIYKSUS")
                if k and str(k.get("liikVal", "")).upper() == "KATASTRIYKSUS":
                    o.maara("katastritunnus", k.get("tunnus"), "In-ADS")
            except ConnectionError:
                pass
        ky = None
        if self.kataster and o.katastritunnus:
            try:
                ky = self.kataster.yksus(o.katastritunnus)
                if not ky:
                    hoiatused.append(f"Katastriüksust {o.katastritunnus} ei leitud katastrist.")
            except ConnectionError as err:
                hoiatused.append(f"Katastriteenus pole kättesaadav: {err}")

        # 4. Objektitüüp
        if not tyyp_teada:
            ots = e.otstarve if e else (ehr_kirje or {}).get("kasutamise_otstarve")
            tyyp, põhjus, th = tuvasta(
                inads_liik=inads_liik, otstarve=ots, kaos_kood=e.kaos_kood if e else None,
                osa_liik=osa.liik if osa else None, osa_nr=o.hooneosa_nr, eluruume=e.eluruume if e else 0,
                on_katastriyksus=bool(ky) and not (e or ehr_kirje))
            hoiatused += th
            if tyyp is None:
                return hoiatused
            o.tyyp, o.tyyp_pohjendus = tyyp, põhjus
            o.allikad["tyyp"] = "tuvastatud automaatselt"
            self.logi.append(f"Objektitüüp: {tyyp.value} ({põhjus})")

        # 5. Andmed objektile
        if o.tyyp.value != "maa":
            if e:
                hoiatused += ehr_api.rikasta(o, e, osa, kuupäev)
                self.logi.append(f"Ehitisregister: {e.nimetus or 'ehitis'} {e.ehr_kood}"
                                 + (f", hooneosa {osa.tahis}" if osa else ""))
            elif ehr_kirje:
                ehr.rikasta(o, ehr_kirje)
                self.logi.append("Ehitisregister (väljavõte): ehitise andmed leitud.")
            elif self.ehr.olemas:
                hoiatused.append("Ehitist ei leitud EHR-i väljavõttest.")
        if ky:
            hoiatused += kataster.rikasta(o, ky)
            self.logi.append(f"Maakataster: {ky.tunnus}, {ky.pindala_m2} m², {ky.sihtotstarbed_tekst}")
        elif o.tyyp.value in ("maa", "eramu") and not o.krundi_pind_m2:
            hoiatused.append("Katastriandmeid ei leitud – krundi pind tuleb sisestada käsitsi.")

        # 6. Asukoht
        if not self.vorguta and o.lat and o.lon and not o.kaugused_m:
            try:
                o.kaugused_m = osm.kaugused(self.klient, li["overpass_url"], o.lat, o.lon)
                o.allikad["kaugused_m"] = "OpenStreetMap"
            except ConnectionError as err:
                hoiatused.append(f"OpenStreetMap pole kättesaadav: {err}")
        return hoiatused

    def hinda(self, o: Objekt, kuupäev: date | None = None, korter: str | None = None,
              maa_eur_m2: float | None = None) -> Hinnang:
        kuupäev = kuupäev or date.today()
        kogumise_hoiatused = self.kogu(o, korter, kuupäev)
        if o.tyyp is None:
            return Hinnang(o, kuupäev, [], None, None, {}, [f"[andmed] {x}" for x in kogumise_hoiatused])
        tulemused = [
            statistika_meetod(o, self.stat, self.indeks, self.s, kuupäev),
            vordlus_meetod(o, self.vordlus, self.indeks, self.s, kuupäev),
            kulu_meetod(o, self.stat, self.indeks, self.s, kuupäev, maa_eur_m2),
        ]
        h = lepita(o, tulemused, self.s, kuupäev)
        kogumise_hoiatused += self.stat.hoiatused
        self.stat.hoiatused = []
        if self.stat.api:
            self.logi += self.stat.api.logi
            self.stat.api.logi = []
        h.hoiatused = [f"[andmed] {x}" for x in kogumise_hoiatused] + h.hoiatused
        if self.turg.olemas:
            pind = o.krundi_pind_m2 if o.tyyp.value == "maa" else o.pind_m2
            eur_m2 = h.turuväärtus / pind if h.turuväärtus and pind else None
            h.turg = {keel: self.turg.kontekst(o, eur_m2, keel) for keel in ("et", "en")}
            if h.turg["et"].hoiatus:
                h.hoiatused.append(f"[turg] {h.turg['et'].hoiatus}")
        return h
