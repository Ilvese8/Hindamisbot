"""Viisakas HTTP-klient avalike teenuste jaoks: viivitus, timeout, korduskatse, vahemälu."""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

import requests


class Klient:
    def __init__(self, kasutajaagent: str, viivitus_s: float = 1.0, timeout_s: int = 30,
                 vahemalu: Path | None = None, vahemalu_paevi: float = 7.0):
        self.s = requests.Session()
        self.s.headers["User-Agent"] = kasutajaagent
        self.viivitus_s = viivitus_s
        self.timeout_s = timeout_s
        self.vahemalu = vahemalu
        self.vahemalu_s = vahemalu_paevi * 86400
        self._viimane = 0.0
        if vahemalu:
            vahemalu.mkdir(parents=True, exist_ok=True)

    def _vm_fail(self, meetod: str, url: str, params) -> Path | None:
        if not self.vahemalu:
            return None
        h = hashlib.sha1(f"{meetod}|{url}|{json.dumps(params, sort_keys=True)}".encode()).hexdigest()
        return self.vahemalu / f"{h}.json"

    def json(self, url: str, params=None, data=None, meetod: str = "GET"):
        vm = self._vm_fail(meetod, url, params or data)
        if vm and vm.exists() and time.time() - vm.stat().st_mtime < self.vahemalu_s:
            return json.loads(vm.read_text(encoding="utf-8"))
        viga = None
        for katse in range(3):
            oota = self.viivitus_s - (time.monotonic() - self._viimane)
            if oota > 0:
                time.sleep(oota)
            try:
                self._viimane = time.monotonic()
                r = self.s.request(meetod, url, params=params, data=data, timeout=self.timeout_s)
                if r.status_code == 429 or r.status_code >= 500:
                    raise requests.HTTPError(f"HTTP {r.status_code}")
                r.raise_for_status()
                tulemus = r.json()
                if vm:
                    vm.write_text(json.dumps(tulemus, ensure_ascii=False), encoding="utf-8")
                return tulemus
            except (requests.RequestException, ValueError) as e:
                viga = e
                time.sleep(2 ** katse)
        raise ConnectionError(f"Päring ebaõnnestus: {url} ({viga})")
