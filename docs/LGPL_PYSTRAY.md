# Conformità LGPL-3.0 per pystray

Mr. Rao utilizza **[pystray](https://github.com/moses-palmer/pystray)**
(Copyright © 2016–2022 Moses Palmér) sotto **GNU LGPL versione 3** (o successiva,
a scelta dell’utente, come da avviso del progetto).

Questo documento descrive come il progetto **rispetta** la LGPL. Non è un parere legale.

---

## 1. Cosa copre la LGPL qui

- **pystray** e i suoi file sorgente/binari della libreria  
- **Non** il resto del codice Mr. Rao (che ha la propria `LICENSE`)

---

## 2. Obblighi che adempiamo

| Obbligo tipico LGPL | Come lo soddisfaciamo |
|---------------------|------------------------|
| Fornire il testo della licenza | `licenses/pystray/COPYING.LGPL`, `COPYING`, copie gnu.org |
| Notice di copyright | `licenses/pystray/NOTICE.txt`, commenti in `mr_rao/tray.py`, UI ⓘ, footer |
| Non imporre restrizioni su pystray | La licenza Mr. Rao esclude esplicitamente pystray (e le altre terze parti) |
| Permettere modifica/debug della libreria | Import standard `import pystray`; ambiente Python o bundle modificabile |
| Accesso al sorgente di pystray | Link GitHub/PyPI + possibilità di `pip install pystray==…` |
| Attribuzione in prodotti derivati | `THIRD_PARTY.md` + cartella `licenses/` da includere nelle build |

---

## 3. Come sostituire o aggiornare pystray

### Installazione da sorgente (sviluppo)

```bat
cd <cartella del progetto>
venv\Scripts\activate
pip uninstall pystray
pip install pystray==0.19.5
REM oppure da un fork:
REM pip install git+https://github.com/moses-palmer/pystray.git
```

Riavviare Mr. Rao. Non è richiesto ricompilare il resto del progetto.

### Portable (PyInstaller)

1. Nella cartella del portable deve esserci `licenses\` (copiata dalla build).  
2. Il codice di pystray finisce tipicamente sotto `app\_internal\` (o simile).  
3. Un utente avanzato può sostituire i file del package `pystray` lì, oppure
   ricostruire il portable da sorgente dopo aver installato un’altra versione:

```bat
pip install "pystray @ git+https://github.com/moses-palmer/pystray.git"
scripts\build_portable.bat
```

### Disattivare il tray (scelta, non obbligo)

```bat
set MR_RAO_TRAY=0
```

L’app funziona senza icona di notifica; se la distribuzione **non** include
pystray, gli obblighi LGPL su pystray non si applicano a quel binario.
**Noi includiamo comunque notice e testi** quando pystray è presente.

---

## 4. Combinazione con la licenza Mr. Rao

Mr. Rao è distribuito sotto **GNU AGPL-3.0**, che la Free Software Foundation
indica come compatibile con la LGPL: una libreria LGPL può essere combinata in
un'opera AGPL-3.0.

Dal punto di vista pratico questa combinazione **semplifica** gli adempimenti:
l'obbligo LGPL più delicato è consentire all'utente di sostituire la libreria
con una propria versione, e l'AGPL impone già di distribuire il sorgente
completo. Chi riceve Mr. Rao ha per costruzione tutto il necessario per
ricompilarlo con un'altra pystray.

Nessuno deve chiedere permesso a Rao per usare, modificare o sostituire
**pystray**: quei diritti vengono dalla LGPL e restano intatti.

---

## 5. File da non rimuovere in una redistribuzione

```
LICENSE                 ← Mr. Rao
THIRD_PARTY.md
licenses/README.md
licenses/pystray/*      ← LGPL/GPL + NOTICE
docs/LGPL_PYSTRAY.md    ← consigliato
```

I nomi qui sopra sono quelli del repository. **Nel pacchetto portable il primo
si chiama `LICENSE.txt`**: `scripts/build_portable.bat` lo copia cambiandogli
nome. Chi controlla una redistribuzione cerca il file, non il percorso, e va
saputo prima di dichiararlo mancante. Gli altri conservano il nome.

`scripts/build_portable.bat` copia `LICENSE` (come `LICENSE.txt`),
`THIRD_PARTY.md`, l'intera `licenses\` e questo file nel pacchetto.
