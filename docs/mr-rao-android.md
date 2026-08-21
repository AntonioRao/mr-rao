# Mr. Rao su Android — note per la sessione che la costruisce

Documento di passaggio, scritto dopo una sessione di ricognizione (non di
implementazione). Nessuna riga di codice Android esiste ancora. Contiene le
verifiche fatte sul disco di questa macchina, non supposizioni — dove serve
sono indicati i comandi/file con cui ricontrollare.

Repo coinvolti:
- `C:\Users\anton\mr-rao` — app desktop Flask, pubblica, AGPL-3.0-or-later
- `C:\Users\anton\mr-rao-plus` — estensione browser, privata, commerciale

> **Secondo giro di verifica — 20 agosto 2026.** Le affermazioni tecniche di
> §1, §2 e §3 sono state ricontrollate una per una sul disco e **tornano
> tutte** (dettaglio in coda a ciascuna sezione). Sono state aggiunte due
> cose che mancavano e che cambiano il piano: la **§0**, che guarda cosa
> esiste già su Android — la prima stesura non lo aveva chiesto a nessuno — e
> una correzione in **§4**, dove la frase «su Android le estensioni browser
> non esistono» era falsa. Chi riprende il lavoro legga la §0 prima di tutto
> il resto: decide se questo progetto va fatto, non come.

---

## 0. Cosa esiste già su Android (verifica di mercato)

Fatta via ricerca web il 20 agosto 2026. È la verifica che la prima stesura
non aveva fatto, ed è quella che riordina le priorità.

### Il convertitore: la nicchia è annunciata, non occupata

Su Google Play, **oggi**, chi vuole trasformare un documento in Markdown
trova quasi solo il verso opposto — decine di app *Markdown → PDF*. Nella
direzione che interessa a noi:

| | Cosa fa | Dove gira |
|---|---|---|
| **[FreeConvert](https://play.google.com/store/apps/details?id=com.gachistudio.freeconvert&hl=en_US)** | documento → Markdown, fra molti formati | **nel cloud**: i file si caricano sui loro server |
| **[Open Markdown](https://openmarkdown.app/)** | 12+ formati → Markdown, OCR on-device 5 alfabeti | on-device, ma **«coming soon to google play»**: non è ancora scaricabile |

Due conseguenze, e vanno lette insieme.

**Lo spazio c'è davvero.** L'unica cosa installabile oggi che converta un
documento in Markdown lo fa **caricandolo su un server di terzi** — cioè
esattamente ciò che Mr. Rao esiste per evitare. E il caso d'uso tipico è
convertire un documento *per incollarlo in una chat AI*, quindi spesso un
documento riservato. Una app che fa la stessa cosa senza che il file esca dal
telefono non è un «me too»: è l'opposto, sullo stesso bisogno.

**Ma la finestra ha una data di scadenza.** Open Markdown arriva con 12
formati e OCR in cinque alfabeti, cioè da dove la roadmap del §4 arriverebbe
al passo 4. Essere primi non protegge; protegge essere **diversi**, e la
differenza difendibile è una sola: on-device **e** anonimizzato. Nessuno dei
due la copre — Open Markdown è on-device ma non anonimizza niente,
FreeConvert non è nemmeno on-device.

### La redazione: nessuno la fa, su Android

Cercando strumenti che tolgano i dati personali prima di incollarli in una
chat AI, quello che si trova è:

- **estensioni Chrome** — PasteSecure, Redactifi, Caviard, ChatGPT Privacy
  Shield. **Su Android non funzionano**: Chrome per Android non supporta le
  estensioni.
- **un'app iOS** — CleanPII.
- **nessuna app Android nativa.**

### Conseguenza per il piano

Il §4 arrivava alla conclusione giusta — l'app è un redattore — ma per la
ragione debole («nessuno converte un PDF di 40 pagine dal cellulare»). Le
ragioni forti sono due, e nessuna delle due era nella prima stesura:

1. **La redazione su Android è terra di nessuno**, mentre su desktop è
   affollata. È il nostro mercato, ed è vuoto.
2. **La conversione non è un ripiego**: oggi l'unica alternativa installabile
   manda i file a un server. Non è un mercato pieno da cui stare alla larga,
   è un mercato scoperto con un concorrente serio in arrivo.

Quindi la conversione **entra nella v1**, non come motivo per esistere ma
come la metà visibile del prodotto: si converte e si anonimizza nello stesso
gesto, che è la cosa che nessuno dei due concorrenti fa.

---

## 1. Perché non è un porting del desktop

Prima ipotesi (scartata): impacchettare il motore Python di `mr-rao` con
Chaquopy (Python embedded in APK) e costruire sopra una UI Kotlin.

Il motore di anonimizzazione vero e proprio è portabile senza problemi:
`mr_rao/privacy.py` (4868 righe) e `mr_rao/it_names.py` usano solo
`re`, `dataclasses`, `typing` — stdlib pura, zero dipendenze native.

Ma la pipeline di **conversione documenti** (`mr_rao/converter.py`) non lo è,
e il motivo non è ovvio finché non si guardano le dipendenze transitive:

```
markitdown  → Requires-Dist: magika~=0.6.1        (hard dependency, non un extra)
magika      → Requires-Dist: onnxruntime>=1.17.0
pdfplumber  → Requires-Dist: pypdfium2>=5.9.0
```

`onnxruntime` e `pypdfium2` non sono nel repo di pacchetti nativi di
Chaquopy (verificato su `https://chaquo.com/pypi-13.1/`: ci sono lxml,
pandas, numpy, Pillow, cryptography, cffi — non onnxruntime, non pikepdf,
non pypdfium2). Quindi non è solo l'OCR (`rapidocr`+`onnxruntime`,
dichiaratamente pesante) a restare fuori: **markitdown non si installa
proprio**, e siccome `converter.py` lo usa per rilevare il tipo di ogni
file in ingresso, salta l'estrazione testo per tutti i formati, non solo
i PDF scansionati.

Anche `python-docx` e `python-pptx`, che sembravano innocui, dipendono da
`lxml` — un'estensione C. Funzionano su Chaquopy solo perché Chaquopy
distribuisce una build precompilata di lxml per Android; non erano "pure
Python" come si era detto in una prima stesura di questo ragionamento.

**Conclusione**: portare il desktop così com'è vorrebbe dire riscrivere
`converter.py` da zero attorno a librerie compatibili Android, non
semplicemente ricompilare. Non impossibile, ma è un progetto diverso da
"fare un'APK di Mr. Rao".

---

## 2. La scoperta che cambia il piano: il motore esiste già in TypeScript

`C:\Users\anton\mr-rao-plus\src\motore\` contiene una riscrittura completa
del motore di riconoscimento/sostituzione in TypeScript — 8266 righe su **19**
file (`motore.ts`, `nomi.ts`, `nomi_sostituzione.ts`, `sostituzioni.ts`,
`sostituzioni_2.ts`, `sostituzioni_3.ts`, `validatori.ts`, `vocabolari.ts`,
`schemi.ts`, `schemi_contestuali.ts`, `quasi_identificatori.ts`, `termini.ts`,
`unicode.ts`, `rapporto.ts`, `opzioni.ts`, `atti.ts`, `formati_en.ts`,
`nomi_en_extra.ts`, `nomi_minuscoli.ts`), scritta per l'estensione browser.
La prima stesura ne contava 18: mancava `nomi_sostituzione.ts`. Il totale di
righe era invece esatto.

Verificato con grep su tutti i file di `src/motore/`:
- nessun `import`/`require` esterno al motore stesso (tutti relativi `./`)
- nessun uso di `document`, `window`, `chrome.*`, `fs` — è calcolo puro
- l'unica dipendenza dell'intero pacchetto (`package.json`) è `fflate`, e
  serve solo al modulo di estrazione allegati, non al motore

C'è anche un corpus di conformità congelato da rispettare in caso di
riscrittura/porting: `corpus/casi.jsonl` + `corpus/atteso.json`.

**Implicazione**: per Android non serve Chaquopy, non serve portare Python.
Il motore gira così com'è in qualunque runtime JavaScript — WebView,
React Native (Hermes), Capacitor. Zero riscrittura del cuore del prodotto.

Nota tecnica sul perché *non* conviene comunque riscriverlo in Kotlin da
zero: `re` di Python e le regex di Java/Kotlin divergono su lookbehind,
gruppi con nome e proprietà Unicode. Con un corpus di test congelato alle
spalle, ripartire da un motore TS già validato evita una nuova campagna di
validazione da zero.

---

## 3. Conversione documenti lato Android: cosa c'è, cosa manca

`mr-rao-plus` ha già un modulo di estrazione testo da formati composti:
`src/estensione/allegati_formati.ts` (243 righe, unica dipendenza
`fflate`) — legge **PDF, DOCX, XLSX, PPTX, ODT** senza pdf.js e senza rete.

Ma è stato scritto per un altro scopo, e la differenza conta:

> È un **rilevatore**, non un **convertitore**. Decide se un allegato
> contiene dati personali; se non riesce a leggerlo bene restituisce
> `null` = "illeggibile", e il chiamante blocca l'invio. Per un
> convertitore `null` non è un esito accettabile, serve comunque il
> miglior testo possibile.

Limiti concreti, verificati leggendo il file:

- **Output è testo piatto**, non Markdown. `testoDaXmlOffice()` fa
  `.replace(/<[^>]+>/g, " ")` — toglie tutti i tag XML indiscriminatamente.
  Titoli, liste, tabelle finiscono tutti sullo stesso piano.
- **XLSX è il caso peggiore**: `testoDaXlsx()` concatena
  `xl/sharedStrings.xml` e poi ogni `xl/worksheets/sheetN.xml` come testo
  libero. Le celle perdono riga e colonna — per un foglio di calcolo il
  risultato è inservibile così com'è.
- **PDF**: `testoDaPdf()` gestisce solo stream `FlateDecode` (o non
  compressi), niente CMap/font subset (caratteri sbagliati su PDF con
  font sottoinsieme), nessuna informazione di posizione (tabelle e colonne
  si mescolano), e negli operatori `TJ` i valori di kerning vengono
  scartati — le parole tendono ad attaccarsi.
- Nessun OCR, dichiarato esplicitamente nel commento di testa del file.

**Ma la struttura da cui ricostruire un Markdown vero c'è già nell'XML,
il codice attuale la butta via**, non manca dai sorgenti:
- DOCX: `w:pStyle` → livello titolo, `w:tbl` → tabella, `w:numPr` → liste
- XLSX: attributo `r="A1"` su ogni cella → riga/colonna per ricostruire
  la griglia invece di un flusso di testo

Sono conversioni deterministiche, verificabili con lo stesso approccio a
corpus congelato già in uso nel progetto. Ordine di grandezza: 200-300
righe aggiuntive per formato (DOCX, XLSX, PPTX, ODT), non riscritture.

Il PDF è il caso a parte. Lì la scelta giusta è diversa da quella fatta
per l'estensione browser: **pdf.js**. Nell'estensione era stato escluso
per peso del pacchetto e per il worker — vincoli che un'APK non ha allo
stesso modo. pdf.js risolve font/encoding/posizione che il parser
manuale attuale non tenta di risolvere.

> **Verifica del 20 agosto 2026 — l'obiezione sul peso non regge più.**
> `allegati_formati.ts` dichiara in testa di scartare pdf.js «(peso e
> worker)». Misurato su un concorrente che lo spedisce davvero: l'estensione
> **PasteSecure** impacchetta `pdf.js` (410 KB + 1,4 MB di worker),
> `SheetJS` per XLSX e `mammoth` per DOCX, e l'estensione **intera** pesa
> **1,7 MB**.
>
> Questo **non** cambia la scelta fatta per `mr-rao-plus`: là il modulo è un
> *rilevatore*, gli basta abbastanza testo per rispondere sì/no, e se non ce
> la fa il terzo esito («illeggibile» → invio bloccato) è la risposta giusta.
> Pagare 1,8 MB per migliorare un sì/no sarebbe peso speso male.
>
> Cambia il ragionamento **qui**: per un convertitore, dove l'uscita è ciò
> che l'utente legge, `null` non è una risposta e le parole attaccate
> nemmeno. Il costo di pdf.js è ora un numero misurato invece di una
> preoccupazione, e su un'APK è trascurabile.

Per l'OCR su Android, la scelta naturale non è né `rapidocr` (esclude per
via di onnxruntime, vedi §1) né `tesseract.js`: è **ML Kit Text
Recognition** di Google — nativo, on-device, offline, gratuito, e più
accurato di quello attualmente usato dal desktop.

---

## 4. Forma dell'app: non un clone del desktop

Lo strato che si rompe nel porting (conversione documenti pesanti) è
anche quello che sul telefono serve meno spesso: nessuno converte un PDF
di 40 pagine dal cellulare come attività primaria.

Il buco vero su Android è un altro: **mr-rao-plus è un'estensione
browser**, e il mobile è scoperto per *quel* prodotto, non (solo) per il
convertitore.

> **Correzione del 20 agosto 2026.** La prima stesura scriveva qui «su
> Android le estensioni browser non esistono». È **falso**: non esistono su
> Chrome per Android, ma **Firefox per Android le supporta**, e di
> `mr-rao-plus` esiste già una build Firefox pubblicata su AMO.
>
> Nel manifest Firefox attuale (`dist-firefox/manifest.json`) c'è
> `browser_specific_settings.gecko` ma **manca `gecko_android`**, la chiave
> che rende l'estensione installabile sul telefono. Sono poche righe.
>
> Non è però una vittoria annunciata: la documentazione di Mozilla avverte
> che **MV3 su Firefox Android ha spigoli noti** e consiglia MV2. La nostra è
> MV3, anche se usa `background.scripts` e non un service worker — che è
> proprio il punto critico citato. Quindi: **mezza giornata di esperimento**
> (aggiungi la chiave, installi, provi su un telefono vero), non una riga di
> roadmap da dare per fatta.

### Perché l'app serve comunque, anche se Firefox funziona

Il canale Firefox copre una fetta sola: chi usa Firefox, **dentro il
browser**. Su un telefono l'AI però non si usa quasi mai nel browser — si usa
nelle **app native** di ChatGPT, Claude, Gemini, Copilot. Nessuna estensione,
su nessun browser, vedrà mai quello che si scrive lì dentro.

Ecco perché l'app nativa non è un'alternativa all'estensione ma la cosa che
copre il caso principale. Le strade praticabili, in ordine:

| Strada | Copre | Note |
|---|---|---|
| **Share-target** | ogni app, ogni browser | l'utente sceglie «Condividi → Mr. Rao». Nessun permesso speciale, nessun attrito con Play. **È il punto di partenza.** |
| **Tastiera (`InputMethodService`)** | tutto ciò che si digita, app native comprese | l'unica che intercetta *prima* dell'invio nell'app di ChatGPT. Ma una tastiera vede tutto quello che scrivi: stesso problema di percezione già affrontato sul desktop (`docs/SCORCIATOIA-APPUNTI.md`, «disinnesco della somiglianza con un keylogger»), qui amplificato. Va progettata con quel problema in testa dal primo giorno. |
| Servizio di accessibilità | tutto | Play lo consente solo con giustificazioni molto strette: strada da non prendere. |
| Sorveglianza degli appunti | — | da Android 10 l'accesso agli appunti in background è chiuso. Non praticabile. |

Proposta di forma per la prima versione: **share-target + eventuale
tastiera custom**, non un file manager con conversione batch.
- selezioni testo in qualunque app → "Condividi" → Mr. Rao → torna
  anonimizzato (copiato/pronto da incollare)
- variante più profonda: `InputMethodService` che filtra prima
  dell'invio, stesso principio di mr-rao-plus ma a livello di tastiera
  invece che di estensione

Il caso "converti un documento in Markdown per risparmiare token quando
lo incolli in una chat AI" (motivazione emersa in conversazione, valida:
il testo estratto pesa un ordine di grandezza meno del documento
originale, e soprattutto meno di mandarlo come immagine/allegato binario
a un'app che lo farebbe passare per OCR lato server) resta comunque
dentro allo share-target: si condivide il file invece del testo, l'app
lo converte e anonimizza, e il risultato è pronto da incollare.

### Roadmap proposta, in ordine di resa su fatica

0. **`gecko_android` nel manifest Firefox** — mezza giornata, indipendente da
   tutto il resto. Se regge, c'è già un prodotto mobile per gli utenti
   Firefox mentre l'app si costruisce.
1. Share-target + DOCX/ODT → Markdown strutturato + anonimizzazione
   (riuso quasi totale di `src/motore/` + `allegati_formati.ts` esteso)
2. PDF via pdf.js → Markdown
3. XLSX con griglia ricostruita (righe/colonne da `r="A1"`)
4. OCR per PDF/immagini scansionati via ML Kit
5. Tastiera, se e quando il problema di fiducia del §4 è risolto per iscritto

Sul punto lasciato aperto — se il PDF debba stare nel primo giro — la §0 dà
una risposta: **sì**. È il formato che arriva su WhatsApp e per posta, ed è
quello su cui si misura il confronto con un servizio cloud. Una v1 che
converte solo DOCX non regge il paragone con l'unica alternativa esistente,
per quanto quella carichi i file su un server.

---

## 5. Pubblicazione — Google Play Store

Verificato via ricerca web (agosto 2026), non da documentazione locale.

**Costo**: $25 USD **una tantum**, non un abbonamento — accesso a vita
alla Play Console.

**Commissioni**: zero su app gratuite. Solo su acquisti in-app/abbonamenti,
e qui il quadro è cambiato di recente per effetto della causa Epic v.
Google: dal 30 giugno 2026 (EEA, UK, US; altri mercati a scaglioni fino a
settembre 2027) le tariffe sono **10% sul primo milione di dollari annuo**,
poi 20% (nuove installazioni) o 25% (installazioni esistenti) sopra quella
soglia — non più il 30% storico. È anche permesso l'uso di un sistema di
pagamento proprio o rimandare l'utente al proprio sito per il checkout.

**Account personale vs organizzazione** — è il vero punto di attrito, non
i $25:

| | Personale | Organizzazione |
|---|---|---|
| Costo | $25 | $25 |
| Closed testing obbligatorio prima del rilascio pubblico | **sì — 12 tester, 14 giorni** | no |
| Documenti richiesti | verifica identità | verifica identità + **D-U-N-S number** |

I 12 tester devono essere 12 account Gmail distinti che tengono l'app
installata per 14 giorni consecutivi — è la parte che blocca più gente
in pratica. Con partita IVA/ditta individuale si può ottenere un D-U-N-S
gratuito da Dun & Bradstreet e aprire come organizzazione, saltando il
requisito dei tester.

**Flusso di pubblicazione**:
1. Account + $25 + verifica identità (+ D-U-N-S se organizzazione)
2. Build come **Android App Bundle (.aab)** — Play non accetta più APK
   per app nuove; la firma è gestita da Play App Signing
3. Scheda store: descrizione, screenshot, icona, URL privacy policy
4. **Data safety form** — dichiarazione di cosa l'app raccoglie. Per Mr.
   Rao è il punto più semplice e più forte insieme: nessuna raccolta,
   nessuna rete, tutto on-device — diventa un'etichetta visibile sulla
   scheda pubblica, non solo un modulo da compilare
5. Content rating (questionario)
6. Closed testing se account personale (vedi tabella sopra)
7. Review, giorni non ore, per il primo rilascio

**Cambiamento imminente da conoscere, riguarda anche un piano B "distribuisco
l'APK dal mio sito"**: Google sta introducendo la **verifica sviluppatore
anche per il sideload**, non solo per Play Store. Dal settembre 2026 in
Brasile, Indonesia, Singapore, Thailandia; **globale dal 2027**. Le app di
sviluppatori non verificati richiederanno un flusso con attesa di 24 ore o
ADB per essere installate su dispositivi Android certificati (quelli con
Play Protect e app Google preinstallate). Il sideload non sparisce, ma
smette di essere la scorciatoia immediata che è oggi.

---

## 6. Alternativa/aggiunta: F-Droid

Store alternativo per software libero, nessun rapporto con Google Play.

- **Non carichi un APK pronto**: dai il repo sorgente, F-Droid compila in
  ambiente controllato proprio e firma con la sua chiave — garanzia
  verificabile che il binario corrisponde al codice pubblico
- Richiede **licenza libera** (AGPL-3.0-or-later è nella lista accettata)
  e sorgente pubblico → adatto a **mr-rao** (pubblico, AGPL), **non** a
  mr-rao-plus (privato, commerciale)
- **Gratis**: zero fee, zero account developer, zero D-U-N-S, zero
  requisito tester
- Nessuna review soggettiva, solo controlli automatici su licenza/tracker
- Coerente col posizionamento del prodotto ("i dati non escono, offline",
  vedi `docs/PRIVACY.md`): niente Google Play Services richiesti, niente
  telemetria per costruzione dello store stesso
- Contro: pubblico più piccolo, aggiornamenti più lenti (la build parte
  quando il loro server ci arriva, non al push)

Non è alternativo a Play Store, è **aggiuntivo**: costo marginale zero,
un repo pubblico + un file di metadata YAML minimo.

---

## 7. Decisioni ancora aperte per chi riprende questo lavoro

- ~~PDF nel primo giro o nel secondo~~ — **chiusa dalla §0: nel primo giro**
- `gecko_android` regge davvero su Firefox Android con un manifest MV3? È la
  prima cosa da provare, e la risposta cambia l'urgenza di tutto il resto
- La tastiera si fa o no: è l'unica strada verso le app native di ChatGPT e
  Claude, ed è anche quella che chiede più fiducia all'utente. Decisione di
  prodotto, non tecnica
- Stack UI: WebView "nudo" sopra il motore TS, Capacitor, o React
  Native — non discusso in questa sessione, va scelto prima di scrivere
  codice
- Account Play Store personale (12 tester) o organizzazione (D-U-N-S) —
  dipende da se l'utente ha/vuole aprire partita IVA per questo
- Se pubblicare anche su F-Droid fin dalla v1 o solo dopo che l'app è
  stabile
- Se la versione Android va trattata come feature di **mr-rao** (AGPL,
  motivo per cui F-Droid è naturale) o se nasce come prodotto a parte —
  cambia la licenza e quindi le opzioni di distribuzione disponibili
