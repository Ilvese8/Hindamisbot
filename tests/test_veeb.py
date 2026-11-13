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
    at.text_input[0].input("Näidise tn 1-15, Tallinn")
    at.selectbox[0].select("Korter")
    at.number_input[0].set_value(51.2)
    at.number_input[2].set_value(1968)
    at.button[0].click()
    at.run()
    assert not at.exception and not at.error
    meetrikad = {m.label: m.value for m in at.metric}
    assert meetrikad["Hinnanguline turuväärtus"].endswith("€")
    assert [b.label for b in at.get("download_button")] == ["Laadi alla aruanne (Word)", "Laadi alla aruanne (Markdown)"]
