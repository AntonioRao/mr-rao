# Mr. Rao architecture

*Questo documento in italiano: [ARCHITECTURE.md](ARCHITECTURE.md).*

## Overview

```
Browser ──HTTP──► Flask (routes) ──► jobs (thread pool) ──► converter
                                                         ├── eml_parser (+ BeautifulSoup4)
                                                         ├── markitdown (+ Magika)
                                                         ├── ocr_service (RapidOCR + pdfplumber)
                                                         └── privacy (pack sequence: core + it + en)
CLI / SendTo ──► mr_rao.cli convert ──► same converter
Watch (UI/CLI) ──► watch_service loop ──► converter
Tray ──► open browser / quit / restore clipboard
Shortcut ──► clipboard ──► same privacy engine ──► clipboard
```

## Frontend (UI 2.0)

| Asset | Role |
|-------|------|
| `templates/index.html` | Semantic markup, journey hierarchy |
| `static/css/app.css` | Design system: glass, aurora, float, glow |
| `static/js/app.js` | Interactions, job polling, tooltips, watch |
| `static/img/*` | Logo, favicon, desktop icon |

**Main UI journey**

1. Hero (brand)
2. Drop zone (primary action)
3. Control bar (profile + privacy)
4. Advanced options (collapsed)
5. Result (tabs + export)
6. Secondary: session + watched folder

## Backend modules

| Module | Responsibility |
|--------|----------------|
| `app.py` | Entry point of the local server. It tries the application window **first** and falls back to the browser; it starts the tray, the watcher and the busy-port check |
| `console_win.py` | It sits at the root and not in `mr_rao/` on purpose: it attaches the Windows console **before** any other module prints. The executable is built with no console, so a double-click opens no black window; without this attach, `MrRao.exe convert` would print nothing and look like it had done nothing |
| `config.py` | Brand, paths (frozen/dev), limits, env |
| `mr_rao/app_factory.py` | Flask factory, Host/CSRF security middleware |
| `mr_rao/routes.py` | HTTP API + templates |
| `mr_rao/jobs.py` | In-memory job store, progress, cancel, worker limit |
| `mr_rao/converter.py` | Single pipeline + frontmatter + merge + text fallback |
| `mr_rao/eml_parser.py` | Email thread → Markdown + attachments |
| `mr_rao/ocr_service.py` | OCR for images/PDFs + tables |
| `mr_rao/docx_export.py` | Redacted Markdown → `.docx`. **Regenerates** the document instead of covering the original: under a black rectangle the text would still be there |
| `mr_rao/i18n.py` | Both languages in a single dictionary, shared by server, templates and JavaScript. The interface language does **not** choose the recognisers |
| `mr_rao/privacy.py` | The engine: recogniser sequence, packs, suspects, OCR recovery |
| `mr_rao/finestra.py` | An application window instead of a browser tab: same interface, same server, the system's own rendering engine. The close button **hides** it — the program stays in the tray. If it cannot open, it falls back to the browser |
| `mr_rao/redazione_pdf.py` | Redacting a PDF **without rasterising it**: removes the glyph bytes from the content stream and puts the placeholder there, in a standard font. The document that comes out is still selectable and weighs the same. Reachable from the interface: a «See the preview» button on the result, before/after pages side by side, a green box on every placeholder |
| `mr_rao/it_names.py` | Italian vocabularies: first names, surnames, capitalised common words |
| `mr_rao/en_formats.py` | Anglo validators (NHS, NINO, SSN, ITIN, ABA, SIN, ABN, TFN, MRZ) with their test vectors beside them |
| `mr_rao/user_folders.py` | Working folders, detection of synchronised folders |
| `mr_rao/profiles.py` | Conversion presets |
| `mr_rao/watch_service.py` | In-process hotfolder |
| `mr_rao/tray.py` | Optional system tray; hosts the shortcut's notification and restore |
| `mr_rao/appunti.py` | Keyboard shortcut that redacts the clipboard. Three layers: the part that **decides** receives read and write from outside and is the one under test; the rest talks to Windows. Uses `RegisterHotKey`, **never** a keyboard hook — see [SCORCIATOIA-APPUNTI.en.md](SCORCIATOIA-APPUNTI.en.md) |
| `mr_rao/cli.py` | CLI convert / watch / health |
| `mr_rao/__main__.py` | Entry point for `python -m mr_rao`: two lines calling `cli.main` |
| `mr_rao/portcheck.py` | Free port + multi-instance messages |

## The privacy engine

Every recogniser is a **`Passo`** in `SEQUENZA`, and declares four things: a
stable name, its pack, the switch that turns it on, and a priority.
`apply_privacy_filter` is a loop: a step runs if its pack is among the
chosen ones **and** its switch is on.

**There are four packs** (`CORE`, `IT`, `EN`, `ATTI`), and they do not all
answer the same question. The first three separate what holds everywhere from
what holds in one country only: the core cannot be switched off — an IBAN
passes mod-97 in every SEPA country, a card passes Luhn everywhere — and the
two national ones stack, because the Italian firm with an English contract is
the real use case. `ATTI` instead says **for which trade**: land registry
references, case numbers and vehicle plates are data a notary wants removed
and a purchasing office wants kept, which is why it is **off by default**.

Where they are chosen is not the same for all of them: `CORE`, `IT` and `EN`
are selectable from the interface, from JSON and from the command line
(`--no-pack-it`, `--no-pack-en`). **`ATTI` only from the interface and from
JSON**: the command line has no option that turns it on.

**Priority belongs to the data type, not to the pack.** Italian tax code
(it) and SSN (en) run together, before phone numbers: that is what stops a
phone number from swallowing a VAT number. If the order followed the packs,
adding a third one would break it, and it would show up as a wrong redaction
rather than as an ordering mistake.

**Prose or form** (`PrivacyOptions.prosa`) decides how much to demand before
substituting a name: in a letter a single hit in the lists is enough, on a
form it is almost always a field label. Measured across more than a hundred
administrative documents and 1500 real emails: demanding two hits removes
2739 wrong substitutions on forms and costs 609 on letters.

The signal that decides it lives **in the PDF, not in the text**: the boxes
on a form are vector lines and rectangles, they survive reading the file and
die in the conversion. That is why `_e_prosa()` lives in `converter.py` and
not in the engine. On scans it stays `None`, because counting vectors on an
image would give zero and zero would be read as "prose": the right answer
for the wrong reason.

**Names work by levels of evidence.** `_scrub_names` runs **nine** rules in
order, from the strongest signal to the weakest: a professional title in
front; a role, a colon and a surname in capitals (`Il Ministro: GIORGETTI`);
a name before an email address; a name after one; a name next to a valid
Italian tax code; a declared role (`il cliente Mario Rossi`); a form field
(`Nome: Mario Rossi`); a closing formula (`Cordiali saluti, Esposito`); an
adjacent pair recognised in the lists. The first eight substitute; the ninth
substitutes only with as many hits as the prose/form threshold demands. A
single listed word with nothing around it becomes a **suspect** and not a
substitution: the document stays readable and whoever checks knows where to
look.

## Conversion flow

1. Upload validated (extension + requested size)
2. Bytes → single-use temp file (`convert_bytes`)
3. Engine: `auto` | `rapidocr` | `markitdown`
4. Document type inferred (`_e_prosa`) unless forced
5. Optional privacy → report + possible `markdown_raw`
6. Optional YAML frontmatter
7. Temp cleanup

## Local security

- Default bind `127.0.0.1`
- `Host` header allow-list (anti DNS rebinding), **including on `0.0.0.0`**:
  this machine's addresses, not `*`
- External `Sec-Fetch-Site` refused on mutations, with `Origin` as a
  fallback for clients that do not send it (anti CSRF)
- `frame-ancestors 'none'`, `nosniff`, `no-referrer` on every response
- Time cap on OCR (`MR_RAO_OCR_TIMEOUT`), checked between pages like
  cancellation
- `debug` only with `MR_RAO_DEBUG=1`
- No authentication (local single user)

Detail and reasoning in [SECURITY.en.md](../SECURITY.en.md).

## Known gaps (see BACKLOG)

- **Scans**: the recognisers look for valid shapes, the OCR produces almost
  valid ones. Mitigated two ways — checksum-constrained recovery for tax
  codes and IBANs, and suspect flagging for the rest — but it remains the
  main limit on effectiveness (P0-ter).
- **Italian names**: on administrative documents the recogniser still
  produces thousands of wrong substitutions, measured across more than a
  hundred blank documents (#5). The prose/form parameter removes most of
  them, but the list-based method has a precision ceiling that incremental
  constraints do not raise.
- **Interface in Italian and English** (#1, phase 3): chosen from the
  browser, switchable with one click, and the produced document follows the
  same language. The command line stays Italian.
- **No authentication**: a local tool for one person, not a service.

## Related documentation

- [BACKLOG.md](BACKLOG.md) — priorities P0–P4 *(Italian)*
- [PORTABLE.md](PORTABLE.md) — offline build *(Italian)*
- [PRIVACY.en.md](PRIVACY.en.md) — redaction
- [BEAUTIFULSOUP.md](BEAUTIFULSOUP.md) — HTML email *(Italian)*
