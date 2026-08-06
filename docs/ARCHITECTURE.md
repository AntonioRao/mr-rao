# Architettura Mr. Rao

## Panoramica

```
Browser ──HTTP──► Flask (routes) ──► jobs (thread pool) ──► converter
                                                         ├── eml_parser (+ BeautifulSoup4)
                                                         ├── markitdown (+ Magika)
                                                         ├── ocr_service (RapidOCR + pdfplumber)
                                                         └── privacy (regex IT + Scrubadub)
CLI / SendTo ──► mr_rao.cli convert ──► stesso converter
Watch (UI/CLI) ──► watch_service loop ──► converter
Tray ──► open browser / quit
```

## Frontend (UI 2.0)

| Asset | Ruolo |
|-------|--------|
| `templates/index.html` | Markup semantico, gerarchia journey |
| `static/css/app.css` | Design system: glass, aurora, float, glow |
| `static/js/app.js` | Interazioni, job poll, tooltip, watch |
| `static/img/*` | Logo, favicon, ico Desktop |

**Journey UI principale**

1. Hero (brand)  
2. Drop zone (azione primaria)  
3. Control bar (profilo + privacy)  
4. Opzioni avanzate (collassate)  
5. Risultato (tabs + export)  
6. Secondari: sessione + cartella automatica  

## Moduli backend

| Modulo | Responsabilità |
|--------|----------------|
| `config.py` | Brand, path (frozen/dev), limiti, env |
| `mr_rao/app_factory.py` | Factory Flask, middleware sicurezza Host/CSRF |
| `mr_rao/routes.py` | HTTP API + template |
| `mr_rao/jobs.py` | Job store in-memory, progress, cancel, worker limit |
| `mr_rao/converter.py` | Pipeline unica + frontmatter + merge + fallback text |
| `mr_rao/eml_parser.py` | Thread email → Markdown + allegati |
| `mr_rao/ocr_service.py` | OCR immagini/PDF + tabelle |
| `mr_rao/privacy.py` | Redaction granulare IT |
| `mr_rao/profiles.py` | Preset conversione |
| `mr_rao/watch_service.py` | Hotfolder in-process |
| `mr_rao/tray.py` | System tray opzionale |
| `mr_rao/cli.py` | CLI convert / watch / health |
| `mr_rao/portcheck.py` | Porta libera + messaggi multi-istanza |

## Flusso conversione

1. Upload validato (estensione + size richiesta)  
2. Bytes → temp monouso (`convert_bytes`)  
3. Engine: `auto` | `rapidocr` | `markitdown`  
4. Privacy opzionale → report + eventuale `markdown_raw`  
5. Frontmatter YAML opzionale  
6. Cleanup temp  

## Sicurezza locale

- Bind default `127.0.0.1`  
- Allow-list header `Host` (anti DNS rebinding)  
- Check `Origin` su mutazioni (anti CSRF basico)  
- `debug` solo con `MR_RAO_DEBUG=1`  
- Nessuna autenticazione (single-user locale)  

## Gap noti (vedi BACKLOG)

- Shell **SendTo / Apri con** → solo CLI, non UI (P0)  
- Lingua OCR advisory (P3)  

## Documentazione correlata

- [BACKLOG.md](BACKLOG.md) — priorità P0–P4  
- [PORTABLE.md](PORTABLE.md) — build offline  
- [PRIVACY.md](PRIVACY.md) — redazioni  
- [BEAUTIFULSOUP.md](BEAUTIFULSOUP.md) — HTML email  
