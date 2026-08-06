# RAOmark

**Convertitore intelligente di documenti in Markdown — 100% offline, zero API.**

Trasforma PDF, DOCX, XLSX, PPTX, HTML, CSV, TXT e immagini in Markdown puro con un semplice drag & drop. Include OCR integrato per documenti scansionati e un parser dedicato per thread email `.eml` con anonimizzazione automatica dei dati sensibili.

---

## ✨ Funzionalità

| Feature | Dettaglio |
|---------|-----------|
| 📄 **Documenti** | PDF, DOCX, DOC, XLSX, XLS, PPTX, PPT, HTML, CSV, JSON, XML, TXT, RTF |
| 👁️ **OCR immagini** | PNG, JPG, BMP, TIFF, WebP — via RapidOCR (offline, no GPU) |
| 🔄 **Fallback automatico** | PDF scansionati → OCR pagina per pagina automatico |
| 📧 **Thread email** | Parse .eml completo con separazione reply-chain |
| 🛡️ **Privacy filter** | Anonimizza email, telefoni, nomi (Scrubadub, locale) |
| ⚡ **Zero cloud** | Tutto gira in locale, nessun dato inviato a server esterni |

---

## 🚀 Installazione (nuovo PC)

Fai doppio clic su:
```
Installa MarkItDown.bat
```

Lo script verifica Python, crea un ambiente virtuale e installa tutte le dipendenze.

## ▶️ Avvio

Fai doppio clic su:
```
Avvia MarkItDown.bat
```

L'app si avvia su **http://127.0.0.1:5000** e apre il browser automaticamente.

---

## 🏗️ Stack

- **Backend**: Python 3.x + Flask
- **Conversione documenti**: [MarkItDown](https://github.com/microsoft/markitdown) (Microsoft)
- **OCR**: [RapidOCR](https://github.com/RapidAI/RapidOCR) via `rapidocr_onnxruntime`
- **PDF OCR fallback**: pdfplumber + Pillow
- **Privacy**: [Scrubadub](https://github.com/LeapBeyond/scrubadub)
- **Email parser**: stdlib `email` + BeautifulSoup4

---

## 📁 Struttura

```
raomark/
├── app.py                   ← Server Flask
├── requirements.txt         ← Dipendenze
├── Avvia RAOmark.bat        ← Launcher
├── Installa RAOmark.bat     ← Installer
├── templates/
│   └── index.html           ← UI
└── uploads/                 ← Temp (auto-pulita)
```

---

*RAOmark — by RAO*
