# Componenti di terze parti — Mr. Rao

> Generato da `scripts/gen_third_party.py` leggendo i metadati dei pacchetti
> **realmente installati**. Non modificare a mano: rigenerare.

Mr. Rao **non** è un fork di questi progetti: li usa come dipendenze.
Le loro licenze restano integre e **prevalgono** sui rispettivi file.

Mr. Rao è distribuito sotto **[AGPL-3.0](LICENSE)**. Tutte le licenze qui
elencate sono compatibili con l'AGPL-3.0: permissive (MIT, BSD, Apache-2.0,
PSF), copyleft di file (MPL-2.0, esplicitamente compatibile) e LGPL, che
l'AGPL può incorporare. La licenza di Mr. Rao **non** limita i diritti che
queste librerie concedono.

Pacchetti nell'ambiente: **51** — di cui **4** con obblighi
oltre la semplice attribuzione (copyleft o eccezioni).

## Licenze con obblighi particolari

Queste impongono adempimenti concreti — testo di licenza, notice, o
condizioni sulla ridistribuzione — e non la semplice attribuzione.
Sono elencate per prime perché sono quelle da controllare.

| Progetto | Versione | Licenza | Notice locale |
|----------|----------|---------|---------------|
| [certifi](https://github.com/certifi/python-certifi) | 2026.7.22 | Mozilla Public License 2.0 (MPL 2.0) | — |
| [pyinstaller](https://pyinstaller.org) | 6.21.0 | GNU General Public License v2 (GPLv2) | — |
| [pyinstaller-hooks-contrib](https://github.com/pyinstaller/pyinstaller-hooks-contrib) | 2026.6 | Apache Software License; GNU General Public License v2 (GPLv2) | — |
| [pystray](https://github.com/moses-palmer/pystray) | 0.19.5 | GNU Lesser General Public License v3 (LGPLv3) | [`licenses/pystray/`](licenses/pystray/) |

**pystray** (LGPL-3.0) è l'unica libreria LGPL del pacchetto: testo di
licenza, NOTICE e istruzioni di sostituzione in `licenses/pystray/`.
Essendo Mr. Rao distribuito sotto AGPL-3.0 con il sorgente completo,
l'obbligo LGPL di consentirne la sostituzione è soddisfatto di conseguenza.

**PyInstaller** è GPLv2-or-later **con eccezione esplicita** che consente di
costruire e distribuire programmi non liberi: è ciò che rende lecito
distribuire `MrRao.exe`, il cui bootloader deriva da PyInstaller.
Serve solo per costruire il pacchetto portable, non a runtime.

**MPL-2.0** (certifi) è copyleft *per file*: obbliga a rendere
disponibile il sorgente dei soli file MPL eventualmente modificati.
Mr. Rao non li modifica.

## Dipendenze dirette

| Progetto | Versione | Uso in Mr. Rao | Licenza | Notice locale |
|----------|----------|----------------|---------|---------------|
| [beautifulsoup4](https://www.crummy.com/software/BeautifulSoup/bs4/download/) | 4.15.0 | Corpo HTML delle email → testo | MIT License | — |
| [Flask](https://flask.palletsprojects.com/page/changes/) | 3.1.3 | Server web locale | BSD-3-Clause | — |
| [magika](https://google.github.io/magika/) | 0.6.2 | Riconoscimento del tipo di file | Apache Software License | — |
| [markitdown](https://github.com/microsoft/markitdown#readme) | 0.1.7 | Documenti Office/HTML/PDF → Markdown | MIT | — |
| [onnxruntime](https://onnxruntime.ai) | 1.28.0 | Esecuzione dei modelli OCR | MIT License | — |
| [pdfminer.six](https://github.com/pdfminer/pdfminer.six) | 20260107 | Parsing PDF (usato da pdfplumber) | MIT | — |
| [pdfplumber](https://github.com/jsvine/pdfplumber) | 0.11.10 | Estrazione testo e tabelle da PDF | MIT License | — |
| [pillow](https://pillow.readthedocs.io/en/stable/releasenotes/index.html) | 12.3.0 | Immagini | MIT-CMU | — |
| [pyinstaller](https://pyinstaller.org) | 6.21.0 | Build del pacchetto portable (solo sviluppo) | GNU General Public License v2 (GPLv2) | — |
| [pystray](https://github.com/moses-palmer/pystray) | 0.19.5 | Icona nella barra di sistema | GNU Lesser General Public License v3 (LGPLv3) | [`licenses/pystray/`](licenses/pystray/) |
| [pytest](https://docs.pytest.org/en/stable/changelog.html) | 9.1.1 | Test (solo sviluppo) | MIT | — |
| [PyYAML](https://pyyaml.org/) | 6.0.3 | Verifica del frontmatter nei test | MIT License | — |
| [rapidocr-onnxruntime](https://github.com/RapidAI/RapidOCR) | 1.2.3 | OCR offline (immagini e PDF scansionati) | Apache-2.0 | — |
| [Werkzeug](https://werkzeug.palletsprojects.com/page/changes/) | 3.1.8 | Livello WSGI | BSD-3-Clause | — |

## Dipendenze indirette

Arrivano come dipendenze delle precedenti. Sono elencate per intero perché
l'obbligo di attribuzione è di chi distribuisce, non di chi riceve.

<details><summary>Elenco completo (37 pacchetti)</summary>

| Progetto | Versione | Licenza | Notice locale |
|----------|----------|---------|---------------|
| [altgraph](https://altgraph.readthedocs.io) | 0.17.5 | MIT License | — |
| [blinker](https://discord.gg/pallets) | 1.9.0 | MIT License | — |
| [certifi](https://github.com/certifi/python-certifi) | 2026.7.22 | Mozilla Public License 2.0 (MPL 2.0) | — |
| [cffi](https://cffi.readthedocs.io/) | 2.1.1 | MIT-0 | — |
| [charset-normalizer](https://github.com/jawah/charset_normalizer/blob/master/CHANGELOG.md) | 3.4.9 | MIT | — |
| [click](https://click.palletsprojects.com/page/changes/) | 8.4.2 | BSD-3-Clause | — |
| [colorama](https://github.com/tartley/colorama) | 0.4.6 | BSD License | — |
| [cryptography](https://cryptography.io/en/latest/changelog/) | 50.0.0 | Apache-2.0 OR BSD-3-Clause | — |
| [defusedxml](https://github.com/tiran/defusedxml) | 0.7.1 | Python Software Foundation License | — |
| [flatbuffers](https://google.github.io/flatbuffers/) | 25.12.19 | Apache Software License | — |
| [idna](https://github.com/kjd/idna/blob/master/HISTORY.md) | 3.18 | BSD-3-Clause | — |
| [iniconfig](https://github.com/pytest-dev/iniconfig) | 2.3.0 | MIT | — |
| [itsdangerous](https://itsdangerous.palletsprojects.com/changes/) | 2.2.0 | BSD License | — |
| [Jinja2](https://jinja.palletsprojects.com/changes/) | 3.1.6 | BSD License | — |
| [markdownify](http://github.com/matthewwithanm/python-markdownify) | 1.2.3 | MIT License | — |
| [MarkupSafe](https://palletsprojects.com/donate) | 3.0.3 | BSD-3-Clause | — |
| [numpy](https://numpy.org) | 2.5.1 | BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0 | — |
| [opencv-python](https://github.com/opencv/opencv-python) | 5.0.0.93 | Apache Software License | — |
| [packaging](https://packaging.pypa.io/) | 26.3 | Apache-2.0 OR BSD-2-Clause | — |
| [pefile](https://github.com/erocarrera/pefile) | 2024.8.26 | MIT | — |
| [pip](https://pip.pypa.io/en/stable/news/) | 26.2.1 | MIT | — |
| pluggy | 1.6.0 | MIT License | — |
| [protobuf](https://developers.google.com/protocol-buffers/) | 7.35.1 | 3-Clause BSD License | — |
| [pyclipper](https://github.com/fonttools/pyclipper) | 1.4.0 | OSI Approved; MIT License | — |
| [pycparser](https://github.com/eliben/pycparser) | 3.0 | BSD-3-Clause | — |
| [Pygments](https://pygments.org) | 2.20.0 | BSD-2-Clause | — |
| [pyinstaller-hooks-contrib](https://github.com/pyinstaller/pyinstaller-hooks-contrib) | 2026.6 | Apache Software License; GNU General Public License v2 (GPLv2) | — |
| [pypdfium2](https://github.com/pypdfium2-team/pypdfium2) | 5.12.1 | BSD-3-Clause, Apache-2.0, dependency licenses | — |
| [python-dotenv](https://github.com/theskumar/python-dotenv) | 1.2.2 | BSD-3-Clause | — |
| [pywin32-ctypes](https://github.com/enthought/pywin32-ctypes) | 0.2.3 | BSD-3-Clause | — |
| [requests](https://requests.readthedocs.io) | 2.34.2 | Apache Software License | — |
| [setuptools](https://github.com/pypa/setuptools) | 83.0.0 | MIT | — |
| [shapely](https://shapely.readthedocs.io/) | 2.1.2 | BSD License | — |
| [six](https://github.com/benjaminp/six) | 1.17.0 | MIT License | — |
| [soupsieve](https://github.com/facelessuser/soupsieve) | 2.9.1 | MIT | — |
| [typing_extensions](https://github.com/python/typing_extensions/issues) | 4.16.0 | PSF-2.0 | — |
| [urllib3](https://github.com/urllib3/urllib3/blob/main/CHANGES.rst) | 2.7.0 | MIT | — |

</details>

## In caso di redistribuzione

Conservare almeno:

- `LICENSE` (Mr. Rao)
- `THIRD_PARTY.md` (questo file)
- `licenses/` (intera cartella)

La build portable (`scripts/build_portable.bat`) li copia già nel pacchetto.

## Se non vuoi nemmeno la dipendenza LGPL

Disinstalla pystray: si perde solo l'icona nella barra di sistema, e
l'applicazione resta pienamente utilizzabile dal browser e da riga di
comando. Il riconoscimento dei dati personali non ne dipende.

