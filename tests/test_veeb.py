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
    lehekülg = " ".join(m.value for m in at.markdown)
    assert "Sinu kinnisvara" in lehekülg and "turuväärtus" in lehekülg
    hinda = next(b for b in at.button if b.label == "Hinda")
    assert hinda.disabled            # ilma valitud aadressita ei saa hinnata
    # keele vahetus nupuga ET/EN
    at.session_state["keelevalik"] = "EN"
    at.run()
    assert not at.exception
    lehekülg = " ".join(m.value for m in at.markdown)
    assert "Your property" in lehekülg
    assert any(b.label == "Estimate" for b in at.button)


def test_tulemuse_kaart_mõlemas_keeles(monkeypatch):
    """Tulemuse kaart, meetodikaardid ja allalaadimised – eesti ja inglise keeles."""
    import sys
    sys.path.insert(0, str(JUUR / "tests"))
    import test_hindamisbot as TH
    from hindamisbot.hindaja import Hindaja
    s = TH.lae(JUUR / "seadistused_naidis.toml")
    h = Hindaja(s, vorguta=True)
    hinnang = h.hinda(TH.korter(), kuupäev=TH.KP)
    for keel, tekst, nupp in (("et", "Hinnanguline turuväärtus", "Laadi alla aruanne (Word)"),
                              ("en", "Estimated market value", "Download report (Word)")):
        at = AppTest.from_file(str(JUUR / "streamlit_app.py"), default_timeout=30)
        at.session_state["keel"] = keel
        at.session_state["keelevalik"] = keel.upper()
        at.session_state["hinnang"] = hinnang
        at.run()
        assert not at.exception
        lehekülg = " ".join(m.value for m in at.markdown)
        assert tekst in lehekülg and 'class="result"' in lehekülg and 'class="methods"' in lehekülg
        assert nupp in [b.label for b in at.get("download_button")]
