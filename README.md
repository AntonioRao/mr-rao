# Mr. Rao

**Turn PDFs, Office files, scans and emails into clean Markdown — with the personal data already stripped out.**
**All on your own machine, without sending anything anywhere.**

[![Version](https://img.shields.io/badge/version-1.3.1-3b82f6)](docs/CHANGELOG.md)
[![Tests](https://img.shields.io/badge/tests-161%20passing-10b981)](tests/)
[![Network](https://img.shields.io/badge/network-no%20outbound%20calls-8b5cf6)](#how-it-actually-stays-local)
[![Licence](https://img.shields.io/badge/licence-AGPL--3.0-f59e0b)](LICENSE)
[![Windows](https://img.shields.io/badge/Windows-portable%2C%20no%20Python-06b6d4)](docs/PORTABLE.md)

[🇬🇧 English](README.md) · **[🇮🇹 Italiano](README.it.md)**

![Mr. Rao — interface](docs/img/schermata.png)

> **Heads up:** Mr. Rao is built for **Italian** documents. It recognises *codice fiscale*, *partita IVA*, IBANs and Italian names, and its interface is in Italian. The code and its documentation are in English, and the redaction engine is designed to be extended to other countries — see [Contributing](CONTRIBUTING.md).

---

## The problem

You want to hand a document to ChatGPT, Claude or any other assistant. You need two things:

1. the text, clean, not a PDF;
2. **not** to hand over your client's tax ID while you're at it.

Online converters solve the first problem by creating the second: to convert the file, you have to upload it. If that file is an invoice, a medical record, a contract or an email thread with real people in it, you have just shipped it to a server you know nothing about.

Mr. Rao does the conversion **and** the redaction on your own computer. The file never moves.

---

## What it does

| | |
|---|---|
| 📄 **Documents** | PDF, DOCX, DOC, XLSX, XLS, PPTX, PPT, HTML, CSV, JSON, XML, TXT, RTF |
| 👁️ **Scans and photos** | Offline OCR on PNG, JPG, TIFF, WebP, BMP, GIF — and on scanned PDFs |
| 📊 **PDF tables** | Rebuilt as Markdown tables instead of unravelling into loose lines |
| 📧 **Email** | `.eml` files with the thread split message by message, attachments extractable |
| 🛡️ **Personal data** | Emails, phone numbers, tax IDs, VAT numbers, IBANs, names → replaced with placeholders |
| 🔍 **Verification** | A before/after view showing exactly what was removed |
| 📁 **Watched folder** | Drop files in one folder, the `.md` files appear in another |
| ⌨️ **Command line** | `convert`, `watch`, `health` — also from the portable executable |

---

## Getting started

### Windows, without installing Python

Download the portable package and double-click `Avvia Mr Rao.bat`. Nothing else needed: Python, the OCR models and every dependency are already inside (~390 MB).

### With Python

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

It opens at `http://127.0.0.1:5000`. If that port is busy it tells you **which instance** holds it and starts on the first free one.

### Command line

```bash
python -m mr_rao.cli convert invoice.pdf -o invoice.md
python -m mr_rao.cli convert folder\*.pdf --merge -o all.md
python -m mr_rao.cli watch .\inbox .\outbox --move-done
```

### Docker

```bash
docker compose up --build
```

Published **on localhost only**: the app has no authentication, so exposing it to a network has to be a deliberate choice (put a reverse proxy with auth in front).

---

## Real use cases

**Law firm — an email thread to attach to a case file.**
An `.eml` with twenty stacked replies becomes readable Markdown, one message at a time, with the attachments pulled out. The "legal email" profile strips names, addresses and contact details, so what's left can go to a consultant or an AI assistant without exposing the other parties.

**Accountant — invoices and bookkeeping.**
The "invoices" profile rebuilds the tables and hides tax ID, VAT number and IBAN **while leaving the amounts visible** — they're the reason you're reading the document in the first place.

**Anyone working with AI assistants.**
The "LLM-ready" profile produces lean text, no technical headers, personal data already replaced. Copy, paste, stop worrying.

**Digitised paper archives.**
Watched folder plus the "OCR only" profile: empty your scanner into one folder and find the Markdown in the other, without sitting in front of the screen.

**Anyone who has to show their work.**
Each file can carry a header with its origin, date, engine used and **how many redactions** were applied. Useful when the conversion itself needs documenting.

---

## What it does NOT do

Better said upfront:

- **It is not a layout translator.** It produces structured text, not a graphical clone of the PDF.
- **Name redaction is not infallible.** It relies on a list of common Italian names, so an unusual surname can slip through. That is exactly why the before/after view exists — **always check** before sharing.
- **OCR works no miracles.** On a skewed, blurry scan it gets things wrong, like everything else.
- **There is no authentication.** It is a local tool for one person, not a multi-user service.
- **The OCR language selector does not switch models yet.** It is already logged in the [backlog](docs/BACKLOG.md) as something to either implement properly or remove.

---

## How it actually stays local

Not a slogan — something you can check:

- **There is not a single outbound network call in the app's own code.** The only `urlopen` in the codebase points at `127.0.0.1`, and it exists to identify which process holds a busy port. One command proves it: `grep -rn "urlopen\|requests\." mr_rao/`
- **The OCR models ship with the package.** No download on first run.
- **Working folders never land in a synced directory.** On Windows, "Documents" often *is* the OneDrive folder: Mr. Rao detects that and falls back to a local folder, telling you why. This was a real bug, fixed in [1.3.0](docs/CHANGELOG.md).
- **The local server defends itself.** `Host` header allow-list (against DNS rebinding) and rejection of cross-site requests (against CSRF), so no page open in your browser can drive Mr. Rao.

---

## What's inside, transparently

Mr. Rao is **not** a fork of any of these projects: it uses them as dependencies, and their licences stay intact.

The conversion core is **[MarkItDown](https://github.com/microsoft/markitdown)** by Microsoft (MIT). OCR is **[RapidOCR](https://github.com/RapidAI/RapidOCR)** (Apache-2.0) on **[ONNX Runtime](https://onnxruntime.ai/)**. Everything else — Flask, BeautifulSoup, pdfplumber, Pillow, Scrubadub — is listed in full in **[THIRD_PARTY.md](THIRD_PARTY.md)**.

> *Mr. Rao is not affiliated with or endorsed by Microsoft or any of the projects mentioned.*

That list is not maintained by hand: [`scripts/gen_third_party.py`](scripts/gen_third_party.py) **generates** it from the metadata of the packages actually installed, and the quality gate fails when it drifts. The hand-written version had already got one licence wrong and omitted another one that carried real obligations — hence the automation.

Two libraries are **LGPL** (pystray and python-stdnum): licence texts, notices and replacement instructions live in [`licenses/`](licenses/).

---

## Licence

Copyright © 2026 Rao

Mr. Rao is **free software** under the **[GNU Affero General Public License v3.0](LICENSE)**.
You may use, study, modify and redistribute it — including commercially — under the terms of that licence.

The one obligation that matters in practice: **if you offer Mr. Rao to others over a network** (turn it into a web service, put it behind a company portal), section 13 of the AGPL requires you to make the source of your version, modifications included, available to those users. Used locally as intended, nothing changes.

Distributed **without any warranty**, in the hope that it will be useful.
Dependencies each remain under their own licence — see [THIRD_PARTY.md](THIRD_PARTY.md).

---

## Quality

```bash
scripts\quality_gate.bat
```

Four steps: compilation, dependency health, licence alignment, **161 tests**.

The tests do not just cover the happy path. They cover the defects that cost the most: the profile × format matrix that uncovered broken OCR on PDFs, option isolation between files of the same batch, the busy-port behaviour on Windows, the GET request that wrote to disk, the folders that ended up in the cloud. Every regression test was verified **failing against the old code** first — a test that passes with the bug in place proves nothing.

---

## Documentation

- [Architecture](docs/ARCHITECTURE.md) · [Privacy](docs/PRIVACY.md) · [Changelog](docs/CHANGELOG.md)
- [Backlog](docs/BACKLOG.md) — what's missing, in priority order
- [Portable build](docs/PORTABLE.md) · [Security](SECURITY.md) · [Contributing](CONTRIBUTING.md)

## Configuration

| Variable | Default | Meaning |
|----------|---------|---------|
| `MR_RAO_PORT` | `5000` | Local server port |
| `MR_RAO_MAX_UPLOAD_MB` | `50` | Limit for the **whole request**, not per file |
| `MR_RAO_MAX_OCR_PAGES` | `50` | Maximum OCR pages per PDF |
| `MR_RAO_MAX_WORKERS` | `2` | Concurrent conversions; the rest queue |
| `MR_RAO_FOLDER_ROOT` | automatic | Where to create the working folders |
| `MR_RAO_ALLOWED_HOSTS` | `127.0.0.1,localhost` | Hosts accepted in the `Host` header |

---

*Mr. Rao — from document to Markdown. Offline.*
