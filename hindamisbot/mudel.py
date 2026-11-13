"""Andmemudelid: hinnatav objekt, meetodi tulemus ja lõplik hinnang."""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import date
from enum import Enum
from typing import Optional


class ObjektiTyyp(str, Enum):
    KORTER = "korter"
    ERAMU = "eramu"          # elamu koos krundiga (sh ridaelamuboks, paarismaja pool)
    MAA = "maa"              # hoonestamata maa (elamu-, äri-, tootmis-, maatulundusmaa)
    ARIPIND = "aripind"      # äri-/büroo-/tootmispind või -hoone

    @classmethod
    def parse(cls, v: str) -> "ObjektiTyyp":
        v = v.strip().lower()
        aliases = {"maja": "eramu", "elamu": "eramu", "krunt": "maa", "ari": "aripind", "äripind": "aripind"}
        return cls(aliases.get(v, v))


class Seisukord(str, Enum):
    UUS = "uus"
    VAGA_HEA = "väga hea"
    HEA = "hea"
    RAHULDAV = "rahuldav"
    REMONDIVAJADUS = "remondivajadus"
    KAPITAALREMONT = "kapitaalremont"


@dataclass
class Objekt:
    """Hinnatav objekt. Väljad täidetakse avaandmetest; käsitsi antud väärtused on ülimuslikud."""
    aadress: str
    tyyp: Optional[ObjektiTyyp] = None          # None = tuvastatakse automaatselt
    tyyp_pohjendus: Optional[str] = None
    # Asukoht (In-ADS)
    normaliseeritud_aadress: Optional[str] = None
    maakond: Optional[str] = None
    omavalitsus: Optional[str] = None
    asustusyksus: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None
    ads_oid: Optional[str] = None
    katastritunnus: Optional[str] = None
    ehr_kood: Optional[str] = None
    hooneosa_nr: Optional[str] = None        # korteri / äripinna / muu hooneosa number
    osa_ehr_kood: Optional[str] = None       # hooneosa kood EHR-is (nt 101019881-2139396)
    # Ehitis (EHR) / hooneosa
    ehitise_otstarve: Optional[str] = None
    hooneosa: Optional[str] = None
    lift: Optional[bool] = None
    pind_m2: Optional[float] = None          # korteri/hoone üldpind või netopind
    ehitusaasta: Optional[int] = None         # kasutusloa aasta → ehitusloa aasta → esmane kasutuselevõtt
    rekonstrueeritud: Optional[int] = None
    korruseid: Optional[int] = None
    korrus: Optional[int] = None
    tube: Optional[int] = None
    materjal: Optional[str] = None
    energiaklass: Optional[str] = None
    seisukord: Optional[Seisukord] = None
    # Krunt (kataster)
    krundi_pind_m2: Optional[float] = None
    sihtotstarve: Optional[str] = None
    sihtotstarbed: Optional[str] = None          # kõik sihtotstarbed protsentidega
    omandivorm: Optional[str] = None             # eraomand / munitsipaalomand / riigiomand …
    kinnistu_nr: Optional[str] = None            # kinnistusraamatu registriosa number
    maa_maksustamishind: Optional[float] = None  # maa korralise hindamise maksustamishind
    katastri_markus: Optional[str] = None
    krundi_kuju: Optional[list] = None          # polügooni rõngad L-EST97 meetrites (joonise jaoks)
    hoone_kuju: Optional[list] = None
    # Asukohatunnused (OSM)
    kaugused_m: dict = field(default_factory=dict)
    # Märkused andmete päritolu kohta: väli -> allikas
    allikad: dict = field(default_factory=dict)

    def maara(self, väli: str, väärtus, allikas: str, kirjuta_yle: bool = False) -> None:
        """Määrab välja väärtuse, kui see on tühi (või kirjuta_yle=True), ja jätab allika meelde."""
        if väärtus is None:
            return
        if getattr(self, väli) is None or kirjuta_yle:
            setattr(self, väli, väärtus)
            self.allikad[väli] = allikas

    def vanus(self, kuupäev: date) -> Optional[int]:
        return None if self.ehitusaasta is None else max(0, kuupäev.year - self.ehitusaasta)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["tyyp"] = self.tyyp.value if self.tyyp else None
        d["seisukord"] = self.seisukord.value if self.seisukord else None
        return d


@dataclass
class Korrektsioon:
    nimi: str
    tegur: float          # kordaja, nt 1.05 = +5%
    põhjendus: str


@dataclass
class MeetodiTulemus:
    meetod: str                      # "statistika", "võrdlus", "kulu"
    väärtus: Optional[float]         # eurodes
    eur_m2: Optional[float] = None
    usaldus: float = 0.0             # 0..1 – kui palju meetodit lepitamisel usaldada
    vahemik: Optional[tuple] = None  # (madal, kõrge)
    korrektsioonid: list = field(default_factory=list)
    selgitus: list = field(default_factory=list)
    hoiatused: list = field(default_factory=list)
    andmed: dict = field(default_factory=dict)  # nt kasutatud võrdlusobjektid

    @property
    def kehtiv(self) -> bool:
        return self.väärtus is not None and self.väärtus > 0


@dataclass
class Hinnang:
    objekt: Objekt
    hindamise_kuupäev: date
    tulemused: list
    turuväärtus: Optional[float]
    vahemik: Optional[tuple]
    kaalud: dict
    hoiatused: list = field(default_factory=list)
    turg: dict = field(default_factory=dict)   # keel -> turuulevaated.TuruKontekst
