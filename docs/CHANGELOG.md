# Changelog

## 1.1.0 — Feature pack + portable (build verificata)

### Build portable (eseguita e testata)
- `scripts/build_portable.bat` riparato (encoding cmd) e eseguito con successo
- Output: `dist/MrRao-Portable/` (~390 MB) con `app/MrRao.exe` + dipendenze
- Smoke test: `MrRao.exe health` e `MrRao.exe convert` OK
- Fix crash console Windows: niente freccia Unicode in `app.py` (cp1252)
- CLI gestita **prima** dell'avvio server (health/convert/file drop)

### Icone
- Lockup **Mr** + **RAO** (RAO grande, Mr leggibile, no clipping)
- `mr-rao.ico` multi-size + shortcut Desktop automatico

### Feature
- System tray (pystray)
- Profili preset (email legali, fatture, solo OCR, LLM-ready, no privacy)
- Diff privacy (prima/dopo + highlight segnaposto)
- Allegati `.eml` scaricabili dall'UI
- Hotfolder watch da UI (`/api/watch`)
- Confronto 2 file (Documento A / B)
- Drag-out `.md` (Chrome/Edge) dal bottone/output
- Menu contestuale Windows + Invia a
- Export `.md` / `.txt` / copia pulita LLM
- Multi-file + merge batch, progress, annulla
- Preview Raw/Markdown, cronologia sessione, Ctrl+V immagine
- Privacy IT (email, telefoni, CF, IBAN, P.IVA, nomi) + report
- CLI `convert` / `watch` / `health`
- Tabelle PDF, frontmatter YAML, OCR RapidOCR offline
- Parser `.eml` thread IT/EN + BeautifulSoup4

### Portable install
- Sul target: **nessun Python, pip o git**
- `Installa Mr Rao.bat` → `%LOCALAPPDATA%\MrRao` + Desktop + shell
- Docs: `docs/PORTABLE.md`

## 1.0.0 — Mr. Rao

### Brand
- Rebrand completo da MarkItDown / RAOmark a **Mr. Rao**
- Logo SVG, favicon SVG, bat, README, footer

### Fix
- Aggiunto **beautifulsoup4** a requirements e installer
- Label motore: RapidOCR (non piu PaddleOCR)
- Font system-ui (offline reale)
- Upload con UUID (no collisioni)
- `debug` da env `MR_RAO_DEBUG`
- Toggle privacy HTML valido
- Errori 500 non espongono stack al client
- Thread email: match piu vicino all'inizio, depth limit

### Qualita
- Architettura a moduli `mr_rao/`
- Healthcheck `/api/health`
- Job async con progress + cancel
- Test pytest + `scripts/quality_gate.*`
- Docker / compose
