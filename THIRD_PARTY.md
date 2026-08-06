# Componenti di terze parti — Mr. Rao

Mr. Rao **non** è un fork di questi progetti: li usa come dipendenze.
Le loro licenze restano integre e **prevalgono** sui rispettivi file.

## Elenco principale

| Progetto | Uso in Mr. Rao | Licenza (orientativa) | Repository / sito |
|----------|----------------|----------------------|-------------------|
| [MarkItDown](https://github.com/microsoft/markitdown) | Conversione documenti → Markdown | MIT | Microsoft |
| [RapidOCR](https://github.com/RapidAI/RapidOCR) (`rapidocr_onnxruntime`) | OCR offline su immagini/PDF | Apache-2.0 | RapidAI |
| [ONNX Runtime](https://onnxruntime.ai/) | Runtime modelli OCR / Magika | MIT | Microsoft |
| [Flask](https://github.com/pallets/flask) | Server web locale | BSD-3-Clause | Pallets |
| [Werkzeug](https://github.com/pallets/werkzeug) | WSGI / utilità Flask | BSD-3-Clause | Pallets |
| [Beautiful Soup](https://www.crummy.com/software/BeautifulSoup/) (`beautifulsoup4`) | HTML email → testo | MIT | Leonard Richardson |
| [Scrubadub](https://github.com/LeapBeyond/scrubadub) | Redazione PII (base) | MIT | LeapBeyond |
| [pdfplumber](https://github.com/jsvine/pdfplumber) | PDF, tabelle, raster pagine | MIT (verificare NOTICE del pacchetto) | jsvine |
| [Pillow](https://github.com/python-pillow/Pillow) | Immagini | HPND / MIT-CMU | Python Pillow |
| [Magika](https://github.com/google/magika) | Rilevamento tipo file (via MarkItDown) | Apache-2.0 | Google |
| [pystray](https://github.com/moses-palmer/pystray) | Icona system tray (opzionale) | **LGPL-3.0** | moses-palmer |

Altre dipendenze transitive (numpy, opencv, scikit-learn, nltk, …) compaiono in `pip freeze` / ambiente virtuale e restano sotto le rispettive licenze PyPI.

## Compatibilità con la licenza di Mr. Rao

La [LICENSE](LICENSE) di Mr. Rao limita l’**uso commerciale del codice e del prodotto Mr. Rao** (autorizzazione richiesta).

Questo **non** vieta di usare MarkItDown, RapidOCR, Flask, ecc. da soli sotto MIT/Apache/BSD.

### Nota su pystray (LGPL-3.0)

- Uso in sviluppo da sorgente con package installato è tipicamente accettabile.
- **Redistribuzione binaria** (es. PyInstaller che include pystray) richiede di rispettare la LGPL (diritto di sostituire la libreria, notice, eventuale offerta del codice oggetto / istruzioni di relink a seconda del caso).
- Il tray si può disattivare con `MR_RAO_TRAY=0` se si preferisce non includere pystray in una distribuzione commerciale.

## Attribuzione consigliata

Quando redistribuisci Mr. Rao, conserva almeno:

- `LICENSE` (Mr. Rao)
- `THIRD_PARTY.md` (questo file)
- notice delle librerie se richiesti dai rispettivi package

## Aggiornamento

Le licenze sopra sono rilevate dai metadata dei package installati e dalle pagine ufficiali dei progetti; verificare sempre i file LICENSE nei repository upstream prima di una distribuzione formale.
