# Mr. Rao

**Trasforma PDF, Word, Excel, scansioni ed email in Markdown pulito — con i dati personali già rimossi.**
**Tutto sul tuo computer, senza mandare niente a nessuno.**

[![CI](https://github.com/AntonioRao/mr-rao/actions/workflows/ci.yml/badge.svg)](https://github.com/AntonioRao/mr-rao/actions/workflows/ci.yml)
[![Versione](https://img.shields.io/badge/versione-1.4.0-3b82f6)](docs/CHANGELOG.md)
[![Test](https://img.shields.io/badge/test-250%20passati-10b981)](tests/)
[![Rete](https://img.shields.io/badge/rete-nessuna%20chiamata%20esterna-8b5cf6)](#come-fa-a-essere-davvero-locale)
[![Licenza](https://img.shields.io/badge/licenza-AGPL--3.0-f59e0b)](LICENSE)
[![Windows](https://img.shields.io/badge/Windows-portable%20senza%20Python-06b6d4)](docs/PORTABLE.md)

**🇮🇹 Italiano** · [🇬🇧 English](README.md)

![Mr. Rao — interfaccia](docs/img/schermata.png)

> *Note for international visitors: Mr. Rao targets Italian documents — it recognises codice fiscale, partita IVA, IBAN and Italian names. The interface is in Italian; the code is documented in English.*

---

## Il problema

Vuoi dare un documento in pasto a un assistente AI. Ti servono due cose:

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
| 🛡️ **Dati personali** | Nomi, indirizzi, telefoni, email, URL, codice fiscale, P.IVA, IBAN, carte, chiavi API → sostituiti con segnaposto |
| 🔍 **Verifica** | Scheda «prima / dopo» che mostra esattamente cosa è stato tolto |
| 📁 **Cartella automatica** | Butti i file in una cartella, i `.md` compaiono nell'altra |
| ⌨️ **Riga di comando** | `convert`, `watch`, `health` — anche dall'eseguibile portable |



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
- **La schermatura dei nomi non è infallibile.** Oltre a un elenco di nomi italiani valgono le regole di contesto — un titolo davanti, un indirizzo email accanto, due parole maiuscole che non sono parole italiane — ma un cognome che assomiglia a una parola comune può sfuggire. Per questo esiste la scheda «prima / dopo» — **controlla sempre** prima di condividere.
- **L'OCR non fa miracoli.** Su una scansione storta e sfocata sbaglia, come tutti.
- **Sui documenti scansionati la protezione è più debole.** I riconoscitori cercano un codice fiscale o un IBAN scritti bene: se l'OCR legge `A01` come `AD1`, il codice non viene riconosciuto e resta nel testo. Il risultato lo segnala con un avviso, ma è lì che il confronto «prima / dopo» va guardato davvero.
- **Non ha autenticazione.** È un attrezzo locale per una persona, non un servizio multiutente.

---

## Come fa a essere davvero locale

Non è uno slogan, è verificabile:

- **Nel codice dell'app non c'è una sola chiamata di rete verso l'esterno.** L'unica `urlopen` presente punta a `127.0.0.1` e serve a capire chi occupa la porta. Controllabile in un comando: `grep -rn "urlopen\|requests\." mr_rao/`
- **I modelli OCR sono nel pacchetto.** Nessun download al primo avvio.
- **Le cartelle di lavoro non finiscono nel cloud.** Su Windows «Documenti» spesso *è* la cartella OneDrive: Mr. Rao se ne accorge e in quel caso usa una cartella locale, dicendoti perché — così uno strumento che promette che i file non escono dal computer non te li sincronizza in silenzio sul cloud aziendale.
- **Il server locale si difende.** Header `Host` in allow-list (contro il DNS rebinding) e rifiuto delle richieste cross-site (contro la CSRF): una pagina aperta nel browser non può pilotare Mr. Rao.

---

## Trasparenza su cosa c'è dentro

Mr. Rao **non** è un fork di questi progetti: li usa come dipendenze, e le loro licenze restano intatte.

Il cuore della conversione è **[MarkItDown](https://github.com/microsoft/markitdown)** di Microsoft (MIT). L'OCR è **[RapidOCR](https://github.com/RapidAI/RapidOCR)** (Apache-2.0) su **[ONNX Runtime](https://onnxruntime.ai/)**. Il resto — Flask, BeautifulSoup, pdfplumber, Pillow — è elencato per intero in **[THIRD_PARTY.md](THIRD_PARTY.md)**.

> *Mr. Rao non è affiliato né sponsorizzato da Microsoft o dagli altri progetti citati.*

Quell'elenco non è scritto a mano: lo **genera** [`scripts/gen_third_party.py`](scripts/gen_third_party.py) leggendo i metadati dei pacchetti realmente installati, e il quality gate fallisce se si discosta da quelli. Così non può invecchiare in silenzio.

Una sola libreria è **LGPL** (pystray, per l'icona nella barra di sistema): testo di licenza, notice e istruzioni per sostituirla sono in [`licenses/`](licenses/).

---

## Licenza

Copyright © 2026 Rao

Mr. Rao è **software libero** sotto **[GNU Affero General Public License v3.0](LICENSE)**.
Puoi usarlo, studiarlo, modificarlo e ridistribuirlo — anche in ambito professionale
e commerciale — alle condizioni della licenza.

**Senza alcun obbligo aggiuntivo puoi**: usarlo nel tuo studio o in azienda, anche
per lavoro retribuito; installarlo sui computer dei tuoi clienti; farci sopra
consulenza, formazione o assistenza a pagamento.

**L'articolo 13 scatta solo se fai due cose insieme**: *modifichi* Mr. Rao **e** lo
rendi utilizzabile da altri *attraverso una rete* (un servizio web, un portale
aziendale). In quel caso devi offrire il codice sorgente della **tua** versione agli
utenti di quel servizio — non all'autore. Che tu lo offra gratis o a pagamento non
cambia nulla: l'AGPL non guarda al prezzo.

È qui la differenza con la GPL normale, che quel caso non lo copre: chi mette un
software su un server non sta distribuendo copie, e senza l'articolo 13 potrebbe
tenersi le proprie modifiche. Per uno strumento che si regge sulla fiducia, quel
buco era da chiudere.

Questa è una sintesi in buona fede, non consulenza legale: il testo che vale è
[LICENSE](LICENSE).

Distribuito **senza alcuna garanzia**, nella speranza che sia utile.
Le dipendenze restano ciascuna sotto la propria licenza — vedi [THIRD_PARTY.md](THIRD_PARTY.md).

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
