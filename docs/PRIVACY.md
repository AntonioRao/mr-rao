# Privacy — Mr. Rao

*This document in English: [PRIVACY.en.md](PRIVACY.en.md).*

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
| Telefoni | `{{PHONE}}` | Prefisso `+39`, cellulari `3xx`, parola di contesto (`cell`, `tel`, `fax`), oppure fisso con separatori. La **barra** (`011/7323929`) vale solo con la parola di contatto o il prefisso internazionale davanti |
| Codice fiscale | `{{CODICE_FISCALE}}` | Struttura a 16 caratteri. Il **carattere di controllo** non rifiuta, segnala |
| | | Riconosce anche l'**omocodia** — le cifre sostituite da lettere quando due persone collidono — ma lì il carattere di controllo **deve** tornare |
| | | Recupera anche la forma storpiata dall'OCR, se il controllo del candidato corretto torna |
| P.IVA | `{{PARTITA_IVA}}` | Prefisso `IT` o contesto fiscale vicino. La **cifra di controllo** non rifiuta, segnala |
| IBAN | `{{IBAN}}` | **Mod-97** (ISO 13616), anche scritto a gruppi di quattro come lo stampano le banche |
| Coordinate non-IBAN | `{{BBAN}}` | CIN+ABI+CAB+conto, con contesto bancario vicino |
| Carte di pagamento | `{{CARD}}` | **Luhn** (ISO/IEC 7812) |
| Indirizzi | `{{ADDRESS}}` | Via, viale, piazza, corso, largo, contrada e altri, anche abbreviati (`V.le`, `P.zza`, `P.le`, `L.go`, `C.so`); nome per esteso o con l'iniziale puntata (`Via A. Volta`); con civico, CAP e comune |
| Nomi di persona | `{{NAME}}` | Vedi sotto |
| Chiavi e password | `{{SECRET}}` | Token, chiavi API, JWT, blocchi di chiave privata, `password: ...` |
| Documenti d'identità | `{{DOC_ID}}` | Carta d'identità elettronica, patente, passaporto. **Serve il tipo di documento scritto vicino**, vedi sotto |
| Riferimenti catastali | `{{CATASTO}}` | **Pacchetto «Atti e pratiche», spento di default.** Foglio **e** particella insieme, subalterno facoltativo. Il foglio da solo è la pagina di una relazione |
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

## I nomi di persona: tre segnali, tutti con un riscontro

Un elenco di nomi non è mai completo, e affidarsi solo a quello lascia
passare tutti i cognomi non comuni. Valgono quindi anche le regole di
contesto, dal segnale più forte al più debole:

1. **Titolo professionale davanti** — Dott., Ing., Geom., Avv., Sig.
2. **Ruolo, due punti, cognome in maiuscolo** — `Il Ministro: GIORGETTI`.
   È la firma degli atti pubblici italiani.
3. **Nome accanto a un indirizzo di posta** — `Tizio Caio <t.caio@x.it>`.
   È il caso più frequente nelle email.
4. **Nome proprio riconosciuto** che tira dentro la parola successiva.

Tutte chiedono **un riscontro**. Ce n'era una quinta che non lo chiedeva,
ed è stata tolta.

### La firma degli atti pubblici

La seconda regola merita una nota, perché è l'unica in cui gli elenchi non
contano niente — di proposito. Sulle dodici Gazzette Ufficiali del corpus
pubblico quella forma compare **107 volte**, e dei 114 cognomi trovati
**28** stanno nei nostri elenchi: pretendere il riscontro avrebbe lasciato
passare gli altri 86. Quello che decide è il ruolo davanti ai due punti.

Sulla stessa forma un modello NER da 64 MiB prendeva 3 casi su 42. Non è
una questione di quanto sa un modello: il segnale sta nella punteggiatura.

Il permesso si paga con tre vincoli, ognuno nato da un falso positivo
misurato: fra il ruolo e i due punti non ci può essere una **virgola**
(*«Responsabile della protezione dei dati, all'indirizzo: INPS»* — quei due
punti non sono del ruolo); il cognome non attraversa l'**a capo**; e deve
essere **tutto maiuscolo e non una parola comune**, altrimenti su un modulo
si mangerebbe le etichette dei campi (*«Responsabile: SETTORE TECNICO»*).

### Quando la parola comune è anche un cognome

Quarantadue cognomi degli elenchi sono anche parole comuni italiane —
Conti, Villa, Carta, Porta, Valle, Forte, Gentile, Grande — o nomi di città
che in Italia sono cognomi frequentissimi: Napoli, Ferrara, Messina,
Catania, Salerno, Udine, Brescia. Fino alla 1.15.0 la parola comune vinceva
sempre, e *«il dott. Marco Conti»* usciva come *«il dott. NOME Conti»*: il
nome tolto e il cognome lasciato, cioè il documento che sembra trattato e
non lo è.

Dalla 1.16.0 l'ultima parola resta se è un cognome noto **e** ha davanti
una parola che negli elenchi c'è davvero. Serve la coppia: la sola forma
non basta, altrimenti ogni «Valle» a fine frase diventerebbe una persona.

Due parole meritano una nota a parte. **Giulia** ed **Emilia** stavano fra
le parole comuni per un motivo solo: fanno parte di *Friuli Venezia Giulia*
e *Emilia Romagna*. Sono anche due dei nomi di battesimo più diffusi in
Italia. Toglierle dall'elenco avrebbe fatto sparire mezza Italia
amministrativa dai documenti, quindi non si è tolto niente: **decide la
parola accanto**. Se prima c'è «Venezia» o dopo c'è «Romagna» è una regione,
altrimenti è una persona.

### La regola ritirata, e cosa costa averla tolta

Fino alla 1.12.0 esisteva **l'euristica del cognome**: due parole maiuscole
di fila che non sembrano parole italiane sono nome e cognome, **senza
nessun riscontro negli elenchi**. Era spenta di default dalla 1.7.2 ed è
stata **ritirata del tutto nella 1.13.0**.

Il conto su documenti che non contengono un solo dato personale: 8 904
sostituzioni sbagliate su venti moduli dell'Agenzia delle Entrate in
bianco, 14 376 su otto Gazzette, 2 888 su novantanove moduli fiscali
statunitensi. Mangiava «Redditi Persone Fisiche», «Quadro RN», «Imposta
Lorda». Nel 2026 il fenomeno è stato **riprodotto su ventisette moduli
amministrativi scaricati direttamente dagli enti** — documenti che non
abbiamo scelto noi — dove passava da 27 sostituzioni sbagliate a 2 529.

Il difetto non era che indovinava: è che **decideva da sola**.

**Il prezzo, detto per intero.** Un nome e cognome che non stanno in
nessuno dei due elenchi, senza titolo davanti, senza firma e senza
indirizzo di posta accanto, ora **resta nel documento** — e non diventa
nemmeno un sospetto, perché il sospetto richiede almeno un riscontro.
Un nome straniero isolato in mezzo a un testo è il caso tipico. È una
perdita reale, ed è il prezzo scelto: l'alternativa era sbagliare
novantaquattro volte tanto su documenti che non contengono nessuno.

Il limite è sotto test in `tests/test_privacy_riconoscitori.py`, così se un
giorno una regola nuova lo coprisse, questa pagina verrebbe aggiornata
insieme al test invece che dimenticata.

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

### Sul testo, senza OCR di mezzo — misurato il 2026-08-09

Quasi tutti i numeri di questa pagina riguardano le scansioni, dove il
limite principale è l'OCR. Su email, contratti, delibere e documenti Office
il motore è **interamente responsabile**, e non c'è nessuno da incolpare.
Quel percorso non era mai stato misurato: `scripts/bench_testo.py`.

**Falsi positivi: zero.** Su 3,6 milioni di caratteri di moduli
amministrativi veri e in bianco — 27 italiani scaricati da Agenzia delle
Entrate, INPS, Dogane, Giustizia e Camere di Commercio, 15 moduli IRS —
**nessuna sostituzione sbagliata**, 42 documenti su 42 perfetti. Documenti
che non abbiamo scelto noi: è la differenza che conta.

**Richiamo sulle forme regolari: 100%.** Dati dal valore noto inseriti in
paragrafi veri di Gazzetta Ufficiale, verificati puliti prima
dell'inserimento: 520 casi su 520, zero perdite silenziose. Otto tipi di
dato in tre cornici ciascuno, e i nomi in tutti e cinque i livelli di prova.

**Richiamo sulle forme difficili: 73% redatto, 20% segnalato, 6,7% perso in
silenzio.** È il numero onesto, perché è così che i dati arrivano davvero da
un `.docx` o da un PDF:

| Forma | Esito |
|-------|-------|
| IBAN e carta a gruppi di quattro o con trattini, codice fiscale in minuscolo, telefono coi punti o senza parola davanti, email offuscata `[at]`, indirizzo senza civico, **email spezzata da un a capo** | redatta |
| IBAN spezzato da un a capo · `Il Direttore Generale: MORETTI` · un cognome che è anche parola comune (`Marco Chiesa`) | **segnalata**, non tolta |
| Nome e cognome fuori da entrambi gli elenchi, senza titolo né firma né posta accanto | **persa in silenzio** |

L'unica perdita silenziosa rimasta è il limite dichiarato più sopra, quello
che il ritiro dell'euristica ha reso esplicito. Le altre due categorie non
sono equivalenti e la tabella le tiene separate apposta: **segnalato** lascia
a chi legge la possibilità di intervenire, **perso in silenzio** no.

**Cosa questa misura ha trovato.** L'indirizzo di posta mandato a capo
dall'estrattore — `g.moretti@` a fine riga e il dominio su quella dopo —
spariva in silenzio in 20 casi su 20. Corretto nella 1.14.0, con il permesso
più stretto possibile: un solo a capo, solo dopo la chiocciola.

### La varietà dei valori — misurato il 2026-08-09

Le due misure sopra cambiano la **frase** in cui il dato compare. Cambiare
il **valore** è una domanda diversa, e ha trovato due difetti che nessuna
delle altre vedeva. Trecento valori distinti per tipo, tutti validi:
`scripts/bench_varieta.py`.

Reggono al 100%: IBAN con CIN e ABI qualsiasi; carte Visa, Mastercard,
Discover e **American Express da 15 cifre**; numeri fissi con prefisso da 2,
3 e 4 cifre; indirizzi con dieci parole diverse per «via»; cinquanta domini
di posta.

Due non reggevano, e sono stati corretti nella 1.15.0:

- il **codice fiscale con omocodia** — quello in cui l'Agenzia sostituisce
  alcune cifre con le lettere `L M N P Q R S T U V` perché due persone
  otterrebbero lo stesso codice: **zero riconosciuti su 300**, il 40% perso
  in silenzio. Ora viene tolto, ma **solo se il carattere di controllo
  torna**: ammettere lettere dove il codice vuole cifre rende la forma quasi
  una parola qualsiasi, e lì l'aritmetica non è un di più, è ciò che regge
  tutto;
- il **telefono con la barra**, `Tel. 011/7323929`, forma standard delle
  carte intestate italiane: **zero su 300**, mentre gli stessi numeri con lo
  spazio o il trattino venivano presi. Ora viene tolto **se davanti c'è una
  parola di contatto** — un recapito non ha nessun conto che possa
  smentirne la forma, quindi il permesso si paga chiedendo il contesto.

Resta a zero, per scelta documentata, la **partita IVA nuda**: undici cifre
senza prefisso `IT` né contesto fiscale vicino sono indistinguibili da un
numero qualsiasi.

La stessa domanda girata sui **venti riconoscitori anglosassoni** e sui
documenti d'identità — NHS, National Insurance, SSN, ITIN, routing ABA, SIN,
ABN, TFN, tutti e sei i formati di codice postale britannico, MRZ, BBAN,
carta d'identità, patente, passaporto — non ha trovato niente:
`scripts/bench_varieta_en.py`, tutti al 100%.

Sul **resto del pacchetto italiano** (`scripts/bench_varieta_it.py`,
ventisei forme, duecento valori ciascuna) sono usciti invece tre difetti,
corretti nella 1.16.0: i due sui nomi descritti sopra, e gli **indirizzi con
l'iniziale puntata** — *«Via A. Volta 5»*, *«piazza G. Verdi 1»* — che il
riconoscitore non poteva nemmeno cominciare a leggere. Quest'ultimo,
misurato sul corpus a verità zero dove il motore non sostituiva **nulla**,
tira fuori **41 indirizzi veri** da dodici numeri di Gazzetta Ufficiale, con
zero falsi positivi: `via PEC, 30` e `via FTP, 12` restano intatti.

Reggevano già: cognomi con la particella (De, Di, Lo, Della), con
l'apostrofo (D'Angelo, Dell'Orto), accentati, nomi composti; codici fiscali
**femminili** (giorno di nascita +40) e di chi è **nato all'estero** (codice
comune `Z…`); civico con la lettera, indirizzi senza CAP; numeri verdi 800,
servizi 199, prefissi esteri; URL, JWT, chiavi AWS, importi, date di
nascita.

### La parità fra i formati

Lo stesso documento in dieci formati — `.txt`, `.html`, `.csv`, `.json`,
`.xml`, `.docx`, `.xlsx`, `.pptx`, `.eml` e un `.png` che passa dall'OCR —
deve proteggere allo stesso modo, perché fra un formato e l'altro cambia
l'estrattore. **Otto dati su otto in tutti e dieci**, nessuno lasciato
leggibile. Banco: `scripts/bench_formati.py`.

### Che il richiamo non possa scendere in silenzio

Tutte le misure sopra contano gli **errori** su documenti che non
contengono niente. È la metà giusta da guardare per prima — un motore che
sovra-redige è inutilizzabile — ma è una metà, e l'altra è invisibile per
costruzione: se una modifica facesse smettere il motore di vedere «piazza
G. Verdi, 1», ogni banco a verità zero resterebbe verde. **Zero errori su un
documento vuoto è anche il risultato di un motore spento.**

`scripts/bench_corpus_pubblico.py` guarda l'altra metà, e lo fa sui
documenti **che non abbiamo scritto noi**: Gazzette Ufficiali e moduli
scaricati dagli enti che li pubblicano. Fallisce in due direzioni — se
compare una sostituzione sui moduli in bianco (dove l'atteso è zero), e se
il numero di sostituzioni sulla prosa vera **scende**. I numeri sono
congelati insieme all'impronta dell'elenco dei file, così un corpus diverso
viene detto invece di sembrare una regressione.

Il corpus non sta nel repository: sono decine di megabyte e non sono nostri
da ridistribuire. Il test si salta dicendolo, ma i tre test che provano il
**meccanismo** girano sempre — un controllo che gira solo sulla macchina di
chi sviluppa non è un controllo.

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

- **Nessun elenco di cognomi è completo**, e dalla 1.13.0 non c'è più
  un'euristica che indovini i mancanti: un nome e cognome fuori elenco,
  senza titolo, firma o indirizzo di posta accanto, **resta nel documento e
  non produce nemmeno un sospetto**. Vedi «La regola ritirata» più sopra.
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
  sproposito. L'euristica che indovinava senza riscontri, che era la fonte
  principale degli errori, è stata **ritirata nella 1.13.0**.
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
