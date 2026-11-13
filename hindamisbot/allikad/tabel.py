"""CSV/XLSX lugemine paindliku veerunimede vastendusega (avaandmete väljavõtted muutuvad aeg-ajalt)."""
from __future__ import annotations

import re
import unicodedata
from pathlib import Path

import pandas as pd


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "_", s).strip("_")


def loe(tee: Path) -> pd.DataFrame:
    if tee.suffix.lower() in (".xlsx", ".xls"):
        df = pd.read_excel(tee)
    else:
        # Eesti väljavõtetes on sageli semikoolon ja komakohaga numbrid
        with open(tee, encoding="utf-8-sig") as f:
            esimene = f.readline()
        sep = ";" if esimene.count(";") > esimene.count(",") else ","
        df = pd.read_csv(tee, sep=sep, encoding="utf-8-sig", decimal="," if sep == ";" else ".",
                         dtype=str, keep_default_na=False)
    df.columns = [_norm(c) for c in df.columns]
    return df


def vastenda(df: pd.DataFrame, aliased: dict[str, list[str]]) -> pd.DataFrame:
    """Nimetab veerud ümber standardnimedeks. aliased: standardnimi -> võimalikud nimed."""
    ümber = {}
    for std, nimed in aliased.items():
        for n in [std, *nimed]:
            n = _norm(n)
            if n in df.columns and n not in ümber:
                ümber[n] = std
                break
    return df.rename(columns=ümber)


def arv(v):
    """'1 234,5' -> 1234.5; tühi -> None."""
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return None if pd.isna(v) else float(v)
    s = str(v).strip().replace("\xa0", "").replace(" ", "").replace(",", ".")
    if s in ("", "-", "nan", "None"):
        return None
    try:
        return float(s)
    except ValueError:
        return None
