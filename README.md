# Mr. Rao

**Dal documento al Markdown. Offline. Firmato Rao.**

Convertitore locale di PDF, Office, immagini (OCR), HTML, CSV e thread email `.eml` in Markdown puro. Privacy-first con detector italiani (email, telefoni, CF, P.IVA, IBAN, nomi). Nessun cloud.

![Mr. Rao](static/img/logo.svg)

---

## Funzionalità (implementate)

| Area | Dettaglio |
|------|-----------|
| Documenti | PDF, DOCX, DOC, XLSX, XLS, PPTX, PPT, HTML, CSV, JSON, XML, TXT, RTF |
| OCR | PNG, JPG, BMP, TIFF, WebP, GIF — **RapidOCR** offline (script latini) |
| Fallback PDF | Scansioni → OCR automatico (limite pagine configurabile) |
| Tabelle PDF | Estrazione tabelle → Markdown |
| Email | Parser `.eml` thread IT/EN, allegati elencati e **scaricabili** |
| Privacy IT | Email, telefoni `+39`, CF, IBAN, P.IVA, nomi + Scrubadub + **diff privacy** |
| Profili | Predefinito, email legali, fatture, solo OCR, LLM-ready, no redazione |
| UX | Multi-file, merge, **confronto 2 file**, progress, annulla, Raw/Preview, cronologia, Ctrl+V |
| Export | `.md`, `.txt`, copia pulita LLM, frontmatter YAML, **drag-out** `.md` |
| Hotfolder | Watch da UI + CLI (`watch inbox out`) |
| Tray | Icona system tray (Apri UI / Hotfolder / Esci) |
| Shell Windows | Invia a + menu contestuale **Apri con Mr. Rao** |
| CLI | `convert`, `watch`, `health` (anche via `MrRao.exe`) |
| Portable | `dist/MrRao-Portable` — **zero Python** sul PC destinazione (~390 MB) |
| Docker | `Dockerfile` + `docker-compose.yml` |
| Qualità | 23 test pytest + `scripts/quality_gate.bat` |

---

## Installazione (Windows)

Doppio clic su:

```
Installa Mr Rao.bat
```

Lo script:

1. Verifica Python  
2. Crea `venv`  
3. Installa `requirements.txt` (**include beautifulsoup4**)  
4. Esegue i test (gate)  
5. Crea il collegamento **Mr Rao** sul Desktop  

### BeautifulSoup4 — a cosa serve?

Serve a convertire il **corpo HTML delle email** in testo leggibile (rimuove tag, script, stili). Senza di essa i file `.eml` HTML resterebbero pieni di markup. Dettagli: [docs/BEAUTIFULSOUP.md](docs/BEAUTIFULSOUP.md).

---

## Avvio web

```
Avvia Mr Rao.bat
```

Apre **http://127.0.0.1:5000**

Variabili opzionali:

| Variabile | Default | Significato |
|-----------|---------|-------------|
| `MR_RAO_DEBUG` | `0` | `1` abilita debug Flask |
| `MR_RAO_PORT` | `5000` | Porta |
| `MR_RAO_MAX_UPLOAD_MB` | `50` | Limite upload |
| `MR_RAO_MAX_OCR_PAGES` | `50` | Max pagine OCR PDF |

---

## CLI

```bat
venv\Scripts\activate
python -m mr_rao.cli health
python -m mr_rao.cli convert documento.pdf -o out.md
python -m mr_rao.cli convert cartella\*.pdf --merge -o tutto.md
python -m mr_rao.cli watch .\inbox .\out --move-done
```

---

## API

| Endpoint | Descrizione |
|----------|-------------|
| `GET /api/health` | Healthcheck |
| `POST /api/convert` | Job asincrono (singolo file) → `{job_id}` |
| `POST /api/convert/batch` | Batch / merge |
| `POST /api/convert/sync` | Conversione sincrona |
| `GET /api/jobs/<id>` | Stato, progress, risultato |
| `POST /api/jobs/<id>/cancel` | Annulla job |

---

## Test e quality gate

```bat
scripts\quality_gate.bat
```

Oppure:

```bat
venv\Scripts\python -m pytest tests -q
```

Il gate (compileall + health + pytest) viene eseguito anche da `Installa Mr Rao.bat` e **prima del commit**.

---

## Portable (senza Python sul PC destinazione)

Su un PC di build (con Python una tantum):

```bat
scripts\build_portable.bat
```

Produce `dist\MrRao-Portable\` con **tutte** le dipendenze incluse (niente git/pip sul target).

Sul PC utente: doppio clic su **`Installa Mr Rao.bat`** → collegamento Desktop, icona, menu contestuale.

Dettagli: [docs/PORTABLE.md](docs/PORTABLE.md)

## Docker

```bat
docker compose up --build
```

---

## Struttura

```
markitdown-webapp/
├── app.py                 # Entry server
├── config.py              # Config / brand
├── mr_rao/
│   ├── app_factory.py
│   ├── routes.py
│   ├── converter.py
│   ├── eml_parser.py      # usa BeautifulSoup4
│   ├── ocr_service.py
│   ├── privacy.py
│   ├── jobs.py
│   └── cli.py
├── static/img/            # logo + favicon
├── templates/index.html
├── tests/
├── docs/
├── scripts/quality_gate.*
├── Installa Mr Rao.bat
└── Avvia Mr Rao.bat
```

---

## Documentazione

- [BeautifulSoup4](docs/BEAUTIFULSOUP.md)
- [Architettura](docs/ARCHITECTURE.md)
- [Privacy](docs/PRIVACY.md)
- [Changelog](docs/CHANGELOG.md)

---

*Mr. Rao — by Rao · Powered by MarkItDown, RapidOCR, Scrubadub, BeautifulSoup4*
