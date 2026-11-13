"""Seadistuste laadimine (seadistused.toml)."""
from __future__ import annotations

import tomllib
from pathlib import Path

VAIKIMISI = Path(__file__).resolve().parent.parent / "seadistused.toml"


class Seadistused(dict):
    """Sõnastik, mis lubab punktiga teid: s.get_path('kulu.max_kulum')."""

    def __init__(self, data: dict, juur: Path):
        super().__init__(data)
        self.juur = juur

    def get_path(self, tee: str, vaikimisi=None):
        cur = self
        for osa in tee.split("."):
            if not isinstance(cur, dict) or osa not in cur:
                return vaikimisi
            cur = cur[osa]
        return cur

    def fail(self, võti: str) -> Path:
        """Andmefaili tee seadistuste kausta suhtes."""
        p = Path(self["andmefailid"][võti])
        return p if p.is_absolute() else self.juur / p


def lae(tee: str | Path | None = None) -> Seadistused:
    p = Path(tee) if tee else VAIKIMISI
    with open(p, "rb") as f:
        return Seadistused(tomllib.load(f), p.resolve().parent)
