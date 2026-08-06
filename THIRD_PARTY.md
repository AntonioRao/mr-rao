# Componenti di terze parti — Mr. Rao

Mr. Rao **non** è un fork di questi progetti: li usa come dipendenze.
Le loro licenze restano integre e **prevalgono** sui rispettivi file.
La [LICENSE](LICENSE) di Mr. Rao **non** limita i diritti sulle librerie sotto.

## Elenco principale

| Progetto | Uso in Mr. Rao | Licenza | Repository / sito | Notice locale |
|----------|----------------|---------|-------------------|---------------|
| [MarkItDown](https://github.com/microsoft/markitdown) | Documenti → Markdown | MIT | Microsoft | — |
| [RapidOCR](https://github.com/RapidAI/RapidOCR) | OCR offline | Apache-2.0 | RapidAI | — |
| [ONNX Runtime](https://onnxruntime.ai/) | Runtime modelli | MIT | Microsoft | — |
| [Flask](https://github.com/pallets/flask) | Server web locale | BSD-3-Clause | Pallets | — |
| [Werkzeug](https://github.com/pallets/werkzeug) | WSGI | BSD-3-Clause | Pallets | — |
| [Beautiful Soup](https://www.crummy.com/software/BeautifulSoup/) | HTML email → testo | MIT | crummy.com | — |
| [Scrubadub](https://github.com/LeapBeyond/scrubadub) | Redazione PII | MIT | LeapBeyond | — |
| [pdfplumber](https://github.com/jsvine/pdfplumber) | PDF / tabelle | MIT* | jsvine | — |
| [Pillow](https://github.com/python-pillow/Pillow) | Immagini | HPND / MIT-CMU | python-pillow | — |
| [Magika](https://github.com/google/magika) | Tipo file | Apache-2.0 | Google | — |
| **[pystray](https://github.com/moses-palmer/pystray)** | System tray | **LGPL-3.0** | Moses Palmér | [`licenses/pystray/`](licenses/pystray/) |

\* Verificare sempre i file LICENSE del pacchetto installato.

Altre dipendenze transitive: vedi `pip freeze` nell’ambiente virtuale.

---

## pystray — conformità LGPL-3.0 (completa)

**Copyright (C) 2016–2022 Moses Palmér**  
Licenza: GNU Lesser General Public License v3 (o successiva, a scelta).

Mr. Rao adempie agli obblighi LGPL così:

1. **Testi di licenza** in `licenses/pystray/` (`COPYING.LGPL`, `COPYING`, copie gnu.org).  
2. **NOTICE** in `licenses/pystray/NOTICE.txt`.  
3. **Sorgente** disponibile su GitHub e PyPI (link sopra).  
4. **Libreria sostituibile**: import Python standard; istruzioni in
   [`docs/LGPL_PYSTRAY.md`](docs/LGPL_PYSTRAY.md).  
5. **Nessuna restrizione aggiuntiva** su pystray da parte della licenza Mr. Rao.  
6. **UI e footer** informano l’utente (badge LGPL, link al repository).  
7. **Build portable**: la cartella `licenses/` viene copiata nel pacchetto.

Codice di integrazione: `mr_rao/tray.py` (avviso LGPL in testa al modulo).

---

## Attribuzione in redistribuzione

Conserva almeno:

- `LICENSE` (Mr. Rao)  
- `THIRD_PARTY.md`  
- `licenses/` (intera cartella)  

---

## Aggiornamento

Licenze rilevate da metadata PyPI e repository ufficiali; verificare upstream
prima di una distribuzione formale.
