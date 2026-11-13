# Testversiooni paigaldus tasuta lingile (Streamlit Community Cloud)

Tulemus: avalik link kujul `https://<nimi>.streamlit.app`, kus saab sisestada aadressi ja alla laadida aruande.
Vaja on GitHubi kontot (tasuta). Programmeerida ega käsurida kasutada ei pea.

## 1. Pane kood GitHubi

1. Logi sisse aadressil https://github.com (vajadusel loo konto).
2. Paremal üleval **+ → New repository**.
   - Repository name: `hindamisbot`
   - Vali **Public**. Tasuta paketis võib olla piiramatult avalikke rakendusi, privaatseid ainult üks.
     Koodis pole paroole ega võtmeid, nii et avalik repositoorium on ohutu.
   - Vajuta **Create repository**.
3. Uuel lehel vajuta lingile **uploading an existing file**.
4. Paki `hindamisbot.zip` lahti. Ava kaust `hindamisbot` ja lohista **kogu selle sisu** (mitte kausta ennast)
   brauseriaknasse: kaustad `hindamisbot/`, `andmed/`, `tests/`, `.streamlit/` ning failid `streamlit_app.py`,
   `requirements.txt`, `seadistused.toml` jne.
   - Kaust `.streamlit` on peidetud. macOS-is näed seda Finderis klahvidega Cmd+Shift+. ,
     Windowsis Exploreris valikuga **Vaade → Peidetud üksused**. Kui see jääb üles laadimata, töötab rakendus
     ikkagi, ainult kujundus on vaikimisi.
5. Vajuta **Commit changes**.

Kontrolli, et repositooriumi esilehel on näha `streamlit_app.py` ja `requirements.txt` (mitte ainult üks kaust).

## 2. Käivita rakendus

1. Ava https://share.streamlit.io ja logi sisse GitHubi kontoga. Luba Streamlitil GitHubi lugeda.
2. Vajuta **Create app → Deploy a public app from GitHub**.
3. Täida väljad:
   - Repository: `<sinu-kasutaja>/hindamisbot`
   - Branch: `main`
   - Main file path: `streamlit_app.py`
   - App URL: vali nimi, nt `kinnisvara-hinnang`
4. **Advanced settings → Python version: 3.12**. Bot vajab vähemalt versiooni 3.11.
5. Vajuta **Deploy**. Esimene käivitus võtab paar minutit.

Valmis: link on `https://kinnisvara-hinnang.streamlit.app`.

## 3. Muudatused

Kui muudad GitHubis mõnd faili (nt `seadistused.toml` korrektsioonitegureid), uueneb rakendus mõne minuti jooksul ise.

## Teadaolevad piirangud

- **Uinumine:** rakendus jääb pärast 12 tundi ilma külastusteta magama. Järgmine külastaja näeb nuppu, mis selle
  äratab. Ärkamine võtab umbes minuti.
- **Serveri asukoht:** Streamlit Community Cloud töötab välismaistes andmekeskustes. Kui mõni Eesti riigi teenus
  välismaa IP-sid piirab, näitab rakendus selle kohta hoiatust ja jätkab ülejäänud andmetega. Sel juhul on lahendus
  Eesti või EL-i server.
- **Koormus:** ühest brauserist saab teha kuni 20 hinnangut tunnis (`MAX_HINNANGUID_TUNNIS` failis
  `streamlit_app.py`). Hinnastatistika ja ehitisregistri liidesed pole ametlikult dokumenteeritud. Enne laiemat
  avalikustamist küsi Maa- ja Ruumiametilt (maaruum@maaruum.ee), kas selline kasutus sobib.
- **Vastutus:** leht ja aruanne ütlevad selgelt, et tegemist on automaatse esmase hinnanguga, mitte eksperthinnanguga.

## Kohalik käivitamine (valikuline)

```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```
