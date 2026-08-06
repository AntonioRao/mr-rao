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

- Uso **non commerciale** di Mr. Rao: ok (con attribuzione Mr. Rao).  
- Uso **commerciale** di Mr. Rao: serve autorizzazione a Rao.  
- In **entrambi** i casi, i diritti LGPL su **pystray** restano intatti:
  nessuno deve “chiedere a Rao” per usare, modificare o sostituire **pystray**.

---

## 5. File da non rimuovere in una redistribuzione

```
LICENSE                 ← Mr. Rao
THIRD_PARTY.md
licenses/README.md
licenses/pystray/*      ← LGPL/GPL + NOTICE
docs/LGPL_PYSTRAY.md    ← consigliato
```

`scripts/build_portable.bat` copia `LICENSE`, `THIRD_PARTY.md` e `licenses\` nel pacchetto.
