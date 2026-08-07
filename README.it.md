# Mr. Rao

**Trasforma PDF, Word, Excel, scansioni ed email in Markdown pulito — con i dati personali già rimossi.**
**Tutto sul tuo computer, senza mandare niente a nessuno.**

[![Scarica](https://img.shields.io/badge/⬇️%20scarica-Windows%20portable%20·%20150%20MB-2ea44f?style=for-the-badge)](https://github.com/AntonioRao/mr-rao/releases/latest/download/MrRao-Portable.zip)

[![CI](https://github.com/AntonioRao/mr-rao/actions/workflows/ci.yml/badge.svg)](https://github.com/AntonioRao/mr-rao/actions/workflows/ci.yml)
[![Versione](https://img.shields.io/badge/versione-1.7.0-3b82f6)](docs/CHANGELOG.md)
[![Test](https://img.shields.io/badge/test-384%20passati-10b981)](tests/)
[![Rete](https://img.shields.io/badge/rete-nessuna%20chiamata%20esterna-8b5cf6)](#come-fa-a-essere-davvero-locale)
[![Licenza](https://img.shields.io/badge/licenza-AGPL--3.0-f59e0b)](LICENSE)
[![Windows](https://img.shields.io/badge/Windows-portable%20senza%20Python-06b6d4)](docs/PORTABLE.md)

**🇮🇹 Italiano** · [🇬🇧 English](README.md)

### [⬇️ Scarica per Windows — nessun Python richiesto](https://github.com/AntonioRao/mr-rao/releases/latest/download/MrRao-Portable.zip)

*Estrai lo zip, doppio clic su `Installa Mr Rao.bat`. Fatto.*
<sub>Lo scaricamento parte subito. [Tutte le versioni e le note di rilascio](https://github.com/AntonioRao/mr-rao/releases) · [changelog](docs/CHANGELOG.md)</sub>

![Mr. Rao — interfaccia](docs/img/schermata.png)

> *Note for international visitors: Mr. Rao targets Italian documents — it recognises codice fiscale, partita IVA, IBAN and Italian names. The interface is in Italian; the code is documented in English.*

---

## Il problema

Vuoi dare un documento in pasto a un assistente AI. Ti servono due cose:

1. il testo, pulito, non un PDF;
2. **non** consegnare al fornitore il codice fiscale del tuo cliente.

Gli strumenti online risolvono il primo problema creando il secondo: per convertire il file glielo devi caricare. Se quel file è una fattura, una cartella clinica, un contratto o un thread email con dentro persone reali, l'hai appena spedito a un server di cui non sai nulla.

Mr. Rao fa la conversione **e** l'anonimizzazione dei dati personali sul tuo computer. Il file non si muove.

---

## Il motore di anonimizzazione

La conversione la fa [MarkItDown](https://github.com/microsoft/markitdown), che è di Microsoft ed è ottimo. **Questa è la parte che non trovi altrove.**

### Il numero deve dimostrare di essere un IBAN

Ogni riconoscitore è una coppia: un'espressione regolare che propone candidati, e un validatore che decide. Il pattern non basta mai.

| dato | come viene deciso |
|------|-------------------|
| IBAN | **mod-97** (ISO 13616) |
| Carta di pagamento | **Luhn** (ISO/IEC 7812) |
| Telefono | prefisso `+39`, prefisso cellulare `3xx`, separatori, o una parola di contesto davanti |
| P.IVA | prefisso `IT` o contesto fiscale nei caratteri precedenti |
| Indirizzo | dopo «via», «piazza», «corso» deve seguire una parola con l'iniziale maiuscola |
| Data di nascita | solo accanto a «nato il», «data di nascita» |

È il motivo per cui questo resta intatto:

```
Protocollo interno: 0123456789      →  invariato: nessun prefisso, nessun separatore
Registrata il 01.02.2024            →  invariato: è una data, non un recapito
Ordine 5551234567890123             →  invariato: non passa Luhn
```

E questo sparisce:

```
IBAN IT60X0542811101000000123456    →  {{IBAN}}
Carta 4111 1111 1111 1111           →  {{CARD}}
cell. 335 123 4567                  →  {{PHONE}}
```

### I nomi: quattro segnali, non un elenco

Nessun elenco di cognomi è completo. Per questo valgono anche le regole di contesto, dal segnale più forte al più debole:

1. **titolo professionale davanti** — Dott., Ing., Geom., Avv.;
2. **nome accanto a un indirizzo di posta** — `Tizio Caio <t.caio@x.it>`, il caso più frequente nelle email;
3. **nome proprio riconosciuto** che tira dentro la parola successiva: se «Nazzareno» è un nome, «Sbrolli» è il cognome anche se non compare in nessun elenco;
4. **euristica** — due parole maiuscole di fila che non sono parole italiane.

Solo la quarta può sbagliare, ed è l'unica che si può spegnere da sola.

### Il controllo che conta di più

Un filtro che redige tutto è inutile esattamente come uno che non redige niente. Il banco di prova sono **due** testi, e sono entrambi dei test:

| | sostituzioni attese | risultato |
|---|---|---|
| Una mail italiana con dieci categorie di dati personali | tutto | **29 sostituzioni, niente in chiaro** |
| Un verbale con «Comitato Tecnico», «Piano Industriale», «Fase Uno», protocolli e codici gara | niente | **0 sostituzioni** |

Due cose tengono in piedi il secondo: un vocabolario di parole italiane che capita di trovare maiuscole, e un controllo sulle terminazioni — «Industriale» e «Tecnico» finiscono come finiscono le parole, non come finiscono i cognomi.

### E quello che non riesce a togliere, lo dice

I riconoscitori cercano forme **valide**. Una scansione produce forme **quasi** valide: `A01` letto `AD1`, `IT60` letto `lT60`. La struttura non torna, il dato resta nel testo — e resta leggibile da una persona.

Sostituire senza certezza vorrebbe dire redigere mezzo documento. Ma tacere è peggio, perché **«3 redazioni» su un documento pulito e «3 redazioni» su un documento che il riconoscitore non ha saputo leggere sono lo stesso numero e due situazioni opposte.**

Per questo il risultato distingue le due cose:

```
🛡️ 3 redazioni · ⚠️ 2 da controllare
```

I sospetti sono mascherati — `RS••••••••••••2S` — quanto basta a ritrovarli nel documento, non a leggerli. E un verbale pieno di protocolli, delibere e codici gara ne produce **zero**: se ogni numero diventasse un avviso, l'avviso non varrebbe più niente.

### Nessun modello

Il riconoscimento è codice, non una rete neurale. Lo stesso documento dà **sempre** lo stesso risultato, e ogni sostituzione si spiega indicando la regola che l'ha prodotta. Niente da scaricare, niente da addestrare, niente che cambi comportamento fra due esecuzioni.

**→ [Come funziona nel dettaglio, con i limiti dichiarati](docs/PRIVACY.md)**

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

**[⬇️ Scarica l'ultima versione](https://github.com/AntonioRao/mr-rao/releases/latest/download/MrRao-Portable.zip)** — poi estrai lo zip e fai doppio clic su **`Installa Mr Rao.bat`**.

Non serve altro: Python, modelli OCR e dipendenze sono già dentro. Lo zip pesa ~150 MB, ~310 MB una volta installato.

L'installazione crea il collegamento sul desktop, la voce nel menu Start e il tasto destro «Apri con Mr. Rao» su qualunque file, con una voce dedicata per i dieci formati più frequenti. `Disinstalla Mr Rao.bat` toglie tutto — le tue cartelle di lavoro restano dove sono.

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
- **Il riconoscimento dei nomi non è infallibile.** Oltre a un elenco di nomi italiani valgono le regole di contesto — un titolo davanti, un indirizzo email accanto, due parole maiuscole che non sono parole italiane — ma un cognome che assomiglia a una parola comune può sfuggire. Per questo esiste la scheda «prima / dopo» — **controlla sempre** prima di condividere.
- **L'OCR non fa miracoli.** Su una scansione storta e sfocata sbaglia, come tutti.
- **Sui documenti scansionati la protezione è più debole.** I riconoscitori cercano un codice fiscale o un IBAN scritti bene: se l'OCR legge `A01` come `AD1`, il codice non viene riconosciuto e resta nel testo. Il risultato lo segnala con un avviso, ma è lì che il confronto «prima / dopo» va guardato davvero.
- **Non ha autenticazione.** È un tool locale per una persona, non un servizio multiutente.

---

## Come fa a essere davvero locale

Non è uno slogan, è verificabile:

- **Nel codice dell'app non c'è una sola chiamata di rete verso l'esterno.** L'unica `urlopen` presente punta a `127.0.0.1` e serve a capire chi occupa la porta. Controllabile in un comando: `grep -rn "urlopen\|requests\." mr_rao/`
- **I modelli OCR sono nel pacchetto.** Nessun download al primo avvio.
- **Le cartelle di lavoro non finiscono nel cloud.** Su Windows «Documenti» spesso *è* la cartella OneDrive: Mr. Rao se ne accorge e in quel caso usa una cartella locale, dicendoti perché — così uno strumento che promette che i file non escono dal computer non te li sincronizza in silenzio sul cloud aziendale.
- **Il server locale si difende.** Header `Host` in allow-list contro il DNS rebinding — anche quando scegli di esporlo in rete — e rifiuto delle richieste cross-site, con `Sec-Fetch-Site` prima e `Origin` come ripiego: una pagina aperta nel browser non può pilotare Mr. Rao, nemmeno se è servita da un altro programma sulla tua stessa macchina. [Il dettaglio, con i limiti](SECURITY.md).

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

Cinque passaggi: compilazione, verifica delle dipendenze, allineamento delle licenze, allineamento dei documenti pubblicati, **384 test**.

I test non coprono solo il caso felice. Coprono i difetti che sono costati caro: la matrice profilo × formato che ha scoperto l'OCR su PDF rotto, l'isolamento delle opzioni tra file dello stesso lotto, la porta occupata su Windows, la GET che scriveva su disco, le cartelle che finivano nel cloud. Ogni test di regressione è stato verificato **fallire sul codice di prima**: un test che non fallisce sul bug non dimostra niente.

---

## Documentazione

- [Architettura](docs/ARCHITECTURE.md) — com'è fatto dentro
- [Privacy](docs/PRIVACY.md) — cosa viene riconosciuto e come
- [FAQ privacy per reviewer](docs/PRIVACY_FAQ.md) — undici domande tipiche di chi ispeziona il motore
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
| `MR_RAO_OCR_TIMEOUT` | `900` | Secondi massimi per un OCR (`0` = nessun limite) |
| `MR_RAO_MAX_WORKERS` | `2` | Conversioni in parallelo; le altre restano in coda |
| `MR_RAO_FOLDER_ROOT` | automatico | Dove creare le cartelle di lavoro |
| `MR_RAO_ALLOWED_HOSTS` | gli indirizzi di questa macchina | Host ammessi nell'header `Host` |
| `MR_RAO_SECRET` | casuale a ogni avvio | Chiave di firma; oggi non la usa niente ([perché](SECURITY.md#chiave-di-firma)) |

---

*Mr. Rao — dal documento al Markdown. Offline.*
