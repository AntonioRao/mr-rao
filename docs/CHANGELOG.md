# Changelog

## 1.1.0 — Feature pack + portable

### Icone
- Lockup **Mr** + **RAO** ridisegnato (RAO grande, Mr leggibile, no clipping)
- `mr-rao.ico` multi-size + shortcut Desktop automatico

### Feature
- System tray (pystray)
- Profili preset (email legali, fatture, solo OCR, LLM-ready…)
- Diff privacy (prima/dopo + highlight segnaposto)
- Allegati `.eml` scaricabili dall’UI
- Hotfolder watch da UI (`/api/watch`)
- Confronto 2 file (Documento A / B)
- Drag-out `.md` (Chrome/Edge) dal bottone/output
- Menu contestuale Windows + Invia a

### Portable
- `scripts/build_portable.bat` → PyInstaller onedir offline
- `Installa Mr Rao.bat` nel pacchetto: **nessun Python/git sul target**
- Docs: `docs/PORTABLE.md`

## 1.0.0 — Mr. Rao

### Brand
- Rebrand completo da MarkItDown / RAOmark a **Mr. Rao**
- Logo SVG, favicon SVG, bat, README, footer

### Fix
- Aggiunto **beautifulsoup4** a requirements e installer
- Label motore: RapidOCR (non più PaddleOCR)
- Font system-ui (offline reale)
- Upload con UUID (no collisioni)
- `debug` da env `MR_RAO_DEBUG`
- Toggle privacy HTML valido
- Errori 500 non espongono stack al client
- Thread email: match più vicino all’inizio, depth limit

### Qualità
- Architettura a moduli `mr_rao/`
- Healthcheck `/api/health`
- Job async con progress + cancel
- Test pytest + `scripts/quality_gate.*`
- Docker / compose

### UX
- Multi-file + merge batch
- Preview Markdown
- Copia pulita / export `.txt`
- Cronologia sessione
- Ctrl+V immagine
- Limite size lato client
- Progress bar

### Privacy
- Detector IT granulari + report redazioni

### Feature
- CLI `convert` / `watch` / `health`
- Tabelle PDF
- Frontmatter YAML
- Lingua OCR selezionabile
