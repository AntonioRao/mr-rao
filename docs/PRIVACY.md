# Privacy — Mr. Rao

## Principi

1. **Tutto locale** — nessun invio a servizi esterni
2. **Font di sistema** — nessuna richiesta a Google Fonts
3. **Cronologia** solo in memoria, mai su disco
4. **File temporanei** cancellati a conversione finita

## Come funziona il riconoscimento

Ogni riconoscitore è **un'espressione regolare più un validatore**: il
pattern propone un candidato, il validatore decide se è davvero un dato
personale. È quello che tiene bassi i falsi positivi senza rinunciare alla
copertura — un IBAN si accetta solo se il mod-97 torna, una carta solo se
passa il controllo di Luhn, un numero di dieci cifre è un telefono solo se
ha un prefisso, un separatore o una parola di contesto davanti.

**La decisione non passa da nessun modello.** Il motore è deterministico:
lo stesso testo dà sempre lo stesso risultato, non c'è un punteggio da
tarare né una soglia, e ogni sostituzione si può spiegare guardando la
regola che l'ha prodotta.

Reti neurali nel pacchetto però ce ne sono, e vanno dette invece che
sottintese. Due, entrambe **a monte** del motore:

| Modello | Peso | A cosa serve | Quando gira |
|---------|------|--------------|-------------|
| RapidOCR (PP-OCRv6, `.onnx`) | ~30 MB | Trasformare i pixel di una scansione in caratteri | Su immagini e PDF senza testo |
| magika, caricato da MarkItDown | ~3 MB | Indovinare il tipo di un file dal suo contenuto | Su ogni conversione |

Girano in locale, offline, sul processore: nessuno dei due esce dalla
macchina, e nessuno dei due dice se qualcosa è un dato personale. L'OCR
consegna del testo e si ferma lì; da quel punto in poi decidono espressioni
regolari e aritmetica — è il principio di casa, *il pattern propone, il
validatore decide*, e l'OCR sta a monte perfino del pattern.

Questo taglia in due la responsabilità, ed è utile saperlo in entrambi i
versi. Sul testo, il comportamento del motore è interamente ispezionabile.
Sulle scansioni, **quello che l'OCR legge male il motore non può decidere
bene**: un IBAN storpiato non arriva nemmeno al mod-97, e nessuna regola
recupera un dato che il lettore non ha letto. È il limite misurato più
avanti in questa pagina, non un'ipotesi.

## Cosa viene sostituito

| Tipo | Segnaposto | Come viene deciso |
|------|-----------|-------------------|
| Email | `{{EMAIL}}` | Forma dell'indirizzo, comprese quelle offuscate (`[at]`, `chiocciola`, `punto`) |
| Indirizzi web | `{{URL}}` | `http`, `https`, `www.` — solo questi |
| Telefoni | `{{PHONE}}` | Prefisso `+39`, cellulari `3xx`, parola di contesto (`cell`, `tel`, `fax`), oppure fisso con separatori |
| Codice fiscale | `{{CODICE_FISCALE}}` | Struttura a 16 caratteri. Il **carattere di controllo** non rifiuta, segnala |
| | | Recupera anche la forma storpiata dall'OCR, se il controllo del candidato corretto torna |
| P.IVA | `{{PARTITA_IVA}}` | Prefisso `IT` o contesto fiscale vicino. La **cifra di controllo** non rifiuta, segnala |
| IBAN | `{{IBAN}}` | **Mod-97** (ISO 13616), anche scritto a gruppi di quattro come lo stampano le banche |
| Coordinate non-IBAN | `{{BBAN}}` | CIN+ABI+CAB+conto, con contesto bancario vicino |
| Carte di pagamento | `{{CARD}}` | **Luhn** (ISO/IEC 7812) |
| Indirizzi | `{{ADDRESS}}` | Via, viale, piazza, corso, largo, contrada e altri, con civico, CAP e comune |
| Nomi di persona | `{{NAME}}` | Vedi sotto |
| Chiavi e password | `{{SECRET}}` | Token, chiavi API, JWT, blocchi di chiave privata, `password: ...` |
| Documenti d'identità | `{{DOC_ID}}` | Carta d'identità elettronica, patente, passaporto. **Serve il tipo di documento scritto vicino**, vedi sotto |
| Date di nascita | `{{DATE}}` | **Spento di default.** Solo con contesto di nascita accanto |
| Importi | `{{AMOUNT}}` | **Spento di default.** Valuta, migliaia o contesto contabile |
| Termini tuoi | `{{TERM}}` | L'elenco «nascondi sempre» scritto da chi converte |

### Il pacchetto anglosassone

Arrivato con la 1.8.0 e rimasto fuori da questa tabella fino alla 1.11 — un
buco che oggi non può ripetersi, perché `scripts/check_docs.py` confronta i
segnaposto che il motore sa emettere con quelli scritti qui e **fallisce** se
ne trova uno solo di troppo.

| Tipo | Segnaposto | Come viene deciso |
|------|-----------|-------------------|
| NHS number (UK) | `{{NHS_NUMBER}}` | **Mod-11**. È un conto vero: una cifra sbagliata non passa |
| Routing bancario ABA (US) | `{{ROUTING_NUMBER}}` | Checksum pesato **3-7-1** *più* gli intervalli di prefisso in uso |
| ABN (AU) | `{{ABN}}` | **Mod-89**, con la sottrazione di 1 alla prima cifra |
| TFN (AU) | `{{TFN}}` | **Mod-11** pesato |
| SIN (CA) | `{{SIN}}` | **Luhn** |
| Zona a lettura ottica dei passaporti | `{{MRZ}}` | Cifra di controllo **ICAO 9303** — documento, nascita, scadenza e composita |
| National Insurance number (UK) | `{{NINO}}` | **Nessun checksum**: struttura, più i prefissi che l'HMRC non assegna |
| SSN (US) | `{{SSN}}` | **Nessun checksum**: struttura, più le esclusioni pubblicate dalla SSA |
| ITIN (US) | `{{ITIN}}` | **Nessun checksum**: struttura e intervalli IRS |
| Codice postale britannico | `{{POSTCODE}}` | **Nessun checksum**, come ogni codice postale: solo la struttura |

La divisione fra le due metà è la cosa da leggere. Dove c'è un conto, il
riconoscitore **dimostra**; dove non c'è, può solo escludere ciò che è
palesemente impossibile — e su quei quattro il rischio di prendere un codice
qualsiasi resta più alto. È la stessa ragione per cui i documenti d'identità
italiani pretendono il contesto.

### Perché i documenti d'identità pretendono il contesto

È l'unico riconoscitore che non può appoggiarsi a un conto, e conviene dirlo
apertamente. Un numero di patente **non ha una cifra di controllo**: nessuna
aritmetica può distinguere `MI5512340V` da un codice di protocollo con la
stessa forma. Le tre alternative erano tutte cattive tranne una:

- sostituire a vista cancellerebbe mezza pratica amministrativa — un verbale
  è fatto di protocolli, delibere e codici gara che hanno quella forma;
- tacere lascerebbe passare uno dei dati più sensibili che attraversano uno
  studio;
- **chiedere che il testo dichiari di che documento si tratta**, e quando non
  lo dichiara segnalare invece di agire.

La finestra di contesto è larga di proposito. Su una tessera o una scansione
il tipo di documento non sta accanto al numero: **è il titolo**, diverse righe
sopra. Con una finestra stretta il riconoscitore non vedeva la sola cosa che
lo autorizza a intervenire, e restava fermo proprio sui documenti per cui è
stato scritto.

Ha un interruttore suo, `documenti`, e non sta dentro `fiscal`: un numero di
documento non è un dato tributario, e chi spegne i codici fiscali non intende
scoprire il passaporto.

Su oltre cento documenti a verità zero il costo misurato è **zero**: nessuna
sostituzione sbagliata, nessun sospetto in più.

## I nomi di persona: quattro segnali

Un elenco di nomi non è mai completo, e affidarsi solo a quello lascia
passare tutti i cognomi non comuni. Valgono quindi anche le regole di
contesto, dal segnale più forte al più debole:

1. **Titolo professionale davanti** — Dott., Ing., Geom., Avv., Sig.
2. **Nome accanto a un indirizzo di posta** — `Tizio Caio <t.caio@x.it>`.
   È il caso più frequente nelle email.
3. **Nome proprio riconosciuto** che tira dentro la parola successiva.
4. **Euristica del cognome** — due parole maiuscole di fila che non sono
   parole italiane sono quasi sempre nome e cognome.

La quarta è l'unica che può sbagliare, ed è l'unica che si può spegnere da
sola: casella **«Deduci i cognomi sconosciuti»**, campo
`privacy_name_guess`, opzione `--no-name-guess`. **È spenta di default in
tutti i profili** dalla 1.7.2, e il motivo è un numero: su venti moduli
dell'Agenzia delle Entrate in bianco — documenti che non contengono un solo
dato personale — produceva 8 904 sostituzioni sbagliate. Chi la accende lo
fa sapendo cosa compra.

Due controlli la tengono a bada: un elenco di parole italiane che capita di
trovare con l'iniziale maiuscola (mesi, saluti, enti, città, termini
amministrativi) e un controllo sulle terminazioni — «Industriale» e
«Tecnico» finiscono come finiscono le parole, non come finiscono i cognomi.

## Come è verificato

Il banco di prova sono **due** testi, non uno:

- una **mail italiana** con nomi, indirizzi, recapiti, URL, IBAN, P.IVA,
  codice fiscale e importo: deve sparire tutto;
- un **verbale amministrativo** pieno di «Comitato Tecnico», «Piano
  Industriale», «Fase Uno», numeri di protocollo, date e codici gara:
  **non deve sparire niente**.

Il secondo conta quanto il primo. Un filtro che redige tutto è inutile
esattamente come uno che non redige niente, e il verbale è quello che
impedisce di guadagnare copertura peggiorando lo strumento.

## I sospetti

I riconoscitori cercano forme **valide**. L'OCR produce forme **quasi**
valide: `A01` letto `AD1`, `IT60` letto `lT60`. La struttura non torna, il
dato resta nel testo — e resta leggibile da una persona.

Sostituire senza certezza vorrebbe dire redigere mezzo documento. Ma
tacere è peggio: «3 redazioni» su un documento pulito e «3 redazioni» su
un documento che il riconoscitore non ha saputo leggere sono lo stesso
numero e due situazioni opposte.

Per questo, dopo la sostituzione, un passaggio sul testo rimasto segnala
ciò che somiglia a un dato personale senza esserlo abbastanza da poterlo
togliere. Compaiono nel rapporto come `suspects`, e nell'interfaccia
accanto al conteggio: **«🛡️ 3 redazioni · ⚠️ 2 da controllare»**.

I campioni sono mascherati (`RS••••••••••••2S`): quanto basta a
ritrovarli nel documento, non a leggerli.

Un documento amministrativo pulito — protocolli, delibere, codici gara,
date — produce **zero** sospetti. Se ogni numero diventasse un avviso,
l'avviso non varrebbe più niente.

## Il recupero dei codici storpiati

I sospetti dicono dove guardare. Per i codici che hanno una cifra di
controllo si può fare di meglio: **provare a correggerli**.

Il motore prende il candidato, applica le confusioni tipiche del
riconoscimento ottico — `O`↔`0`, `I`↔`1`, `S`↔`5`, `B`↔`8`, e soprattutto
la elle minuscola letta al posto della i maiuscola — per **al massimo due
caratteri**, e sostituisce solo se il checksum del candidato corretto
torna.

Non decide un'euristica: decide l'aritmetica.

```
RSSMRA85T1OA562S    →  {{CODICE_FISCALE}}   1 correzione, controllo OK
lT60X05428…123456   →  {{IBAN}}             1 correzione, mod-97 OK
lT60X05428…123457   →  invariato            nessuna correzione lo salva
```

**Il checksum da solo non basta**, ed è una lezione pagata: la prima
versione trasformava il numero d'ordine `5551234567890123` in
`SS51234567890123`, e quel candidato il mod-97 lo supera davvero. Se puoi
convertire qualunque sequenza di cifre in un IBAN, prima o poi ne azzecchi
uno. Serve anche restringere lo spazio dei candidati: almeno una delle due
iniziali dev'essere già una lettera.

## Report

La risposta API include `redaction: { total, counts }`, l'interfaccia mostra
il totale e la scheda **«Confronto privacy»** mostra il testo prima e dopo.
Quella scheda è il controllo che conta: è lì che si vede cosa è stato tolto
e, soprattutto, cosa è sfuggito.

## Limiti dichiarati

- **Nessun elenco di cognomi è completo.** L'euristica copre molto ma non
  tutto, e un cognome che assomiglia a una parola italiana può restare.
- **Sulle scansioni la protezione è più debole, e adesso c'è il numero.**
  `scripts/bench_scansioni.py` stampa 8 documenti con dati personali inventati
  — le cifre di controllo le calcola lui, con un'implementazione indipendente
  da quella del motore e verificata sui vettori pubblicati ISO 13616 e Luhn —
  li fa passare per uno scanner simulato, poi per l'OCR e l'anonimizzatore
  veri. Su 64 dati attesi per livello:

  | scansione | redatti | segnalati | **persi in silenzio** | non letti dall'OCR |
  |---|---|---|---|---|
  | testo, senza OCR | 100% | 0% | 0% | 0% |
  | scanner in ordine, 300 / 200 / 150 / 100 DPI | 94–100% | 0% | 0–6% | 0–3% |
  | fotocopia sbiadita, 300 DPI | 94% | 2% | 3% | 2% |
  | fotocopia sbiadita, 200 DPI | 47% | 6% | **38%** | 9% |
  | fotocopia sbiadita, 150 DPI | 6% | 2% | **25%** | 67% |

  **Non è la risoluzione.** Fra 300 e 100 DPI, su una scansione pulita, la
  copertura non peggiora: le differenze sono rumore. Quello che conta è la
  qualità del segno — una fotocopia sbiadita a 200 DPI perde più della metà
  dei dati, e quel documento a occhio si legge benissimo.

  **E la perdita è quasi sempre silenziosa.** Questa riga diceva che «quello
  che resta viene segnalato»: la misura dice di no. Dei dati rimasti leggibili
  nel Markdown i sospetti ne intercettano una minoranza — 0 su 4 sulle
  scansioni pulite, 4 su 28 sulla fotocopia a 200 DPI. La scheda **«Confronto
  privacy»** resta l'unico controllo che vede tutto.

  **Una causa di quelle perdite è stata tolta.** Dove il degrado è forte
  l'OCR **incolla il dato all'etichetta che lo precede** — `IBANIT60X05…`,
  `Tel.02 1234567`, un numero di carta attaccato ai puntini di guida di un
  modulo — e i riconoscitori, che pretendevano uno stacco davanti al
  candidato, non arrivavano nemmeno a proporlo. Il dato passava il proprio
  controllo aritmetico ed è rimasto in chiaro lo stesso: erano le stesse
  cifre di prima, solo attaccate alla parola davanti.

  Ora una parola incollata davanti è ammessa, e per il telefono — che non ha
  un'aritmetica capace di smentire la forma — è ammessa **solo** la parola di
  contatto prima del punto. Il resto non è cambiato: una **cifra** davanti
  continua a fermare tutto, perché vorrebbe dire ritagliare un pezzo da un
  numero più lungo. A decidere resta il mod-97, il Luhn, il carattere di
  controllo: il pattern propone, il validatore decide.

  **Il conto:** i dati persi in silenzio passano da 60 a 46 su 640 (−23%),
  le scansioni da scanner in ordine non ne perdono più nessuno. Il costo
  misurato prima di crederci: su 203 documenti scansionati veri i pattern
  allentati non propongono **nemmeno un candidato**, su 434 000 caratteri di
  testo reale ne propongono 4 e nessuno supera il validatore, e su un
  documento amministrativo costruito apposta per farli scattare ne propongono
  12 — sostituzioni sbagliate: zero.

  **I falsi positivi non peggiorano:** sui documenti di controllo a verità
  zero le sostituzioni sbagliate restano **zero a ogni livello di degrado**,
  anche quando l'OCR restituisce spazzatura.

  Un avvertimento sul banco stesso: **la carta è simulata, non vera.** Misura
  l'OCR e l'anonimizzatore su immagini degradate in modo controllato e
  ripetibile; non sostituisce un corpus di scansioni fatte davvero.
- **Un OCR troncato produce un'anonimizzazione parziale.** Se una scansione supera
  il tetto di tempo (`MR_RAO_OCR_TIMEOUT`, 15 minuti di default), l'estrazione si
  ferma e il motore ha visto solo le pagine lette. Il documento lo dichiara in
  cima, prima del testo: chi legge deve saperlo *prima* di fidarsi.
- **Sui nomi resta la parte difficile.** Il banco non è più sintetico: dalla
  1.8.0 sono oltre cento documenti amministrativi pubblici presi dal web, scansioni comprese, dove la
  risposta attesa è **zero** — quindi ogni sostituzione è un errore per
  costruzione — più 7 500 messaggi di mailing list. I falsi positivi sui nomi
  sono scesi da 6 339 a 1 637: **misurati, non stimati**. Ma 1 637 non è zero,
  e un cognome raro in un contesto ambiguo può ancora restare, o sparire a
  sproposito. L'euristica più aggressiva è spenta di default proprio per
  questo.
- **I formati coperti sono italiani e anglosassoni.** Codice fiscale, partita
  IVA, IBAN e BBAN italiani; NHS number, National Insurance number, SSN, ITIN,
  routing ABA, SIN canadese, ABN e TFN australiani, codice postale britannico,
  righe MRZ dei passaporti. Un numero di telefono tedesco o un NIF spagnolo
  **non** hanno un riconoscitore dedicato: su quei documenti il filtro vede
  meno di quanto sembri.
- **Non sostituisce una valutazione DPIA o un parere legale.**

## Domande da reviewer

Undici domande tipiche di chi clona il repository e ispeziona il motore
(anche con l’aiuto di un’AI), con risposte allineate al codice:

**→ [PRIVACY_FAQ.md](PRIVACY_FAQ.md)**
