"""Veebiliidese suitsutest (Streamlit AppTest), ilma võrguta."""
from pathlib import Path

from streamlit.testing.v1 import AppTest

JUUR = Path(__file__).resolve().parent.parent


def test_veebiliides_hindab_naidisandmetega(monkeypatch):
    import hindamisbot.seadistused as sd
    from hindamisbot.hindaja import Hindaja
    algne_lae = sd.lae
    monkeypatch.setattr("hindamisbot.seadistused.lae", lambda *_: algne_lae(JUUR / "seadistused_naidis.toml"))
    algne_init = Hindaja.__init__
    monkeypatch.setattr(Hindaja, "__init__", lambda self, s, **kw: algne_init(self, s, vorguta=True))

    at = AppTest.from_file(str(JUUR / "streamlit_app.py"), default_timeout=30).run()
    assert not at.exception
    assert at.title[0].value == "Sinu kinnisvara turuväärtus"
    hinda = next(b for b in at.button if b.label == "Hinda")
    assert hinda.disabled            # ilma valitud aadressita ei saa hinnata
