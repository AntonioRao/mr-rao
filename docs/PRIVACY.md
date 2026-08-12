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

**I segnaposto sono numerati, e lo sono di serie.** Dalla 1.20.0 ogni valore
distinto riceve un numero — `{{NAME_1}}`, `{{NAME_2}}` — e lo stesso valore
ripetuto riceve sempre lo stesso. Senza numeri il documento redatto perde il
senso: *«{{NAME}} ha citato {{NAME}} davanti a {{NAME}}»* non si legge, e un
modello linguistico non ci può ragionare sopra.

Nella tabella qui sotto i segnaposto sono scritti nella **forma base**, senza
numero, perché è quella che identifica il tipo. Nel documento vero arrivano
col suffisso, a meno che non si tolga la spunta a «Numera i segnaposto» —
allora l'uscita torna identica alla 1.19.

Il numero non è una chiave: vale **dentro un documento e basta**. Non esiste
nessuna mappa da numero a valore, perché non viene mai costruita, e lo stesso
nome in un altro documento riceve un numero diverso. Un numero stabile fra
documenti sarebbe un identificatore persistente, cioè un dato personale nuovo
inventato da noi.

| Tipo | Segnaposto | Come viene deciso |
|------|-----------|-------------------|
| Email | `{{EMAIL}}` | Forma dell'indirizzo, comprese quelle offuscate (`[at]`, `chiocciola`, `punto`) e la **chiocciola spaziata** (`mario @ esempio.it`). Su quest'ultima l'ultimo pezzo del dominio dev'essere di lettere: senza quel vincolo, `10 @ 4.50` su una fattura diventerebbe un indirizzo |
| Indirizzi web | `{{URL}}` | Schema esplicito — `http`, `https`, `ftp`, `ftps` — oppure `www.`. Non basta un `nome.it` in mezzo al testo |
| Telefoni | `{{PHONE}}` | Prefisso internazionale **qualunque** (`+39`, `+44`, `0033`: da una a tre cifre dopo `+` o `00`), cellulari italiani `3xx`, parola di contesto (`cell`, `tel`, `fax`), oppure fisso con separatori. La **barra** (`011/7323929`) vale solo con la parola di contatto o il prefisso internazionale davanti |
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
| | | Anche i **codici corti**: PIN, PUK, CVV, CVC, codice di sicurezza, OTP, codice di sblocco. Da tre a otto cifre — sopra le otto non è più un PIN, è un protocollo — e serve l'etichetta, che è ciò che li rende sicuri: quelle parole in un documento non hanno altro significato |
| | | E la **frase di recupero** (`frase mnemonica`, `seed phrase`): da 12 a 24 parole, lo standard BIP-39. Sta a parte perché è l'unico segreto fatto di parole separate da spazi, e col valore generico — che si ferma al primo spazio — ne usciva **una sola sostituita su dodici**, con il rapporto che diceva «1 segreto» e la frase ancora utilizzabile |
| Documenti d'identità | `{{DOC_ID}}` | Carta d'identità elettronica, patente, passaporto. **Serve il tipo di documento scritto vicino**, vedi sotto |
| Riferimenti catastali | `{{CATASTO}}` | **Pacchetto «Atti e pratiche», spento di default.** Foglio **e** particella insieme, subalterno facoltativo. Il foglio da solo è la pagina di una relazione |
| Numeri di pratica | `{{PRATICA}}` | **Pacchetto «Atti e pratiche», spento di default.** R.G., protocollo, repertorio, raccolta, cronologico. L'etichetta è obbligatoria e **resta nel testo**: sparisce il numero, resta «Prot. n.». Servono almeno due cifre, oppure l'anno accanto — «Protocollo n. 5» di una convenzione non è una pratica. Il suffisso di registro (`/P`, `/CU`) resta anche lui: dice quale registro, non quale fascicolo |
| Targhe di veicoli | `{{TARGA}}` | **Pacchetto «Atti e pratiche», spento di default.** `AB 123 CD`, con o senza separatori. Il vincolo non è il maiuscolo ma la **coerenza**: tutto maiuscolo o tutto minuscolo, mai misto — `Ab 123 cD` non è una targa, è un refuso o un'altra cosa. I, O, Q e U non esistono sulle targhe e vengono rifiutate. La forma da ciclomotore (`AB 12345`) richiede «targa» o «targato» davanti |
| Date di nascita | `{{DATE}}` | **Spento di default.** Solo con contesto di nascita accanto |
| Importi | `{{AMOUNT}}` | **Spento di default.** Valuta, migliaia o contesto contabile |
| Termini tuoi | `{{TERM}}` | L'elenco «nascondi sempre» scritto da chi converte |

### Due dati che Mr. Rao trova e non toglie mai: età e sesso

Non hanno un segnaposto, e non è una dimenticanza.

Sono **quasi-identificatori**: «45 anni» da solo non identifica nessuno, ma
insieme a un comune piccolo e a una professione sì — ed è esattamente così che
si de-anonimizza un archivio. Toglierli, però, non protegge nessuno di più e
rende il documento inservibile per l'unico uso per cui era stato preparato: chi
lavora su una cartella clinica, su una statistica del personale o su una
perizia sta chiedendo **proprio quei due dati**.

Lasciarli in silenzio, però, vorrebbe dire che chi rilegge non sa che ci sono.
Quindi la terza via, che qui è la sola giusta: **compaiono nel rapporto**, nel
blocco `detected_not_replaced`, separato dalle sostituzioni perché sommare ciò
che si è tolto con ciò che si è lasciato darebbe un totale che non vuol dire
niente. «Lasciate in chiaro 3 età, apposta» è un'informazione che un DPO può
usare per decidere; il silenzio no.

Si riconoscono solo dove **il contesto è una dichiarazione**: `di anni 45`,
`45 anni di età`, `45 anni d'ETÀ`, `età: 45`, `Eta': 45`, `d' anni 78`,
`45enne`, `sesso: F`, `sesso: f`, `genere femminile`. Il
`45 anni` nudo non si guarda, ed è dichiarato: è quasi sempre una durata
(«dopo 45 anni di servizio»), e prenderlo riempirebbe di segnalazioni ogni
relazione aziendale.

L'interruttore «Età e sesso» decide **se guardare**, e non ha un secondo
stato: acceso li segnala, spento non li cerca. Spegnerlo non rende il documento
più pulito, lo rende più silenzioso. Chi li vuole togliere davvero ha già
l'elenco **«nascondi sempre»**, che li toglie — nessuna capacità è perduta, ed
è questo a rendere onesta la scelta di non offrire la sostituzione.

### «Segnala anziché sostituisci»: il terzo stato, e non riguarda solo questi due

Età e sesso sono il caso in cui quel comportamento è **obbligato**. Ma dalla
1.20.0 lo si può chiedere per **ventisei categorie** — praticamente tutte
quelle che il motore riconosce — e la scelta è per categoria, non per famiglia.

Le tre combinazioni, e sono tre cose diverse:

| interruttore | categoria in «segnala» | cosa succede |
|---|---|---|
| acceso | no | **sostituisce** — arriva il segnaposto |
| acceso | sì | **trova e lascia dov'era**, e lo dice nel rapporto |
| spento | — | **non cerca**, e non lascia traccia |

La riga di mezzo è quella che prima non c'era, e serve a chi il dato lo vuole
leggere: gli importi che un modello deve confrontare, l'età in una cartella
clinica. Il valore vero non è nel testo, è nel rapporto — *«ho lasciato in
chiaro 3 importi, apposta»* è un'informazione che un DPO può usare per
decidere; il silenzio no. Un riconoscitore **spento** non lascia traccia, e
chi rilegge non ha modo di sapere se lì dentro non c'era niente o se abbiamo
guardato dall'altra parte.

L'unica categoria che resta fuori è **«termini tuoi»**, ed è una decisione:
quell'elenco è ciò che l'utente ha chiesto esplicitamente di proteggere, e
segnalarlo invece di sostituirlo vorrebbe dire disobbedire a una richiesta
esplicita.

Nell'interfaccia il conto è **triplo**, e i tre numeri rispondono a tre
domande diverse:

```
🛡️ 12 redazioni · ⚠️ 2 da controllare · 👁 3 in chiaro
```

L'ultimo è questa sezione: quello che il motore ha trovato e ha lasciato lì
per scelta di chi converte. Passandoci sopra si leggono le categorie, coi nomi
che si leggono e non con quelli con cui il codice parla a sé stesso. Sommarlo
agli altri due darebbe un totale che non vuol dire niente, ed è il motivo per
cui sono tre numeri e non uno.

Nel documento la stessa informazione viaggia col frontmatter, nel blocco
`detected_not_replaced:` — separato da `redactions:`. È l'unica parte del
rapporto che resta attaccata al file: chi lo riceve fra sei mesi non ha la
richiesta HTTP.

### Il pacchetto anglosassone

Arrivato con la 1.8.0 e rimasto fuori da questa tabella fino alla 1.11 — un
buco che oggi non può ripetersi, perché `scripts/check_docs.py` confronta i
segnaposto che il motore sa emettere con quelli scritti qui e **fallisce** se
ne trova uno solo di troppo.

| Tipo | Segnaposto | Come viene deciso |
|------|-----------|-------------------|
| NHS number (UK) | `{{NHS_NUMBER}}` | **Mod-11** *e* la parola «NHS» accanto |
| Routing bancario ABA (US) | `{{ROUTING_NUMBER}}` | Checksum pesato **3-7-1**, gli intervalli di prefisso in uso, *e* una parola di contesto |
| SIN (CA) | `{{SIN}}` | **Luhn** *e* una parola di contesto |
| ABN (AU) | `{{ABN}}` | **Mod-89** (con la sottrazione di 1 alla prima cifra) *e* la sigla accanto |
| TFN (AU) | `{{TFN}}` | **Mod-11** pesato *e* la sigla accanto |
| Zona a lettura ottica dei passaporti | `{{MRZ}}` | Cifra di controllo **ICAO 9303** su numero del documento, nascita o scadenza. **L'unico che decide da solo** |
| National Insurance number (UK) | `{{NINO}}` | **Nessun checksum**: struttura, più i prefissi che l'HMRC non assegna |
| SSN (US) | `{{SSN}}` | **Nessun checksum**: la forma trattinata 3-2-4, più le esclusioni pubblicate dalla SSA. Nove cifre attaccate non si toccano |
| ITIN (US) | `{{ITIN}}` | **Nessun checksum**: struttura e intervalli IRS |
| Codice postale britannico | `{{POSTCODE}}` | **Nessun checksum**, come ogni codice postale: struttura *e* una parola di recapito accanto, quando non sta già dentro un indirizzo completo |
| Indirizzi anglosassoni | `{{ADDRESS}}` | Il **civico** davanti, almeno una parola in mezzo, e un tipo di via in coda (`Street`, `Road`, `Lane`, `Way`, …), con CAP britannico o ZIP facoltativo |
| Nomi anglosassoni | `{{NAME}}` | **Nessun elenco**: solo dove il testo dichiara che è una persona — titolo davanti, formula di apertura o di chiusura, indirizzo di posta accanto |

**La divisione da leggere non è quella fra chi ha un conto e chi no.** Il
checksum, da solo, non basta quasi mai: il mod-11 dell'NHS lascia passare
circa una sequenza di dieci cifre su nove, e da solo redigerebbe numeri di
fattura. **Cinque di questi sei riconoscitori aritmetici non sostituiscono
niente senza una parola di contesto vicina** — NHS, routing ABA, SIN, ABN e
TFN. Il validatore riduce il rumore, il contesto lo azzera.

L'unico che decide da solo è la **riga MRZ**, e non perché sia più fortunato:
perché la forma è irripetibile. Solo maiuscole, cifre e riempitivi, con almeno
un doppio `<` — nessun'altra riga di testo assomiglia a quella. Vale la pena
proprio lì, perché una MRZ contiene cognome, nome, cittadinanza, data di
nascita, sesso e scadenza tutti insieme.

Una precisazione sulla MRZ, perché è il tipo di dettaglio che sembra un
dettaglio: **la cifra composita di fine riga non si usa**, di proposito. Si
calcola su pezzi **non contigui**, e darle in pasto la riga intera la fa
fallire sempre. I campi controllati sono tre — numero del documento, data di
nascita, scadenza — e ne basta uno che torni.

E dove il conto non c'è del tutto (NINO, SSN, ITIN) resta solo la struttura,
più le esclusioni pubblicate: lì il rischio di prendere un codice qualsiasi è
più alto, ed è la stessa ragione per cui i documenti d'identità italiani
pretendono il contesto.

**Una parola su un numero italiano scambiato per americano.** `Tel. 078-05-1120`
ha esattamente la forma 3-2-4 di un SSN, e il pacchetto anglosassone è acceso
di serie: un notaio italiano si vedeva contare come «SSN» il centralino dello
studio. Il dato spariva comunque — il passo dei telefoni gira dopo e lo prende
—, ma **il rapporto sbagliava il tipo**, e un rapporto che sbaglia il tipo non
serve a rispondere a chi chiede *cosa* c'era nel file. Adesso una parola di
contatto davanti fa lasciare stare quel numero al riconoscitore del SSN.

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

## I nomi di persona: nove segnali, tutti con un riscontro

Un elenco di nomi non è mai completo, e affidarsi solo a quello lascia
passare tutti i cognomi non comuni. Valgono quindi anche le regole di
contesto. `_scrub_names` le esegue in quest'ordine, dal segnale più forte al
più debole:

1. **Titolo professionale davanti** — Dott., Ing., Geom., Avv., Sig.
2. **Ruolo, due punti, cognome in maiuscolo** — `Il Ministro: GIORGETTI`.
   È la firma degli atti pubblici italiani.
3. **Nome prima di un indirizzo di posta** — `Tizio Caio <t.caio@x.it>`.
   È il caso più frequente nelle email.
4. **Nome dopo un indirizzo di posta** — `t.caio@x.it (Tizio Caio)`.
5. **Nome accanto a un codice fiscale valido** — `Elicio Nazar CF
   MNTCRL58D07H163B`. La finestra è stretta apposta: fra il nome e il codice
   ci sta l'etichetta e nient'altro, sulla stessa riga.
6. **Ruolo dichiarato** — `il cliente Mario Rossi`, `il ricorrente …`.
   Pretende **due** parole.
7. **Campo di modulo** — `Nome: Mario Rossi`, `COGNOME= …`. Qui ne basta una:
   l'etichetta non lascia dubbi su cosa venga dopo.
8. **Formula di chiusura** — `Cordiali saluti, Esposito`. È l'unico posto in
   cui un cognome da solo vale come prova.
9. **Nome e cognome adiacenti**, riconosciuti negli elenchi. Quanti riscontri
   servano — uno o due — lo decide la soglia prosa/modulo, più sotto.

L'ordine non è decorativo: i primi otto sono regole di **contesto**, e non
hanno bisogno che il nome sia in un elenco. Il nono è l'unico che si appoggia
agli elenchi, ed è per questo che è l'ultimo.

C'è poi un decimo caso che **non sostituisce mai**: una parola sola che
risulta negli elenchi, senza niente intorno, diventa un **sospetto**. Sotto le
quattro lettere non si guarda nemmeno — «Re» e «Rao» sono cognomi italiani
veri e su un modello Redditi in bianco venivano sostituiti.

Tutte chiedono **un riscontro**, di elenco o di contesto. Ce n'era una che non
lo chiedeva, ed è stata tolta.

### Prosa o modulo: quanti riscontri chiede il nono segnale

Sul segnale più debole la stessa regola ha **segno opposto** a seconda del
documento, e non è un'opinione. Su una lettera, due parole maiuscole di cui
una risulta negli elenchi sono quasi sempre una persona; su un modulo sono
quasi sempre l'etichetta di un campo — «Imposta Lorda», «Quadro RN».

Misurato: pretendere due riscontri toglie **2 739** sostituzioni sbagliate sui
moduli amministrativi in bianco e costa **609** nomi su 1 500 email vere. Non
esiste un valore giusto per entrambi, quindi non se ne sceglie uno: si guarda
il documento.

**Il segnale che decide sta nel PDF, non nel testo.** Le caselle di un modulo
sono righe e rettangoli vettoriali: sopravvivono alla lettura del file e
muoiono nella conversione, quindi si contano lì. La soglia è **0,5 elementi
vettoriali ogni 100 caratteri**, e sta nel vuoto fra due popolazioni misurate,
non a ridosso di una: le istruzioni dell'Agenzia delle Entrate — libretti in
prosa — stanno a 0,2, i modelli dello stesso ente a 0,7, i moduli fiscali
statunitensi fra 3,7 e 9,8.

Per gli altri formati non serve contare: `.eml`, `.txt`, `.md`, `.rtf`,
`.docx`, `.doc`, `.odt`, `.pptx` e `.ppt` sono **prosa**; `.xlsx`, `.xls`,
`.csv`, `.json` e `.xml` sono **moduli**.

Su una scansione la risposta è **«non lo so»**, ed è un terzo stato vero:
contare vettori su un'immagine darebbe zero, e zero verrebbe letto come
«prosa» — la risposta giusta per il motivo sbagliato. In quel caso si sceglie
la prudenza sul documento, cioè il sospetto, e non sul richiamo: un falso
positivo si vede rileggendo l'uscita, un nome lasciato in chiaro no.

Nell'interfaccia lo si può contraddire a mano. Dalla riga di comando no: lì
vale sempre quello che il programma deduce.

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
dato in tre cornici ciascuno, e i nomi in **quattro** livelli di prova —
titolo davanti, firma, accanto a un'email, nome+cognome — più il caso
**nudo**, che di prova non ne ha nessuna e sta lì apposta: è quello che
misura il limite dichiarato più avanti, non un quinto livello.

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

La stessa domanda girata sui **dieci riconoscitori anglosassoni** — NHS,
National Insurance, SSN, ITIN, routing ABA, SIN, ABN, TFN, tutti e sei i
formati di codice postale britannico, MRZ — più i documenti d'identità
italiani e le coordinate bancarie non-IBAN, non ha trovato niente:
`scripts/bench_varieta_en.py`, venti tipi in tutto, tutti al 100%.

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
da ridistribuire. Il test si salta dicendolo, ma i **quattro** test che provano il
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
accanto al conteggio: **«🛡️ 3 redazioni · ⚠️ 2 da controllare»**. Se qualcosa
è stato lasciato in chiaro apposta, accanto compare anche il terzo conto —
`👁 N in chiaro`, spiegato più sopra.

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

La risposta API porta **tre conti separati**, e tenerli separati è il punto:

| campo | cosa dice |
|---|---|
| `counts`, `total` | cosa è stato **tolto** |
| `detected`, `detected_counts`, `detected_total` | cosa è stato trovato e **lasciato apposta** — età, sesso, e le categorie messe in «segnala» |
| `suspects`, `suspects_total` | cosa il motore **non ha saputo decidere** |

Sommarli darebbe un totale che non vuol dire niente. L'interfaccia li mostra
tutti e tre accanto al risultato, e la scheda **«Confronto privacy»** mostra
il testo prima e dopo. Quella scheda è il controllo che conta: è lì che si
vede cosa è stato tolto e, soprattutto, cosa è sfuggito — perché una perdita
silenziosa, per definizione, in nessuno dei tre numeri compare.

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
- **La redazione PDF→PDF non tratta tutte le pagine, e lo dichiara pagina per
  pagina.** Un PDF che entra e un PDF che esce è un percorso a parte
  (`mr_rao/redazione_pdf.py`), e ha limiti suoi:
  - **le scansioni si rifiutano**, e il rifiuto è per pagina, non per
    documento. Senza testo estraibile non ci sono glifi da togliere:
    disegnarci sopra dei rettangoli sembrerebbe una redazione e non lo
    sarebbe. Una pagina scansionata infilata in mezzo a pagine digitali —
    l'allegato firmato a mano — è il caso tipico, e prima usciva contata fra
    quelle trattate. Una pagina **bianca** invece non è un allarme: non ha
    niente da togliere, e resta silenziosa;
  - **le pagine in ripiego non sono redatte.** Quando il testo estratto non si
    ritrova nel flusso di contenuto, o un tratto non si riconduce a nessun
    glifo, la pagina esce **com'era**. Compaiono in `pagine_in_ripiego` con il
    motivo accanto, e il pannello le mostra **sempre**, anche quando sono
    zero, nella tinta dei sospetti — che qui vuol dire «tocca a te guardare».
    Chiamarle redatte sarebbe il modo peggiore di sbagliare;
  - restano fuori, dichiarati, gli operatori di testo `'` e `"`.

  **Il PDF segue le stesse opzioni del Markdown, profilo compreso** — e dalla
  1.24.0 anche il profilo. Prima no: le rotte del PDF costruivano le opzioni
  senza guardare il profilo scelto, quindi la stessa pagina, con le stesse
  caselle, poteva produrre un Markdown redatto in un modo e un PDF redatto in
  un altro. La differenza si vedeva solo aprendo i due file uno accanto
  all'altro, che è il posto in cui nessuno guarda. Ora la regola sta in un
  punto solo (`_privacy_dalla_richiesta`), e ha un nome proprio perché una
  rotta nuova non possa ripetere il difetto.

  **Le annotazioni e i campi modulo invece ci sono, dalla 1.24.0.** Prima no,
  e il difetto era grosso: quel testo non sta nel flusso della pagina, quindi
  usciva intero da un file chiamato `-redatto.pdf` — un codice fiscale ancora
  leggibile dentro un documento il cui nome dice il contrario. Insieme al
  valore viene buttato l'aspetto memorizzato del campo (`/AP`) e si accende
  `NeedAppearances`: senza, sullo schermo resterebbe disegnato il nome di
  prima, con il dato tolto solo sotto.
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
