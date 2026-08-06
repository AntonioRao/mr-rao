# Changelog

## 1.7.0 — Le difese che c'erano, dove non arrivavano

Nessuna funzione nuova: cinque punti in cui i presidi esistenti si fermavano
un passo prima. Ognuno è stato verificato disattivandolo, per controllare che
il suo test diventasse rosso invece di restare verde per caso.

### Il controllo anti-CSRF non scattava sempre

```python
origin = request.headers.get("Origin")
if origin and request.method not in ("GET", "HEAD", "OPTIONS"):
```

**`if origin`.** Niente header, niente controllo — e una navigazione da
`<form>` cross-site può arrivarci senza. Gli endpoint accettano
`multipart/form-data`, che è CORS-safelisted: nessun preflight a fermarla.

Adesso si guarda prima `Sec-Fetch-Site`, che i browser attuali mandano su
ogni richiesta. `Origin` resta come ripiego per chi non lo manda: curl, la
CLI, un browser vecchio.

Ne è uscito un secondo caso, che non era in preventivo. Per `localhost` i
browser considerano **stessa site** anche una porta diversa: una pagina
servita da un altro programma su `127.0.0.1:8080` ha il nostro stesso
hostname, quindi il controllo su `Origin` la lasciava passare. Ora è
rifiutato anche `same-site`.

### Esporsi in rete non deve spegnere la difesa anti-rebinding

Con `MR_RAO_HOST=0.0.0.0` l'allow-list degli host diventava `*`: la difesa
spariva **esattamente quando l'app si esponeva**. Una pagina ostile che si
faceva risolvere sull'IP della macchina tornava a poter *leggere* le risposte
— cioè i documenti convertiti, che è tutto ciò che c'è da proteggere qui.

Adesso l'allow-list contiene gli indirizzi e i nomi di questa macchina.
L'accesso legittimo per IP o per nome passa; il dominio dell'attaccante, che
nell'header `Host` porta il proprio, no. Dietro un reverse proxy serve
`MR_RAO_ALLOWED_HOSTS`, e il 403 lo dice invece di lasciare indovinare.

### Una chiave di firma che nessuno userà per sbaglio

`SECRET_KEY` era la costante `"mr-rao-local-dev-only"`, scritta in un
repository pubblico. Oggi non la usa niente — nessuna sessione, nessun
cookie firmato — ed è proprio questo il problema: il giorno che qualcuno
scrive `session[...]`, che in Flask è una riga, quella costante diventa la
chiave con cui si firmano i cookie, e **non si rompe niente** che lo faccia
notare.

Ora è casuale a ogni avvio e non tocca il disco. Un file sarebbe stato
peggio della costante: seguirebbe l'eseguibile portable dentro OneDrive, nei
backup e nello zip che passa a un collega.

### Intestazioni, con aspettative oneste

`frame-ancestors 'none'`, `nosniff`, `no-referrer` su ogni risposta.

Quella che si guadagna il posto è la prima: impedisce di incorniciare
l'applicazione in un'altra pagina. Il contenuto non sarebbe comunque
leggibile — c'è la same-origin policy — ma il **clic** sì, e qui un clic
accende la sorveglianza di una cartella. `nosniff` ha poco da mordere finché
ogni endpoint risponde JSON: vale come rete per quelli che verranno.

### Un OCR non tiene più occupato un worker per mezz'ora

`MR_RAO_OCR_TIMEOUT`, 15 minuti di default, `0` per toglierlo.

Un thread Python non si uccide dall'esterno, quindi il limite si è messo
dove già si legge il flag di annullamento: **fra una pagina e l'altra**.
Ferma le pagine successive, non quella in corso.

Allo scadere il testo letto fin lì si restituisce, con un avviso **in cima**:

> ⚠️ **OCR interrotto dopo 12 pagine su 50:** superato il limite di tempo.
> Il testo qui sotto è parziale, e con esso la rimozione dei dati personali.

In cima e non in fondo perché un documento troncato in silenzio è peggio di
nessun documento: l'anonimizzazione ha visto solo le pagine lette, e chi legge
deve saperlo *prima* di fidarsi. Per la stessa ragione un OCR scaduto senza
aver letto niente non dice più «nessun testo riconoscibile», che manderebbe
a cercare il problema nel documento invece che nel tempo.

### Un documento non deve poter piantare il convertitore

CodeQL segnalava `py/polynomial-redos` sulla pulizia del testo per
l'incolla-in-chat. Non era un falso positivo:

```python
re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
```

Con un documento fatto di `<!--` mai chiusi il motore riparte da ogni
apertura e arriva ogni volta in fondo. Misurato: 32 mila caratteri in
492 ms, 80 mila in 3,2 secondi — due volte e mezzo l'ingresso, sei volte e
mezzo il tempo. Il limite d'invio è 50 MB, e il documento lo sceglie chi lo
carica.

Nessuna riscrittura dell'espressione lo risolve, perché a essere quadratico
è il *numero di partenze*, non il singolo tentativo. Due `find` che
avanzano sempre in avanti sono lineari: **0,29 ms** sullo stesso ingresso.
Stessa correzione nel gemello JavaScript, dove il prezzo era la scheda del
browser che si pianta.

Le note che l'applicazione scrive di suo sono ora ancorate a inizio riga —
prima `\n?` davanti rendeva ambiguo dove cominciasse il match, ed era la
seconda segnalazione.

### Gli altri dodici alert, chiusi con la ragione scritta

Restavano dodici segnalazioni. Nessuna era sfruttabile, ma per due motivi
diversi — ed è la distinzione che rende il triage una cosa seria invece che
un'archiviazione:

- **sette falsi positivi.** CodeQL segue il nome del file caricato fino a
  una scrittura su disco. Il flusso esiste, ma l'unica parte controllata è
  `Path(filename).suffix`, che **non può contenere un separatore** — provato
  con `../../../etc/passwd`, `a.pdf/../../x`, `..\..\win.ini` — e il nome
  del file lo sceglie `tempfile.mkstemp` nella cartella temporanea. Sopra
  c'è una seconda barriera indipendente: `ALLOWED_EXTENSIONS`;
- **cinque scelte consapevoli.** I percorsi della sorveglianza non sono
  confinati perché la hotfolder deve poter stare dove serve; il bind largo
  è la sonda che controlla se la porta è libera; il tooltip usa `innerHTML`
  perché sei di essi contengono `<b>` e la sorgente è un template.

Le motivazioni stanno **anche nel codice**, non solo nella scheda Security:
chi clona il repository si porta dietro i file, non l'interfaccia di GitHub.
E ognuna dice a quale condizione l'alert va riaperto — una chiusura
sopravvive al codice che l'ha giustificata, ed è lì che il triage marcisce.

Lasciarli aperti non era prudenza: dodici «high» permanenti su un
repository pubblico dicono una cosa falsa a chi guarda, e insegnano a non
guardare più. È così che il tredicesimo non lo vedi.

### Una FAQ per chi cerca l'overclaim

`docs/PRIVACY_FAQ.md` — undici domande di chi apre il repository per
trovarci una promessa più grande del codice. Comincia rispondendo **no**
alla domanda che farebbe più comodo («è anonimizzazione GDPR?»).

Ci è entrata una cosa che prima non era scritta da nessuna parte: i
segnaposto **non sono numerati**, quindi due persone diverse diventano lo
stesso `{{NAME}}`. In uscita non si può ricollegare chi era chi — non esiste
nessuna mappa da custodire, perché non viene mai costruita. Ma un documento
**spezzato in pezzi** perde il contesto fra un blocco e l'altro, e un nome
riconosciuto sul testo intero può sopravvivere in un frammento. Conviene
convertire il documento intero e incollare il risultato, non convertire i
pezzi.

Gli esempi della pagina sono sotto test, come già quelli del README: se il
codice cambia e la pagina no, la suite lo dice prima che se ne accorga un
lettore.

### Italiano scritto da chi l'italiano lo parla

Una passata su tutti i testi pubblici, dopo una segnalazione precisa: parole
tradotte troppo alla lettera, di quelle che fanno pensare a un testo mai
riletto da nessuno.

| Prima | Dopo | Perché |
|-------|------|--------|
| «un **attrezzo** locale» | «un **tool** locale» | un attrezzo è da officina; «tool» si usa anche in italiano |
| «la **schermatura** dei dati» | «l'**anonimizzazione**» | si scherma un cavo, non un dato personale |
| «spento **di serie**» | «spento **di default**» | l'interfaccia diceva già «di default»: era il documento a essere fuori posto |
| «a ogni **confine di stadio**» | «al passaggio da uno stadio all'altro» | *stage boundary* tradotto parola per parola |
| «riconoscitori **innestabili** per Paese» | «estendibili ad altri Paesi» | *pluggable* tradotto parola per parola |
| «**Chi serve** un pipeline» | «**A chi serve** una pipeline» | in italiano «chi serve» significa il contrario; e pipeline è femminile |
| «due **confusions** tipiche» | «due confusioni tipiche» | parola inglese rimasta in mezzo |
| «classificazione automatica **a scala**» | «su larga scala» | *at scale* |
| «quasi-**identifier**» | «quasi-identificatori» | il termine italiano esiste ed è quello |

E una frase proprio sgrammaticata, in `SECURITY.md`: «i parser che legge sono
gli stessi **che gira** qualunque altro programma».

Ridotto anche l'uso di «presidio»: è gergo legittimo, ma dodici volte in sei
pagine è un tic, non un termine.

### Cosa è stato valutato e scartato

- **Confinare i percorsi della sorveglianza.** Romperebbe la funzione: la
  hotfolder deve poter stare nei Documenti o su un disco di rete, e c'è un
  selettore di cartelle nativo apposta. Il danno massimo resta comunque
  qualche cartella e dei file `.md` nuovi, mai una sovrascrittura.
- **Token CSRF double-submit.** Con Host, `Sec-Fetch-Site` e `Origin` non gli
  resta niente da intercettare, e aggiungerebbe un modo nuovo di fallire.
- **Sandbox dei parser.** Una seria su Windows è un progetto a sé; una finta
  proteggerebbe da niente. Il threat model adesso lo dichiara esplicitamente
  in [SECURITY.md](../SECURITY.md), che vale di più.

**352 test** (erano 315).

## 1.6.0 — Il checksum come garanzia, non come filtro

La 1.5.0 aveva imparato a **dire** quello che non riusciva a togliere. Questa
impara a toglierlo.

### Recupero dei codici storpiati dall'OCR

Un codice fiscale letto male — `RSSMRA85T1OA562S`, con la O al posto dello
zero — non ha più bisogno di restare nel testo. Il motore prova a
correggere **fino a due caratteri** usando le confusioni tipiche del
riconoscimento ottico, e sostituisce **solo se il checksum del candidato
corretto torna**.

Non decide un'euristica: decide l'aritmetica. È l'unico modo di essere
tolleranti senza aprire la porta ai falsi positivi.

```
RSSMRA85T1OA562S   →  {{CODICE_FISCALE}}   (1 correzione, controllo OK)
lT60X05428…123456  →  {{IBAN}}             (1 correzione, mod-97 OK)
lT60X05428…123457  →  invariato            (nessuna correzione lo salva)
```

La confusione più frequente di tutte non è lettera-cifra ma **lettera-lettera**:
la elle minuscola letta al posto della i maiuscola. `IT60` diventa `lT60`,
che di lettere ne ha ancora due e quindi supera ogni controllo di forma —
e fallisce il mod-97 senza che nessuno capisca perché.

**Una regressione trovata dai test.** La prima versione trasformava il
numero d'ordine `5551234567890123` in `SS51234567890123`, e quel candidato
il mod-97 lo supera davvero. Il checksum protegge dai candidati sbagliati,
non da uno spazio di candidati troppo largo: se puoi trasformare qualunque
sequenza di cifre in un IBAN, prima o poi ne azzecchi uno. Adesso almeno
una delle due iniziali dev'essere già una lettera.

### L'IBAN come lo stampano le banche

`IT60 X054 2811 1010 0000 0123 456` — a gruppi di quattro, la forma più
comune su carta intestata, bonifici e fatture — **non veniva riconosciuto
affatto**. Il riconoscitore pretendeva i caratteri attaccati.

Non l'aveva trovato nessuna delle due analisi che hanno esaminato il
motore: si cercava il difetto sofisticato mentre mancava il caso normale.

### La cifra di controllo della partita IVA

Stessa scelta del codice fiscale: non rifiuta, informa. Undici cifre in un
contesto fiscale restano sostituite comunque; se la cifra di controllo non
torna, il numero diventa un sospetto — perché o non era una partita IVA, o
il documento è storpiato.

### Email offuscate

`mario [at] esempio [dot] it`, `(at)`, `chiocciola`, `punto`. Chi le scrive
così lo fa apposta perché non sembrino email, e infatti al riconoscitore
non sembravano.

- 315 test (erano 304).

## 1.5.0 — «3 redatti, 2 da controllare»

Il limite più serio del motore non era un difetto: era una scelta. I
riconoscitori cercano forme **valide** e l'OCR produce forme **quasi**
valide — `A01` letto `AD1`, `IT60` letto `lT60`. La struttura non torna,
il dato resta nel testo, e resta perfettamente leggibile da una persona.

Sostituire senza certezza vorrebbe dire redigere mezzo documento. Ma
tacere è peggio: **«3 redazioni» su un documento pulito e «3 redazioni» su
un documento che il riconoscitore non ha saputo leggere sono lo stesso
numero e due situazioni opposte.**

Ora il rapporto distingue le due cose. Dopo la sostituzione, un passaggio
sul testo rimasto cerca ciò che *somiglia* a un dato personale senza
esserlo abbastanza da poterlo togliere:

- sedici caratteri con la proporzione di un codice fiscale, struttura non valida;
- la forma di un IBAN che non supera il mod-97 — **senza pretendere le maiuscole**, altrimenti il sospetto non scatterebbe proprio nel caso che lo motiva;
- sedici cifre che non superano Luhn;
- dopo «cell.» o «tel.» una sequenza che mescola cifre e lettere.

Il risultato compare accanto al conteggio: **«🛡️ 3 redazioni · ⚠️ 2 da
controllare»**, con il dettaglio nel suggerimento. I campioni sono
mascherati (`RS••••••••••••2S`): quanto basta a ritrovarli nel documento,
non a leggerli.

E la prova che non è rumore: sul verbale amministrativo — protocolli,
delibere, codici gara, date — **zero redazioni e zero sospetti**. Se ogni
numero diventasse un avviso, l'avviso non varrebbe più niente.

### Il carattere di controllo del codice fiscale

Il CF era l'unico dato a struttura fissa senza validatore, mentre l'IBAN
ha il mod-97 e le carte hanno Luhn. Ora c'è il calcolo del carattere di
controllo (DM 23/12/1976).

Non serve a rifiutare: un codice con la struttura giusta viene sostituito
comunque, perché su un dato personale l'errore va fatto nella direzione
prudente. Serve a **sapere**: se la struttura torna e il controllo no,
quasi sempre il testo viene da una scansione che ha storpiato un
carattere — e allora ne avrà storpiati altri, che nessun riconoscitore ha
visto. Diventa un sospetto.

### Quattro difetti trovati misurando

Nessuno dei quattro era stato previsto ragionando.

**`Riferimento Del Piero Alessandro` → `Riferimento Del {{NAME}} {{NAME}}`.**
La finestra di tre parole partiva da «Riferimento», consumava «Del» e
lasciava indietro i due nomi, che la regola del nome isolato sostituiva
separatamente. Adesso il riconoscitore prende la sequenza **intera** di
parole maiuscole e decide dentro quali tratti sono nomi, con un tetto a
quattro parole: oltre non è un nome, è un titolo scritto in maiuscolo.

**`spedito via Corriere Espresso` → `{{NAME}}`.** Il riconoscitore di
indirizzi si asteneva correttamente, perché «Corriere» è nel suo elenco di
parole di stop. Poi l'euristica dei nomi si mangiava la coppia. Un
un controllo dentro un riconoscitore non protegge gli altri: adesso quell'elenco
vale per tutti.

**`chiave: importante da ricordare` → `chiave: {{SECRET}}`.** In italiano
«chiave» ha parecchi significati; «password» no. Le etichette ambigue ora
pretendono che anche il *valore* sembri una credenziale.

**Coordinate bancarie contate come telefoni.** `BBAN X 05428 11101
000000123456` veniva spezzato e sostituito con due `{{PHONE}}`: il dato
spariva ma il rapporto diceva «2 telefoni». Un conteggio che sbaglia
categoria è peggio di uno che manca, perché chi lo legge si fida. Ora c'è
un riconoscitore per le coordinate italiane non-IBAN, e gira **prima** dei
telefoni.

- 304 test (erano 276).

## 1.4.2 — Il pacchetto spediva l'icona sbagliata

Il collegamento sul Desktop funzionava, puntava al posto giusto e mostrava
un'icona valida. Solo che non era **quella** icona: il pacchetto ne
spediva una versione più povera — 50.050 byte invece di 65.384 — senza la
terza tappa del gradiente, senza il bordo interno e senza la sottolineatura
sotto «RAO».

La causa era un `try/except` di troppo. Il passo 1 del build generava una
prima serie di icone, poi provava a rigenerarle da `logo.png` con
`sync_icons_from_logo` — ma quell'`import` falliva sempre, perché la
cartella del progetto non era nel percorso di ricerca dei moduli. L'errore
finiva in un `except Exception` che stampava «skipped» e proseguiva,
lasciando in giro le icone della prima passata e sovrascrivendo per giunta
`favicon.svg`, che era stato rifinito a mano.

Un fallimento silenzioso e una riga di log che nessuno legge: la
generazione delle icone risultava riuscita a ogni build.

Adesso quel passaggio è obbligatorio, non facoltativo. La prova che conta:
dopo aver eseguito `generate_icons.py`, `git status` su `static/img/` è
vuoto — l'artwork committato viene riprodotto **identico**.

E la verifica del pacchetto confronta l'icona spedita con quella del
repository. Non «l'icona c'è», che era vero anche prima: **è la stessa**.

## 1.4.1 — Due difetti trovati installando, non testando

Entrambi usciti dalla prova completa da zero: disinstalla, scarica dalla
release, installa, converti. Nessuno dei 253 test li aveva visti.

**Il disinstallatore non chiudeva Mr. Rao.** Usava `taskkill` senza `/F`,
che invia una richiesta di chiusura che un'applicazione console può
semplicemente ignorare. Il processo restava, la cartella restava bloccata,
e la disinstallazione finiva con un avviso invece che con una
disinstallazione. Adesso prova con garbo e poi sul serio. Il caso è quello
normale, non un caso limite: chi disinstalla lo fa quasi sempre con il
programma aperto.

**La parola che introduce una firma finiva dentro il nome.** `FIRMATO
MARIO ROSSI` diventava un solo `{{NAME}}`, portandosi via anche
«FIRMATO». È la stessa famiglia del verbo davanti a un indirizzo email,
corretto poco prima: la regola prende una sequenza di parole maiuscole e
la sostituisce tutta se una di quelle è un nome noto. Aggiunti i participi
che introducono una firma — firmato, redatto, approvato, sottoscritto e
altri.

Il nome sparisce come prima; la parola che lo introduce resta, ed è quella
che dà senso alla riga.

- 256 test.

## 1.4.0 — Su una mail vera passava troppa roba

La segnalazione era circostanziata: in una mail sul desktop restavano in
chiaro gli URL, i numeri di cellulare, gli indirizzi di casa e i nomi
scritti accanto agli indirizzi di posta. Prima di toccare il codice ho
misurato, su una mail italiana realistica con dieci categorie di dati:

| | prima | dopo |
|---|---|---|
| sostituzioni | 10 | **29** |
| persone rimaste in chiaro | 6 su 7 | **0** |
| indirizzi rimasti in chiaro | 5 su 5 | **0** |
| URL rimasti in chiaro | 3 su 3 | **0** |
| numeri rimasti in chiaro | 4 su 5 | **0** |

Il difetto sui numeri era di forma, non di copertura: il riconoscitore
pretendeva le cifre finali tutte attaccate, e `335 123 4567` non lo era.
Un cellulare scritto come lo scrive un essere umano non veniva visto.

### Riconoscitori nuovi

- **Indirizzi web** — `http`, `https`, `www.`. Solo questi tre: bastano a
  riconoscerli a occhio, e non trasformano ogni `nome.it` del testo in un
  link. La punteggiatura finale della frase resta al suo posto.
- **Indirizzi di casa** — via, viale, piazza, corso, largo, contrada e altri
  venti, con il nome della strada, il civico, il CAP e il comune.
- **Chiavi e password** — token, chiavi API, blocchi di chiave privata,
  JWT, e il caso generico `password: ...`. L'etichetta resta, il valore no:
  così si capisce cosa è stato tolto.
- **Carte di pagamento** — verificate con il controllo di Luhn, esattamente
  come gli IBAN sono verificati con il mod-97. Un numero d'ordine di sedici
  cifre non è una carta e resta dov'è.
- **Date di nascita** — spente di default, perché toglierebbero anche le
  date che servono. Accese, sostituiscono solo quelle scritte accanto a
  «nato il», «data di nascita» e simili: la data della riunione resta.

### I nomi: tre segnali invece di un elenco

Un elenco di nomi non è mai completo — è il motivo per cui sei persone su
sette passavano. Adesso valgono anche le regole di contesto:

1. **titolo professionale** davanti (Dott., Ing., Geom., Avv.);
2. **nome accanto a un indirizzo di posta** — `Tizio Caio <t.caio@x.it>`
   è il caso più frequente in assoluto nelle mail, ed era scoperto;
3. **nome proprio riconosciuto** che tira dentro la parola successiva.

E in più l'euristica che serviva davvero: **due parole maiuscole di fila
che non sono parole italiane sono quasi sempre nome e cognome**, anche se
il cognome non compare in nessun elenco. È l'unica regola che può
sbagliare, e infatti ha un interruttore suo (`privacy_name_guess`,
`--no-name-guess`), spento di default nel profilo Fatture dove le
denominazioni sociali abbondano.

L'elenco dei nomi italiani è comunque cresciuto di circa dieci volte.

### Il freno all'entusiasmo

Un filtro che redige tutto è inutile quanto uno che non redige niente. Il
banco di prova sono due testi, non uno: la mail, dove deve sparire tutto, e
un verbale amministrativo pieno di «Comitato Tecnico», «Piano Industriale»,
«Fase Uno», numeri di protocollo e date, dove **non deve sparire niente**.
Il verbale è un test come gli altri e passa con tutti i riconoscitori accesi.

Due controlli lo tengono in piedi: un elenco di parole italiane che capita di
trovare maiuscole, e un controllo sulle terminazioni — «Industriale» e
«Tecnico» finiscono come finiscono le parole, non come finiscono i cognomi.

### Word, Excel e PowerPoint non hanno mai funzionato

Segnalato da un utente con un verbale di collaudo pieno di testo, che
riceveva **«Il file caricato non contiene testo riconoscibile»**.

I formati Office di MarkItDown vivono dietro degli *extra* che non erano
installati. Senza, la conversione alza `MissingDependencyException`, il
testo estratto è vuoto, e il messaggio dà la colpa al documento. DOCX,
DOC, XLSX, XLS, PPTX e PPT: **nessuno di questi ha mai funzionato**, in
nessuna versione, pur essendo annunciati nella tabella del README, nei
badge della finestra di caricamento, nell'elenco del selettore file e
nelle voci del menu contestuale.

Non si vedeva dai test perché i test usavano file finti: un `.docx` vero
non era mai stato convertito. Adesso ce n'è uno, costruito byte per byte
dentro il test, e un controllo che fallisce se un formato dichiarato ha
la sua dipendenza assente. Le dipendenze sono elencate per nome e non
come extra: `markitdown[docx]` non porta `python-docx`.

Cambia anche il messaggio. Quando la causa è nostra la diciamo — «Manca
la libreria python-docx… Non dipende dal documento» — invece di mandare
qualcuno a cercare il problema nel proprio file. Un documento davvero
vuoto continua a ricevere il messaggio di prima.

Le sette librerie aggiunte sono tutte MIT o BSD: nessun nuovo obbligo.

### Nomi in maiuscolo e cognomi da soli

Sempre da una mail vera. Il riconoscitore dei nomi pretende almeno una
minuscola — è così che esclude in un colpo solo acronimi, numeri romani e
i segnaposto già inseriti — e questo lo rendeva **cieco a `MARIO ROSSI`**,
che nelle firme e nelle intestazioni è frequentissimo. Ora c'è una regola
apposta, con gli stessi controlli: `CODICE FISCALE` e `ORDINE DEL GIORNO`
restano dove sono.

E un cognome noto scritto da solo, come capita nelle firme, ora viene
sostituito — tranne quelli che sono anche parole comuni: «Costa», «Villa»,
«Monte», «Ponte» da soli restano quello che sembrano.

Sulla mail di prova: da 98 a 100 nomi sostituiti su 229 dati, e le uniche
sequenze maiuscole superstiti contengono tutte una parola italiana comune.

### Il pannello privacy non comandava niente

Trovato mentre collegavo i riconoscitori nuovi all'interfaccia. Quando la
richiesta portava un profilo, il server prendeva il preset e **buttava via
tutto il resto del modulo**. Siccome la pagina manda sempre il profilo,
l'intero pannello «Quali dati nascondere» era decorativo: si spuntava una
casella e non cambiava nulla, senza alcun errore. Anche l'interruttore
generale, e anche «copia pulita» e le tabelle.

Adesso il profilo è il punto di partenza e la casella dell'utente vince.
Un client che manda solo il profilo continua ad avere esattamente il preset.

Non si vedeva dai test perché i test chiamavano il motore direttamente:
quelli nuovi passano dalla stessa porta da cui passa la pagina. Due di essi
verificano che ogni campo del motore abbia la sua casella nella pagina e
che la pagina la spedisca — la prossima volta il difetto nasce già rotto.

### Collegamenti e disinstallazione

Il collegamento sul Desktop poteva non nascere senza che nessuno lo dicesse:
la creazione non veniva verificata e il messaggio finale era «completata» in
ogni caso. Ora installazione e disinstallazione passano da un solo script,
che stampa il percorso di ogni collegamento e distingue `OK` da `FALLITO`;
se manca il file `.ico` usa l'icona dell'eseguibile invece di rinunciare.
L'elenco delle estensioni del menu contestuale, che viveva in due file
diversi ed era già andato fuori sincrono una volta, adesso sta in uno solo.

### Il build adesso apre quello che ha costruito

Un codice di uscita zero non dice niente su cosa succede al doppio clic:
era già capitato di produrre 390 MB che aprivano una finestra nera e si
chiudevano, e a scoprirlo fu una persona che avviava l'eseguibile, non il
build. Adesso l'ultimo passo avvia il pacchetto, interroga `/api/health`,
converte un `.docx` vero e controlla che l'anonimizzazione abbia lavorato.
Se qualcosa non torna, il build **respinge il pacchetto**.

Ha ripagato subito, e non per un difetto del build: `Contatta
mario.rossi@example.it` faceva sparire **«Contatta»**. La regola «una
parola maiuscola accanto a un indirizzo di posta è un nome» — quella che
risolve i cognomi sconosciuti — davanti a un'email si prendeva anche i
verbi. Ora una parola sola dev'essere un nome o un cognome che negli
elenchi c'è davvero; una coppia continua a bastare.

Nessun test l'aveva visto: passavano tutti da testo scritto per
l'occasione, e nessuno cominciava con un verbo all'imperativo.

### Un residuo di pip che rompeva il build

Il primo tentativo di ricostruire il pacchetto è morto dentro PyInstaller
con un `TypeError` che non nominava la causa. Era una cartella `scipy/`
priva di `__init__.py`: Python la importa lo stesso come *namespace
package*, `import scipy` riesce e `scipy.__file__` è `None`.

Origine: pip su Windows, quando non riesce a cancellare un `.pyd` perché è
in uso, lo rinomina anteponendo una tilde e conta di toglierlo dopo. La
rimozione di Scrubadub nella 1.3.3 ha lasciato 71 MB di macerie —
`~klearn`, `~egex`, `~cipy.libs` — che hanno rotto il build due versioni
più tardi. `scripts/check_venv.py` adesso le nomina prima, invece di
lasciarle comparire come un difetto di qualcun altro.

- 253 test (erano 164).
- Pacchetto portable: 311 MB (le librerie Office ne aggiungono 36).

## 1.3.3 — Via Scrubadub: non faceva quello che credevamo

Il pacchetto portable **non si avviava affatto**. PyInstaller installa un
runtime hook per nltk che viene eseguito prima di qualunque nostro codice:
importa nltk, che importa scikit-learn, che legge un `.css` non incluso nel
bundle. `FileNotFoundError`, applicazione morta prima di arrivare a Flask.

Scoperto avviando l'eseguibile invece di fidarsi del codice di uscita del
build. Caricarlo così sulla release avrebbe consegnato al primo utente 390 MB
che aprono una finestra nera e si chiudono.

### La verifica che ha deciso

Scrubadub era lì «per i documenti in inglese». Misurato su un testo inglese
con nome, telefono UK e SSN:

| | risultato |
|---|---|
| con Scrubadub | 1 redazione (l'email, presa dal *nostro* riconoscitore) |
| senza Scrubadub | 1 redazione — **identico** |
| Scrubadub da solo | `Contact John {{EMAIL}}@acme.co.uk` — spezza il testo e manca nome, telefono e SSN |

Non aggiungeva nulla, in nessuno dei due ambienti, e da solo danneggiava il
testo. Rimosso.

### Cosa cambia

- Dipendenza e opzione `use_scrubadub` eliminate: non resta un comando che non
  fa niente, come per il selettore di lingua OCR.
- **51 pacchetti invece di 70**, **4 licenze con obblighi invece di 6**.
- Sparisce `python-stdnum`: **non c'è più alcuna dipendenza LGPL a runtime**
  oltre a pystray, che serve solo per l'icona nella barra di sistema.
- Portable: **275 MB invece di 393**, 1737 file invece di 4244.
- Il riconoscimento dei dati personali è interamente codice di Mr. Rao:
  email, telefoni, codice fiscale, P.IVA, IBAN con mod-97, importi, nomi.

### Menu contestuale

«Apri con Mr. Rao» e «Invia a» puntavano a un eseguibile non più esistente e
solo 4 estensioni su 10 erano registrate. Reinstallando il pacchetto le voci
tornano corrette: tutti i file più 7 estensioni, e il collegamento in «Invia a».

## 1.3.2 — L'anonimizzazione toglie solo ciò che l'OCR ha letto bene

Emerso testando il repository appena clonato su un PDF scansionato vero, non
su un file di prova.

Stesso contenuto, due strade:

| letto da | redazioni |
|---|---|
| immagine | 3 (`{{CODICE_FISCALE}}`, `{{IBAN}}`, `{{NAME}}`) |
| PDF scansionato | 1 (solo il nome) |

L'OCR storpia i caratteri: `A01` diventa `AD1`, `IBAN IT60X…` diventa
`TBAN1TB0X…`. I riconoscitori sono espressioni regolari e cercano un codice
scritto bene: se non lo trovano, il dato **resta nel testo** — deformato, ma
spesso ancora sufficiente a identificare una persona.

Non è un difetto del codice, è il limite del metodo. Ma è proprio sui
documenti scansionati — quelli per cui uno strumento del genere serve di più —
che la garanzia è più debole, e finora non lo diceva nessuno.

- Il risultato porta un **avviso esplicito** quando la redazione ha lavorato su
  testo OCR, con l'invito a guardare il confronto prima/dopo. Compare su
  immagini, PDF scansionati e fallback OCR; non compare sui documenti nativi
  (sarebbe rumore) né a privacy spenta (non c'è nulla che possa sfuggire).
- Documentato in entrambi i README e in `SECURITY.md`, coi numeri misurati.
- Backlog P0-ter: riconoscimento tollerante alle confusioni tipiche dell'OCR,
  fattibile **senza** aumentare i falsi positivi perché IBAN e codice fiscale
  hanno un checksum — si accetta la variante solo se il controllo torna.
- 161 → 164 test.

## 1.3.1 — Software libero sotto AGPL-3.0, README bilingue

### Licenza: da «source available» ad AGPL-3.0

La licenza non commerciale su misura stava costando più di quanto proteggesse:
GitHub non la riconosce (nessuna corrispondenza SPDX), non si poteva chiamare
open source senza essere smentiti, e gli uffici legali di studi e PMI — cioè
il pubblico a cui l'app serve di più — tendono a bloccare le licenze atipiche.

Mr. Rao è ora **software libero sotto GNU AGPL-3.0**. Uso commerciale incluso.
L'unico obbligo serio scatta per chi lo offre ad altri **attraverso una rete**:
l'articolo 13 impone di rendere disponibile il sorgente della propria versione.
È esattamente la protezione che serviva, senza chiudere l'uso professionale.

Effetto collaterale positivo sulla conformità LGPL: distribuendo il sorgente
completo, l'obbligo di consentire la sostituzione di pystray e python-stdnum è
soddisfatto di conseguenza, non più per analogia.

- `LICENSE` — testo AGPL-3.0 integrale (fonte: gnu.org)
- Avviso di copyright e non-garanzia in `app.py` e `mr_rao/__init__.py`
- Footer e modal informazioni riscritti (obbligo AGPL sulle interfacce interattive)
- Verificata la compatibilità: tutte le dipendenze (MIT, BSD, Apache-2.0,
  MPL-2.0, LGPL, PSF) sono compatibili con AGPL-3.0

### Documentazione

- **README bilingue**: `README.md` in inglese, `README.it.md` in italiano,
  con selettore di lingua in testa a entrambi
- **Screenshot reale** dell'interfaccia in `docs/img/`, prodotto con Chrome
  headless su una conversione vera (non un mockup), più immagine 1280×640
  per l'anteprima social

## 1.3.0 — Audit: privacy dei default, GET sicure, licenze verificabili (161 test)

Release nata da un audit completo. Tutti i punti sotto erano **verificati
eseguendo**, non ipotizzati.

### Privacy — le cartelle di lavoro non finiscono più nel cloud

Su Windows con Known Folder Move la cartella «Documenti» **è** la cartella
OneDrive. `documents_dir()` per giunta metteva OneDrive in cima ai candidati,
quindi le cartelle predefinite della conversione automatica venivano create in
`OneDrive\Documenti\Mr Rao\` — e ogni `.md` convertito, originali inclusi,
finiva sincronizzato sul cloud aziendale. Per un'app il cui footer dice
«100% locale · zero cloud» era la contraddizione più grave del prodotto.

- Nuovo riconoscimento delle radici sincronizzate (OneDrive, Dropbox, Google
  Drive, iCloud, Nextcloud…), per variabile d'ambiente **e** per nome cartella.
- Se «Documenti» risulta sincronizzata si ripiega su `%LOCALAPPDATA%\Mr Rao`,
  e la UI **dice perché**.
- Override esplicito con `MR_RAO_FOLDER_ROOT`.
- Su questa macchina: da `E:\OneDrive - …\Documenti` a `C:\Users\…\Documents`.

### Sicurezza — una GET non modifica più il disco

`GET /api/folders/defaults` creava directory: bastava un `<img src>` su una
pagina qualsiasi per far comparire cartelle nei Documenti dell'utente (il
controllo anti-CSRF si applica solo ai metodi che modificano stato, ed è
giusto così). Ora:

- `GET` è in sola lettura (RFC 9110), `POST` crea e passa dal controllo Origin;
- `GET /api/watch` non crea più nulla — la UI lo interroga **ogni 4 secondi**;
- `create_app()` non crea cartelle all'avvio: chi apre l'app per una conversione
  al volo non si ritrova cartelle nuove nei Documenti.

### Affidabilità

- **Scrittura atomica** dell'hotfolder (file temporaneo + rename): una
  interruzione a metà non lascia più `.md` troncati.
- **`Avvia Mr Rao.bat` non uccide più processi**: il `taskkill /F` poteva
  fermare una conversione in corso proprio mentre scriveva. Se la porta è
  occupata ci pensa `app.py`, che dice chi la occupa e usa la prima libera.
- `browse_folder()` restituisce `None` senza ambiente grafico, come prometteva
  il suo docstring: `tkinter` fallisce alla creazione della finestra, non
  all'import, e quella non era protetta (in container era un 500).

### Licenze — da elenco a mano a documento generato

L'elenco scritto a mano dichiarava **Scrubadub come MIT** (è **Apache-2.0**, che
ha obblighi maggiori) e ometteva **python-stdnum**, che è **LGPL-2.1+**: cioè
proprio la categoria che impone adempimenti. Era stata fatta la cerimonia
completa per pystray e ne era sfuggita una seconda.

- `scripts/gen_third_party.py` **genera** `THIRD_PARTY.md` dai metadati dei
  pacchetti realmente installati; `--check` fallisce se è da rigenerare.
- Tutti e 70 i pacchetti elencati, con in testa i 6 che hanno obblighi oltre
  l'attribuzione.
- `licenses/python-stdnum/` — testo LGPL-2.1 e NOTICE, come per pystray.
- `LICENSE` §5 copre **entrambe** le LGPL e cita l'eccezione di PyInstaller
  (GPLv2 con eccezione: è ciò che rende lecito distribuire `MrRao.exe`).
- Documentato che disinstallando Scrubadub spariscono le dipendenze LGPL e i
  riconoscitori italiani continuano a funzionare — **verificato**.

### Integrità del repository

Metà delle correzioni 1.1.2/1.1.3 esisteva solo sul disco: `HEAD` non era
neppure importabile (`ImportError: cannot import name 'MAX_UPLOAD_MB'`), e il
codice committato aveva ancora la privacy spenta di default. Ora tutto è in
versione controllata.

### Versione

`APP_VERSION` era rimasta a 1.2.1 mentre il changelog arrivava a 1.2.4.

## 1.2.4 — Conformità LGPL pystray completa + footer

### LGPL (pystray) — adempimenti
- Cartella `licenses/pystray/`: COPYING.LGPL, COPYING (GPL), LGPL-3.0.txt, GPL-3.0.txt, NOTICE.txt
- `docs/LGPL_PYSTRAY.md` — come sostituire/aggiornare pystray
- `mr_rao/tray.py` — notice LGPL a runtime e in testa al file
- `LICENSE` §5 — nessuna restrizione aggiuntiva su pystray
- Portable build copia `licenses/`, `LICENSE`, `THIRD_PARTY.md`

### UI
- Footer strutturato: brand, sintesi licenza, link dipendenze, riga dedicata pystray LGPL
- Modal ⓘ aggiornato con checklist conformità LGPL

## 1.2.3 — Trasparenza dipendenze + licenza non commerciale

### UI
- Pulsante **ⓘ** (FAB) e voce footer **Licenza e dipendenze**
- Modal glass con elenco repo, licenze e spiegazione commerciale / LGPL (pystray)
- Link GitHub/siti delle librerie nel footer

### Legale
- `LICENSE` — Mr. Rao Source License (uso non commerciale libero; commerciale su autorizzazione Rao)
- `THIRD_PARTY.md` — MarkItDown (MIT), RapidOCR (Apache-2.0), Flask (BSD), …, pystray (LGPL-3.0)
- Compatibile con le licenze permissive delle dipendenze: la restrizione commerciale vale sul **codice Mr. Rao**, non “chiude” le librerie di terzi

## 1.2.2 — Cartella automatica: Sfoglia… + cartelle predefinite in Documenti

### Cartelle di default (create all'avvio se mancano)
- `Documenti\Mr Rao\Da convertire` — da sorvegliare  
- `Documenti\Mr Rao\Convertiti` — output `.md`  

### UI
- Pulsanti **Sfoglia…** (dialog nativo Windows via tkinter sul server locale)
- Campi percorso in sola lettura + precompilati con i default
- API: `GET /api/folders/defaults`, `POST /api/folders/browse`

## 1.2.1 — UI 2.0 ordinata: tutte le funzioni 1.1.4 + gerarchia a step

### Correzione
La prima passata 1.2.0 aveva **sfoltito troppo** il markup rispetto alla 1.1.4
(tooltip ricchi, microcopy italiana, opzioni complete). Questa release **ripristina
tutta la funzionalità 1.1.4** e la dispone in un flusso pulito.

### Ordine della pagina (anti-disordine)
1. **Carica** — drop zone  
2. **Imposta** — profilo + privacy; avanzate collassate (lettura, privacy granulare, output, multi-file)  
3. **Risultato** — tabs, export, allegati, confronto privacy  
4. **Extra** — sessione | cartella automatica  

### Mantiene (1.1.4)
- Tooltip su profili, metodi, privacy, export, watch, tabs  
- Opzioni: tabelle, scheda informativa, note tecniche, merge, confronto 2 file  
- Privacy granulare + hint se filtro spento  
- Cartella automatica completa (path, done/, avvia/ferma)  
- Design System 2.0 (glass / aurora / float)

### Documentazione
- Backlog P0: SendTo → UI resta prioritario

## 1.2.0 — UI Design System 2.0 + backlog di priorità

### Refactor UI (premium)
- CSS estratto in `static/css/app.css` (design system dedicato)
- **Aurora stage**: orbs animati, griglia vignettata, profondità
- **Glass cards** con blur, bordo gradient, ombre flottanti
- **Hero** con logo flottante, alone conico, wordmark shimmer
- **Drop zone** hero-action: bordo conic-spin al hover, lift, glow
- Control bar essenziale (profilo + privacy); avanzate in pannello collassabile
- Secondari a **griglia** (sessione + cartella automatica affiancati)
- Bottoni con shine sweep, toast glass, tab pill, pulse live sul risultato
- `prefers-reduced-motion` rispettato
- Stessi ID JS: zero regressioni funzionali previste

### Documentazione
- Nuovo [BACKLOG.md](BACKLOG.md) con piano P0–P4 (SendTo→UI prioritario)
- README / ARCHITECTURE aggiornati alla UI 2.0

### Nota
- Menu **Invia a Mr. Rao** resta CLI-only (P0.1 in backlog): non apre ancora l'UI col risultato.
- 1.2.0 aveva semplificato troppo il markup: corretto in **1.2.1**.

## 1.1.4 — Interfaccia comprensibile senza manuale

### Tooltip su ogni comando
Passando il mouse (o arrivandoci con il Tab) su qualunque opzione, pulsante o
scheda compare una spiegazione in italiano semplice: cosa fa, quando serve e
quando conviene lasciarla stare. 37 elementi coperti.

Non si è usato l'attributo `title` del browser: compare dopo un secondo abbondante,
non si può stilare e non appare mai a chi naviga da tastiera. Al suo posto un
singolo riquadro riposizionato, che si apre anche col focus e si chiude con Esc.

### Parole al posto del gergo
- **«Hotfolder (watch)» → «Cartella automatica»**, con una riga che spiega cosa
  fa davvero: sorveglia una cartella e converte da solo i file che ci metti dentro.
- Le lingue OCR non dicono più «(latino)»: era il nome dell'alfabeto, non della
  lingua, e non aggiungeva niente per chi legge. Ora sono «Italiano», «Inglese»,
  «Più lingue insieme».
- «Motore» → «Come leggere il file»; «Forza RapidOCR» → «Forza OCR — scansioni e foto».
- «Filtra dati sensibili» → «Nascondi i dati personali».
- «Frontmatter YAML» → «Scheda informativa in cima»; «Output pulito (LLM)» →
  «Togli le note tecniche»; «Diff privacy» → «Confronto privacy»;
  «Raw / Preview» → «Testo Markdown / Anteprima».
- Gli stati della cartella automatica sono in italiano: `idle` → «non attiva»,
  `Move failed` → «Non riesco a spostare l'originale».

## 1.1.3 — Porta occupata: fine delle versioni fantasma (142 test)

### Il sintomo
Lanciando `Avvia Mr Rao.bat` il browser mostrava una versione **vecchia**
(`v1.0.0`) anche dopo aver aggiornato il codice, senza un solo messaggio di
errore.

### La causa
Werkzeug apre il socket con `SO_REUSEADDR` e su Windows il bind su una porta
già occupata **riesce**: due server restano legati alla stessa porta e le
connessioni finiscono all'uno o all'altro. L'app annunciava "in ascolto sulla
5000", il `.bat` apriva il browser su un URL fisso, e la richiesta veniva
servita dall'altra istanza (una vecchia installazione in `%LOCALAPPDATA%`).

### La correzione
- Nuovo `mr_rao/portcheck.py`: la porta si verifica chiedendo al sistema
  operativo (bind con `SO_EXCLUSIVEADDRUSE`), non con una connect di prova —
  che verso una porta chiusa aspetta il timeout pieno perché il firewall
  scarta il SYN, cioè costerebbe mezzo secondo a ogni avvio.
- All'avvio, se la porta è occupata: si dice **chi** la occupa (interrogando
  `/api/health`: "occupata da Mr. Rao v1.0.0") e si parte sulla prima libera.
- `Avvia Mr Rao.bat` non apre più il browser su `127.0.0.1:5000` fisso: lo
  apre `app.py` sull'indirizzo reale.

## 1.1.2 — Hardening, concorrenza e rifiniture UI (129 test)

### Sicurezza
- **Header `Host` in allow-list** (`MR_RAO_ALLOWED_HOSTS`): un server locale è
  raggiungibile da qualunque pagina aperta nel browser, e un dominio
  dell'attaccante che risolve a `127.0.0.1` leggeva le risposte.
- **Richieste cross-site rifiutate**: `Origin` esterna + metodo che modifica
  stato = 403. Prima un sito qualsiasi poteva avviare un hotfolder con una
  POST multipart (CORS-safelisted, quindi senza preflight).
- **Docker pubblica solo su localhost**: `127.0.0.1:5000:5000`. L'app non ha
  autenticazione, esporla in LAN dev'essere una scelta esplicita.

### Affidabilità
- **Annulla effettivo**: il flag di cancellazione viene letto a ogni confine di
  stadio della pipeline, non solo nel loop OCR delle pagine PDF.
- **Conversioni in parallelo limitate** (`MR_RAO_MAX_WORKERS`, default 2): un
  thread per richiesta permetteva a N upload di avviare N OCR insieme.
- **Job store sfoltito da un sweeper periodico** e con tetto massimo
  (`MR_RAO_MAX_JOBS`): i risultati restavano in RAM finché non arrivava una
  nuova conversione. I job in esecuzione non vengono mai sfrattati.
- **Singleton protetti da lock**: due richieste simultanee costruivano due
  istanze di RapidOCR/MarkItDown.
- **Hotfolder**: `a.pdf` e `a.docx` producevano entrambi `a.md` e il secondo
  sovrascriveva il primo in silenzio; ora diventa `a-docx.md`. La memoria dei
  file già visti non cresce più senza limite.

### Interfaccia
- Il limite di upload lato client segue `MR_RAO_MAX_UPLOAD_MB` invece di essere
  50 fisso, e viene controllata anche la **dimensione totale** dell'invio.
- La cronologia non si duplica più a ogni clic su una voce.
- L'input file viene azzerato subito: riselezionare lo stesso file dopo un
  errore o un annullamento ora funziona.
- Drop zone attivabile da tastiera (Invio / Spazio), come promette il suo
  `role="button"`.
- Lo strip del frontmatter non divora più il testo di un documento che inizia
  con una riga orizzontale `---` (stessa logica in Python e JavaScript).

### Pulizia
- Rimossa `unique_upload_path()` (mai chiamata) e l'import morto in
  `/api/convert/compare`.
- `.gitignore` non nasconde più `MrRao.spec` dietro la regola `*.spec`: il file
  descrive il build portable e ora è committabile (finora restava fuori da git
  senza che nessuno se ne accorgesse).

## 1.1.1 — Correzioni di regressione (98 test)

### Bug corretti
- **Profilo "Solo OCR" su PDF**: `engine=rapidocr` finiva nel ramo immagine
  (`cannot identify image file`) perché il ramo `.pdf` era codice morto. Le
  scansioni PDF — il caso d'uso del profilo — fallivano sempre.
- **`.eml` che contaminava il batch**: il parser riscriveva `opts.privacy`
  sull'oggetto del chiamante, ignorando una scelta esplicita di "nessuna
  redazione" e propagandola a tutti i file successivi di batch e hotfolder.
  La policy privacy ora si decide in un unico punto (il confine API/CLI).
- **Job appesi**: un'eccezione nel thread worker lasciava lo stato a `running`
  per sempre e la UI pollava all'infinito. Ora il job passa a `error`.
- **Errori HTTP in HTML**: il 413 (e 404/405/500 sotto `/api/`) tornava una
  pagina HTML che il frontend non sa parsare. Ora sono JSON, con il limite
  reale in MB e la precisazione che vale per l'intero invio, non per file.
- **Frontmatter non valido**: `redactions: 5` seguito da chiavi indentate non
  è YAML. Ora è una mappa annidata e i valori sono quotati, quindi anche un
  nome file con `:` o `"` produce un blocco parsabile.
- **Privacy OFF di default via API**: chi chiamava `/api/convert/sync` senza
  `privacy_filter` riceveva testo in chiaro. Il default è ora fail-safe e
  coerente con la CLI.
- **Falsi positivi che rovinavano il testo**: `protocollo 0123456789` non è
  più un telefono, `Versione 1.10` non è più un importo (e non si mangia più
  lo spazio successivo), e gli IBAN sono validati con il mod-97 ISO 13616.
- **Immagini OCR fuori posto**: le pagine rasterizzate finivano in `uploads/`
  accanto all'eseguibile (cartella potenzialmente in sola lettura, residui in
  caso di crash). Ora stanno in una directory temporanea di sistema.

### Test
- `tests/test_dispatch.py`: matrice profilo × formato e isolamento delle opzioni
- Regressioni aggiunte su privacy, errori API e validità YAML del frontmatter
- 23 → 98 test

## 1.1.0 — Feature pack + portable (build verificata)

### Build portable (eseguita e testata)
- `scripts/build_portable.bat` riparato (encoding cmd) e eseguito con successo
- Output: `dist/MrRao-Portable/` (~390 MB) con `app/MrRao.exe` + dipendenze
- Smoke test: `MrRao.exe health` e `MrRao.exe convert` OK
- Fix crash console Windows: niente freccia Unicode in `app.py` (cp1252)
- CLI gestita **prima** dell'avvio server (health/convert/file drop)

### Icone
- Lockup **Mr** + **RAO** (RAO grande, Mr leggibile, no clipping)
- `mr-rao.ico` multi-size + shortcut Desktop automatico

### Feature
- System tray (pystray)
- Profili preset (email legali, fatture, solo OCR, LLM-ready, no privacy)
- Diff privacy (prima/dopo + highlight segnaposto)
- Allegati `.eml` scaricabili dall'UI
- Hotfolder watch da UI (`/api/watch`)
- Confronto 2 file (Documento A / B)
- Drag-out `.md` (Chrome/Edge) dal bottone/output
- Menu contestuale Windows + Invia a
- Export `.md` / `.txt` / copia pulita LLM
- Multi-file + merge batch, progress, annulla
- Preview Raw/Markdown, cronologia sessione, Ctrl+V immagine
- Privacy IT (email, telefoni, CF, IBAN, P.IVA, nomi) + report
- CLI `convert` / `watch` / `health`
- Tabelle PDF, frontmatter YAML, OCR RapidOCR offline
- Parser `.eml` thread IT/EN + BeautifulSoup4

### Portable install
- Sul target: **nessun Python, pip o git**
- `Installa Mr Rao.bat` → `%LOCALAPPDATA%\MrRao` + Desktop + shell
- Docs: `docs/PORTABLE.md`

## 1.0.0 — Mr. Rao

### Brand
- Rebrand completo da MarkItDown / RAOmark a **Mr. Rao**
- Logo SVG, favicon SVG, bat, README, footer

### Fix
- Aggiunto **beautifulsoup4** a requirements e installer
- Label motore: RapidOCR (non piu PaddleOCR)
- Font system-ui (offline reale)
- Upload con UUID (no collisioni)
- `debug` da env `MR_RAO_DEBUG`
- Toggle privacy HTML valido
- Errori 500 non espongono stack al client
- Thread email: match piu vicino all'inizio, depth limit

### Qualita
- Architettura a moduli `mr_rao/`
- Healthcheck `/api/health`
- Job async con progress + cancel
- Test pytest + `scripts/quality_gate.*`
- Docker / compose
