# Architettura Mr. Rao

## Panoramica

```
Browser ──HTTP──► Flask (routes) ──► jobs (thread) ──► converter
                                                      ├── eml_parser (+ BeautifulSoup4)
                                                      ├── markitdown
                                                      ├── ocr_service (RapidOCR + pdfplumber)
                                                      └── privacy (regex IT + Scrubadub)
```

## Moduli

| Modulo | Responsabilità |
|--------|----------------|
| `config.py` | Brand, path, limiti, env |
| `mr_rao/app_factory.py` | Factory Flask |
| `mr_rao/routes.py` | HTTP API + UI |
| `mr_rao/jobs.py` | Job store in-memory, progress, cancel |
| `mr_rao/converter.py` | Pipeline unica + frontmatter + merge |
| `mr_rao/eml_parser.py` | Thread email → Markdown |
| `mr_rao/ocr_service.py` | OCR immagini/PDF + tabelle |
| `mr_rao/privacy.py` | Redaction granulare |
| `mr_rao/cli.py` | CLI convert / watch / health |

## Flusso conversione

1. Upload validato (estensione + size)
2. Bytes in temp file monouso (`convert_bytes`) — riduce dwell time su disco
3. Engine: `auto` | `rapidocr` | `markitdown`
4. Privacy opzionale → report conteggi
5. Frontmatter YAML opzionale
6. Cleanup temp

## Sicurezza locale

- Bind default `127.0.0.1`
- `debug` solo con `MR_RAO_DEBUG=1`
- Errori generici al client; dettagli in console server
- Nessuna autenticazione (uso single-user locale)
