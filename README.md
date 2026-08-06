# Mr. Rao

**Trasforma PDF, Word, Excel, scansioni ed email in Markdown pulito. Sul tuo computer, senza mandare niente a nessuno.**

[![Versione](https://img.shields.io/badge/versione-1.3.0-3b82f6)](docs/CHANGELOG.md)
[![Test](https://img.shields.io/badge/test-161%20passati-10b981)](tests/)
[![Rete](https://img.shields.io/badge/rete-nessuna%20chiamata%20esterna-8b5cf6)](#come-fa-a-essere-davvero-locale)
[![Licenza](https://img.shields.io/badge/licenza-uso%20non%20commerciale-f59e0b)](LICENSE)
[![Windows](https://img.shields.io/badge/Windows-portable%20senza%20Python-06b6d4)](docs/PORTABLE.md)

![Mr. Rao](static/img/logo.svg)

> *Note for international visitors: Mr. Rao targets Italian documents — it recognises codice fiscale, partita IVA, IBAN and Italian names. The interface is in Italian; the code is documented in English.*

---

## Il problema

Vuoi dare un documento in pasto a ChatGPT, Claude o un qualunque assistente. Ti servono due cose:

1. il testo, pulito, non un PDF;
2. **non** consegnare al fornitore il codice fiscale del tuo cliente.

Gli strumenti online risolvono il primo problema creando il secondo: per convertire il file glielo devi caricare. Se quel file è una fattura, una cartella clinica, un contratto o un thread email con dentro persone reali, l'hai appena spedito a un server di cui non sai nulla.

Mr. Rao fa la conversione **e** la schermatura dei dati personali sul tuo computer. Il file non si muove.

---

## Cosa fa

| | |
|---|---|
| 📄 **Documenti** | PDF, DOCX, DOC, XLSX, XLS, PPTX, PPT, HTML, CSV, JSON, XML, TXT, RTF |
| 👁️ **Scansioni e foto** | OCR offline su PNG, JPG, TIFF, WebP, BMP, GIF — e su PDF scansionati |
| 📊 **Tabelle PDF** | Ricostruite come tabelle Markdown, non sfilacciate in righe di testo |
| 📧 **Email** | File `.eml` col thread separato messaggio per messaggio, allegati scaricabili |
| 🛡️ **Dati personali** | Email, telefoni, codice fiscale, P.IVA, IBAN, nomi → sostituiti con segnaposto |
| 🔍 **Verifica** | Scheda «prima / dopo» che mostra esattamente cosa è stato tolto |
| 📁 **Cartella automatica** | Butti i file in una cartella, i `.md` compaiono nell'altra |
| ⌨️ **Riga di comando** | `convert`, `watch`, `health` — anche dall'eseguibile portable |

<!-- SCREENSHOT: inserire qui una schermata dell'interfaccia (area di rilascio + risultato
     col badge delle redazioni). Consigliato PNG largo ~1400 px in docs/img/schermata.png -->

---

## Come si usa

### Windows, senza installare Python

Scarica il pacchetto portable e fai doppio clic su `Avvia Mr Rao.bat`. Non serve altro: Python, modelli OCR e dipendenze sono già dentro (~390 MB).

### Con Python

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Si apre da solo su `http://127.0.0.1:5000`. Se quella porta è occupata te lo dice — indicando **chi** la occupa — e usa la prima libera.

### Da riga di comando

```bash
python -m mr_rao.cli convert fattura.pdf -o fattura.md
python -m mr_rao.cli convert cartella\*.pdf --merge -o tutto.md
python -m mr_rao.cli watch .\da-convertire .\convertiti --move-done
```

### Docker

```bash
docker compose up --build
```

Pubblicato **solo su localhost**: l'app non ha autenticazione, esporla in rete dev'essere una scelta consapevole (serve un reverse proxy con autenticazione davanti).

---

## Casi d'uso reali

**Studio legale — thread email da allegare a una pratica.**
Un `.eml` con venti risposte impilate diventa un Markdown leggibile, un messaggio per volta, con gli allegati estratti. Il profilo «Email legali» toglie nomi, indirizzi e recapiti: quello che resta si può girare a un consulente o a un assistente AI senza esporre le controparti.

**Commercialista — fatture e prima nota.**
Il profilo «Fatture» ricostruisce le tabelle e nasconde codice fiscale, P.IVA e IBAN **lasciando visibili gli importi**, che sono il motivo per cui stai leggendo il documento.

**Chi lavora con gli assistenti AI.**
Il profilo «Pronto per LLM» produce testo essenziale, senza intestazioni tecniche, coi dati personali già sostituiti. Copi e incolli senza pensarci due volte.

**Archivi cartacei digitalizzati.**
Cartella automatica più profilo «Solo OCR»: svuoti lo scanner dentro una cartella e ti ritrovi i Markdown nell'altra, senza restare davanti allo schermo.

**Chi deve dimostrare cosa ha fatto.**
Ogni file può portare in cima una scheda con origine, data, motore usato e **quante sostituzioni** sono state applicate. Utile quando la conversione va documentata.

---

## Cosa NON fa

Meglio dirlo subito:

- **Non è un traduttore di layout.** Produce testo strutturato, non un clone grafico del PDF.
- **La schermatura dei nomi non è infallibile.** Si basa su un elenco di nomi italiani comuni: un cognome raro può sfuggire. Per questo esiste la scheda «prima / dopo» — **controlla sempre** prima di condividere.
- **L'OCR non fa miracoli.** Su una scansione storta e sfocata sbaglia, come tutti.
- **Non ha autenticazione.** È un attrezzo locale per una persona, non un servizio multiutente.
- **La scelta della lingua OCR oggi non cambia il modello.** È già annotata nel [backlog](docs/BACKLOG.md) come cosa da implementare davvero o da togliere.

---

## Come fa a essere davvero locale

Non è uno slogan, è verificabile:

- **Nel codice dell'app non c'è una sola chiamata di rete verso l'esterno.** L'unica `urlopen` presente punta a `127.0.0.1` e serve a capire chi occupa la porta. Controllabile in un comando: `grep -rn "urlopen\|requests\." mr_rao/`
- **I modelli OCR sono nel pacchetto.** Nessun download al primo avvio.
- **Le cartelle di lavoro non finiscono nel cloud.** Su Windows «Documenti» spesso *è* la cartella OneDrive: Mr. Rao se ne accorge e in quel caso usa una cartella locale, dicendoti perché. Era un difetto vero, corretto nella [1.3.0](docs/CHANGELOG.md).
- **Il server locale si difende.** Header `Host` in allow-list (contro il DNS rebinding) e rifiuto delle richieste cross-site (contro la CSRF): una pagina aperta nel browser non può pilotare Mr. Rao.

---

## Trasparenza su cosa c'è dentro

Mr. Rao **non** è un fork di questi progetti: li usa come dipendenze, e le loro licenze restano intatte.

Il cuore della conversione è **[MarkItDown](https://github.com/microsoft/markitdown)** di Microsoft (MIT). L'OCR è **[RapidOCR](https://github.com/RapidAI/RapidOCR)** (Apache-2.0) su **[ONNX Runtime](https://onnxruntime.ai/)**. Il resto — Flask, BeautifulSoup, pdfplumber, Pillow, Scrubadub — è elencato per intero in **[THIRD_PARTY.md](THIRD_PARTY.md)**.

> *Mr. Rao non è affiliato né sponsorizzato da Microsoft o dagli altri progetti citati.*

Quell'elenco non è scritto a mano: lo **genera** [`scripts/gen_third_party.py`](scripts/gen_third_party.py) leggendo i metadati dei pacchetti realmente installati, e il quality gate fallisce se è disallineato. La versione compilata a mano aveva già sbagliato una licenza e ne aveva omessa un'altra con obblighi veri: da lì la scelta di automatizzarla.

Due librerie sono **LGPL** (pystray e python-stdnum): testi di licenza, notice e istruzioni per sostituirle sono in [`licenses/`](licenses/). La licenza di Mr. Rao non impone restrizioni aggiuntive su di esse.

---

## Licenza

**Uso personale, didattico, di ricerca e interno all'azienda: libero e gratuito.**
**Uso commerciale** (rivendita, SaaS, prodotto a pagamento che lo incorpora): serve autorizzazione scritta.

Testo completo in [LICENSE](LICENSE). È una licenza *source available*: **non** è una licenza open source approvata OSI, ed è giusto chiamarla col suo nome. Le dipendenze restano ciascuna sotto la propria licenza open source.

---

## Qualità

```bash
scripts\quality_gate.bat
```

Quattro passaggi: compilazione, verifica delle dipendenze, allineamento delle licenze, **161 test**.

I test non coprono solo il caso felice. Coprono i difetti che sono costati caro: la matrice profilo × formato che ha scoperto l'OCR su PDF rotto, l'isolamento delle opzioni tra file dello stesso lotto, la porta occupata su Windows, la GET che scriveva su disco, le cartelle che finivano nel cloud. Ogni test di regressione è stato verificato **fallire sul codice di prima**: un test che non fallisce sul bug non dimostra niente.

---

## Documentazione

- [Architettura](docs/ARCHITECTURE.md) — com'è fatto dentro
- [Privacy](docs/PRIVACY.md) — cosa viene riconosciuto e come
- [Changelog](docs/CHANGELOG.md) — cosa è cambiato e perché
- [Backlog](docs/BACKLOG.md) — cosa manca, in ordine di priorità
- [Portable](docs/PORTABLE.md) — come si costruisce il pacchetto Windows
- [Sicurezza](SECURITY.md) — come segnalare un problema

---

## Configurazione

| Variabile | Default | Significato |
|-----------|---------|-------------|
| `MR_RAO_PORT` | `5000` | Porta del server locale |
| `MR_RAO_MAX_UPLOAD_MB` | `50` | Limite per l'**intero invio**, non per singolo file |
| `MR_RAO_MAX_OCR_PAGES` | `50` | Massimo pagine OCR per PDF |
| `MR_RAO_MAX_WORKERS` | `2` | Conversioni in parallelo; le altre restano in coda |
| `MR_RAO_FOLDER_ROOT` | automatico | Dove creare le cartelle di lavoro |
| `MR_RAO_ALLOWED_HOSTS` | `127.0.0.1,localhost` | Host ammessi nell'header `Host` |

---

*Mr. Rao — dal documento al Markdown. Offline.*
