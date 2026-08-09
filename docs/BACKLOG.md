# Backlog & piano di priorità — Mr. Rao

Lo stato delle voci vale alla **1.16.0**. La fonte di verità resta git e il
[changelog](CHANGELOG.md): se una riga qui dice DONE e il codice dice altro,
ha ragione il codice.

## Principio

> Meno ingressi confusi, più coerenza.  
> Non aggiungere feature finché i journey OS ↔ UI non sono prevedibili.

---

## P0 — Coerenza UX / OS (impatto alto)

**Riscritta il 2026-08-07, dopo aver sentito chi lo usa.** Diceva: «tasto
destro → apri la UI col risultato, perché l'utente si aspetta il browser».
Era un'assunzione, e la persona che lo usa tutti i giorni ha detto il
contrario: *«mi piace il tasto destro che genera direttamente il documento
anonimizzato, è semplice ed efficace»*. Ha ragione — per il caso più
frequente (voglio il testo, adesso) aprire un browser è un passaggio in più,
non uno in meno.

Il difetto vero è un altro, e va nella direzione opposta: **l'esito
scompare**.

| ID | Item | Perché | Stato |
|----|------|--------|--------|
| P0.1 | **L'esito di una conversione da tasto destro non deve sparire quando c'è qualcosa da guardare** | Il `.bat` passa ora `--attendi`: la finestra si ferma se qualcosa è stato tolto o segnalato, e si chiude da sola su un documento pulito | **DONE** (1.7.2) |
| P0.2 | **La CLI deve stampare anche i sospetti**, non solo il conteggio delle redazioni | Stampa tipo e campione mascherato di ognuno, con il perché. Maschera con `*` e non col pallino: in cp1252 sarebbe diventato un punto interrogativo, cioè il carattere che segnala un guasto | **DONE** (1.7.2) |
| P0.3 | Se server già su: riusa porta, non aprire seconda istanza cieca | Evita porte occupate / finestre morte | TODO (parziale: portcheck) |
| P0.4 | Feedback visibile su fallimento shell (message box o log file) | Shell che flasha e sparisce = zero fiducia | **DONE** (1.11) — un fallimento lascia una traccia in `%LOCALAPPDATA%`, e il menu contestuale del portable passa per `cmd /c "... || pause"`, così la finestra resta anche se il processo muore prima di Python. Scelto il file e non una finestra di messaggio: una MessageBox ha lo stesso limite di `--attendi` ed è bloccante. **Contiene data, estensione, dimensione e motivo; non il nome del documento, il percorso né il contenuto** — un registro, su questo programma, è esso stesso un dato. Una riga sola riscritta ogni volta; `MR_RAO_TRACCIA=0` lo spegne |

**Perché P0.1 e P0.2 contano più di quanto sembri.** La FAQ dice che il
confronto prima/dopo «è il controllo che conta», e `PRIVACY.md` che «zero
redazioni non significa documento pulito». Il percorso più veloce e più
comodo — quello che la gente userà davvero — **salta entrambe le cose in
silenzio**. Non è un problema di comodità: è il prodotto che contraddice il
proprio documento.

**Design proposto**

1. Documento pulito (zero redazioni, zero sospetti) → la finestra si chiude
   come adesso: non c'è niente da guardare, e fermarsi per dire «niente»
   insegna a chiudere senza leggere.
2. Qualcosa tolto **o** qualcosa da controllare → si ferma, mostra il
   conteggio, i sospetti mascherati e il percorso del `.md`, e ricorda che
   il confronto si apre nell'app.
3. Il file continua a comparire accanto all'originale: quello non si tocca.

---

## P1 — UX prodotto (dopo P0)

| ID | Item | Perché | Stato |
|----|------|--------|--------|
| P1.1 | **UI Design System 2.0** (glass, aurora, float, glow) | Schermata disordinata post-feature dump | **DONE** |
| P1.2 | Gerarchia a step 1–4: Carica → Imposta → Risultato → Extra | Riduce carico cognitivo | **DONE** (1.2.1) |
| P1.2b | Ripristino funzionalità/tooltip 1.1.4 sul layout 2.0 (senza snellire il prodotto) | 1.2.0 aveva sfoltito troppo | **DONE** (1.2.1) |
| P1.3 | Empty states e microcopy coerenti | Professionalità | **DONE** |
| P1.4 | Preview Markdown più fedele (liste, tabelle) | Anteprima debole | **DONE** — renderer proprio in `static/js/markdown.js`: liste annidate, elenchi numerati, tabelle con allineamenti, blocchi di codice, citazioni. Scritto in casa e non preso da una libreria anche per una ragione di sostanza: un renderer generico rende le immagini remote, e un `<img src>` verso l'esterno sarebbe una chiamata di rete partita dal documento in lavorazione. Qui le immagini restano una didascalia, e la CSP `img-src 'self' data: blob:` fa da seconda serratura |
| P1.5 | Mobile / narrow viewport polish | Uso da tablet | **DONE** (1.12) — solo CSS. Il difetto più grave: a 375 px la pagina era larga **635**, cioè 260 px fuori schermo e irraggiungibili perché tagliati. **Il metodo prima del risultato**: `overflow-x: hidden` sul body *nasconde* lo scorrimento invece di risolverlo, e falsa qualunque verifica — ogni misura è stata presa azzerandolo temporaneamente, altrimenti si misura il tappeto e non la polvere. Trovati per la stessa strada: nome allegato da 480 px in un pulsante da 284, campi del percorso a 61 px quando ne servono 345, i due riquadri dei termini **senza nessuna regola CSS**, aree di tocco da 19,6 px (ora sopra il minimo 24×24 di WCAG 2.2 SC 2.5.8). Verificato a 320, 375, 560, 767, 768, 805, 1024, 1280 e 812×375. Restano due cose che il CSS non può risolvere: **P4.6** e **P4.7** |
| P1.8 | **Elenco di termini sempre / mai da sostituire, configurabile dall'interfaccia** | Il motore decide con regole generali; ogni studio ha però nomi propri ricorrenti (clienti, controparti) e parole che non vanno mai toccate (denominazioni interne). Oggi l'unica leva è spegnere un riconoscitore intero. Vale come [parità GUI](../README.it.md): configurabile lì, non solo da riga di comando | **DONE** — due caselle nel pannello privacy, `--sempre`/`--mai` da riga di comando. «Mai» non è l'opposto di «sempre»: protegge da **tutti** i riconoscitori, vince su «sempre», e non lascia nemmeno un sospetto. Le liste restano scritte fra una conversione e l'altra nel `localStorage` del browser — l'unica cosa che Mr. Rao salva |

---

## P2 — Affidabilità & qualità

| ID | Item | Perché | Stato |
|----|------|--------|--------|
| P2.1 | Test E2E portable (health + convert) | Il build avvia l'eseguibile, interroga `/api/health`, converte **.docx, .xlsx e .pptx** — uno per libreria opzionale — e confronta l'icona: se qualcosa non torna, **respinge il pacchetto** | **DONE in locale** (1.4.2, esteso ai tre formati nella 1.7.0) |
| P2.2 | Test job cancel / watch start-stop | Race conditions | **DONE** (1.11) — 9 test, e hanno trovato **tre difetti veri**: un avanzamento resuscitava un lavoro annullato (la barra ripartiva dopo Annulla), riavviare la sorveglianza durante una conversione lasciava due thread per sempre (segnale di stop condiviso), un annullamento in coda veniva sovrascritto dal worker. Restano segnalati due casi senza test deterministico: due `POST /api/watch` simultanei, e i contatori scritti dal giro orfano prima di morire |
| P2.3 | Test shell integration | Il passaggio `-Prova` di `mr_rao_shell.ps1` stampa cosa scriverebbe e si ferma: da li' l'integrazione OS e' verificabile senza sporcare registro e Desktop di chi lancia i test | **DONE** (1.7.0) |
| P2.4 | Gate pre-commit automatico (hook git opzionale) | Disciplina | **DONE** (1.11) — `scripts/install_hooks.py --install/--status/--uninstall`; punta `core.hooksPath` a `.githooks/` invece di copiare, così non resta in giro una copia vecchia. Esegue solo compileall + import: mezzo secondo contro i 18 del gate intero, perché un hook lento non viene tolto, viene aggirato con `--no-verify` |
| P2.9 | **Build del portable in CI**, non solo in locale | Workflow `portable.yml`: parte senza venv, quindi il pacchetto non può ereditare niente dalla macchina di sviluppo. Non a ogni commit — quando cambia qualcosa che può romperlo, una volta a settimana per le derive a monte, e a mano prima di una release | **DONE** (1.7.0) |

---

## P2-ter — Irrobustimento del server locale (1.7.0)

Numerate `S.x` e non `P2.x`: la prima stesura di questa sezione riusava
P2.5–P2.8, che **P2-bis aveva già presi**, e per qualche ora «P2.7» ha
voluto dire due cose diverse, in due stati diversi. Un elenco in cui non si
può citare un identificativo non serve a niente.

| ID | Item | Stato |
|----|------|--------|
| S.1 | `Sec-Fetch-Site` rifiutato su mutazioni — copre il ramo in cui `Origin` manca, e i vicini di porta su localhost | **DONE** (1.7.0) |
| S.2 | Allow-list host reale anche con `MR_RAO_HOST=0.0.0.0`, invece di `*` | **DONE** (1.7.0) |
| S.3 | `SECRET_KEY` casuale in memoria invece di una costante pubblicata | **DONE** (1.7.0) |
| S.4 | `frame-ancestors 'none'`, `nosniff`, `no-referrer` | **DONE** (1.7.0) |
| S.5 | Tetto di tempo sull'OCR, con troncamento dichiarato nel documento | **DONE** (1.7.0) |
| S.6 | ReDoS quadratico nella pulizia del testo (`<!--` mai chiusi): 3,2 s su 80 mila caratteri, con un tetto d'invio di 50 MB | **DONE** (1.7.0) |
| S.7 | Triage dei 16 alert CodeQL: 4 corretti, 12 chiusi con la motivazione scritta **anche nel codice**, non solo nella scheda Security | **DONE** (1.7.0) |

### Valutati e scartati, con la ragione

| Proposta | Perché no |
|----------|-----------|
| Path policy sui percorsi del monitoraggio (allow-list, confinamento sotto la root dell'app) | Romperebbe la funzione: la hotfolder deve poter stare nei Documenti o su un disco di rete, e c'è un selettore nativo apposta. Il danno massimo è qualche cartella e dei `.md` nuovi — `output_path_for` non sovrascrive mai |
| Token CSRF double-submit | Con `Host` + `Sec-Fetch-Site` + `Origin` non gli resta niente da intercettare; aggiungerebbe stato e un modo nuovo di fallire su un'app monoutente |
| Sandbox dei parser (processo a diritti ridotti) | Una seria su Windows (job object, AppContainer) è un progetto a sé; una finta non protegge da niente. Il threat model lo dichiara invece di simularlo |

---

## P3 — Feature di profondità (no bloat)

| ID | Item | Note | Stato |
|----|------|------|--------|
| P3.1 | OCR multi-lingua reale (modelli aggiuntivi) | Il selettore che non faceva nulla è stato **rimosso** in 1.3.2: meglio nessun comando che uno che promette e non mantiene. Il modello attuale copre gli alfabeti latini | TODO |
| P3.2 | Diff semantico 2 PDF (non solo A/B stacked) | Compare attuale è merge etichettato | TODO |
| P3.3 | Tray: stato job + “apri ultimo risultato” | Tray oggi minimale | TODO |
| P3.4 | Portable firmato / zip release versionato | Distribuzione team | **METÀ FATTA** (1.11) — archivio versionato, archivio a nome fisso e `SHA256SUMS.txt`. Il nome fisso **non deve cambiare**: è ciò che tiene in piedi `/releases/latest/download/...` nei README e nella landing, e la versione la porta già il tag. La **firma** resta fuori: richiede un certificato, e Azure Trusted Signing non valida gli individui nell'UE.<br><br>**DOMANDA A SIGNPATH FOUNDATION INVIATA IL 2026-08-09.** In attesa di risposta: non pubblicano nessun tempo garantito, l'esperienza riportata è da qualche giorno a qualche settimana, e la revisione è fatta a mano.<br><br>**⚠ Il presupposto di questa voce era sbagliato, e va corretto qui perché altrimenti torna.** Dava per scontato che firmare togliesse l'avviso di SmartScreen. **Non è più vero per nessun certificato**: Microsoft ha rimosso nel 2024 la reputazione immediata dei certificati EV, quindi oggi anche un EV passa dallo stesso accumulo di reputazione di un OV. Firmare compra tre cose diverse — l'editore smette di essere «sconosciuto» e diventa un nome, la reputazione comincia ad accumularsi (per certificato: se si cambia, si riparte), e il pacchetto diventa a prova di manomissione. **L'unica strada che toglie l'avviso dal primo giorno resta lo Store** (P3.8).<br><br>**Le alternative, con il prezzo di ciascuna.** *Azure Artifact Signing*: generalmente disponibile per le organizzazioni UE, ma gli **individui restano limitati a USA e Canada**, senza data — chiuso. *Certum open source, €49/anno cloud*: più fonti dicono che porta la dicitura «Open Source Developer», quindi **neanche quello è il nome dell'autore**, e la firma cloud passa da un'app con interfaccia grafica che rompe la build headless. *Certum Standard OV a persona fisica, €209/anno*: è **l'unico che porterebbe «Antonio Andrea Rao»**, ma la loro pagina non dichiara cosa mostri Windows e va chiesto, ha lo stesso problema di automazione, e parte da **zero reputazione**. *EV a €379/anno*: dopo il 2024 non fa niente di più — da scartare.<br><br>**Perché SignPath.** Il confronto vero oggi non è «SignPath contro il tuo nome», è **«editore sconosciuto» contro «SignPath Foundation»**: il nome dell'autore non è sul tavolo a nessun prezzo ragionevole. È gratis, è nata per la CI, e **la scelta è reversibile** — il giorno che si prende un certificato proprio si firma con quello, e l'unico costo è ricominciare ad accumulare reputazione, che si pagherebbe comunque partendo oggi da soli. Il difetto reale da tenere presente: chi scarica dallo Store vede «Antonio Andrea Rao», chi scarica lo zip vedrebbe «SignPath Foundation» — **due editori per lo stesso programma**.<br><br>**Fatto per la domanda**: `docs/CODE-SIGNING-POLICY.md` pubblicata (loro la richiedono), e la dicitura sulla firma messa nei **due README, nelle due landing e nelle note della release** — scritta al presente («il pacchetto NON è firmato, la domanda è stata inviata») invece di anticipare una firma che non c'è. Quando arriva, cambia una riga per superficie.<br><br>**⚠ SMART APP CONTROL, scoperto il 2026-08-09 e cambia il peso di questa voce.** Su Windows 11 esiste una funzione che può sostituirsi a SmartScreen e che **blocca l'esecuzione dei file non firmati** — non li segnala: li blocca — e vale per **tutti gli eseguibili**, non solo per quelli scaricati da internet ([Microsoft Learn](https://learn.microsoft.com/en-us/windows/apps/package-and-deploy/smartscreen-reputation)). Su quelle macchine il portable non è «scomodo da aprire»: **non si apre**. È l'argomento più forte per firmare, e non riguarda l'estetica dell'avviso.<br><br>**Due cose dalla stessa fonte, che correggono le aspettative.** (a) Con un certificato valido — OV o EV — l'avviso al primo scaricamento **resta**, ma mostra il nome dell'editore verificato: firmare non lo fa sparire, lo qualifica. (b) *«La reputazione non si trasferisce dalle versioni precedenti a meno che entrambe non siano firmate con la stessa identità»*: **non firmati, ogni release riparte da zero per sempre**, ed è il motivo per cui con 27 download totali non si arriverebbe mai da nessuna parte. Firmare rompe quel giro.<br><br>Conseguenza su **P3.9**: la riscrittura della sezione «come si supera l'avviso» potrà dire «non compare» **solo per lo Store**. Per il portable firmato la riga giusta è «l'editore mostrato è SignPath Foundation; l'avviso può ancora comparire finché il file non accumula scaricamenti».<br><br>**Cosa resta da fare a risposta ottenuta**: il passo di firma nel workflow, e far arrivare il pacchetto firmato dentro la release senza toccare il nome fisso |
| P3.5 | **Documenti d'identità: carta d'identità, patente, passaporto** | Oggi non c'è nessun riconoscitore. Sono fra i dati più sensibili che passano da uno studio, e hanno formati regolari — la patente italiana ha una struttura fissa, il passaporto una riga MRZ leggibile a vista. Va fatto col metodo di casa: il pattern propone, un validatore decide, e il verbale amministrativo deve restare a zero | **DONE** (1.11) — carta d'identità elettronica, patente e passaporto, interruttore proprio (`documenti`), non dentro `fiscal`. Questi numeri **non hanno una cifra di controllo** e la loro forma è identica a quella di mille protocolli: si sostituiscono solo con il tipo di documento scritto vicino, altrimenti diventano un sospetto. Sui 127 documenti a verità zero: zero sostituzioni sbagliate |
| P3.8 | **Microsoft Store (MSIX), l'unica strada gratuita che toglie davvero l'avviso di SmartScreen** | Chi installa dallo Store non vede nessun avviso: il pacchetto lo firma Microsoft. E dal 2026 l'account sviluppatore è **gratuito**, per individui e per aziende. Ma non è un passo di confezionamento, è un **riadattamento dell'integrazione col sistema**: in MSIX i registri sono virtualizzati, quindi il menu contestuale non si scrive più con lo script PowerShell ma si **dichiara nel manifesto** (`windows.fileTypeAssociation`); il collegamento sul Desktop non esiste per costruzione (solo voce nel menu Start); e l'installatore `.bat` sparisce. Servono manifesto, icone in tutte le misure, `MakePri`, e il superamento della certificazione. Da verificare anche l'attrito noto fra i termini di licenza dello Store e le licenze della famiglia GPL. **Non risolve il percorso principale**: chi scarica lo zip da GitHub vede l'avviso esattamente come prima | **IN CORSO** — nome «Mr. Rao» prenotato su Partner Center (Store ID `9N7SJ4W88KQC`), manifesto in `packaging/AppxManifest.xml` con l'identita' vera assegnata dallo Store e le dieci associazioni di file dichiarate. **Scadenza: la prenotazione del nome decade se l'app non viene inviata entro tre mesi (dal 2026-08-09, quindi entro il 2026-11-09).** Mancano: icone in tutte le misure richieste, `MakeAppx`/`MakePri` nel workflow, e la catena di pubblicazione (registrazione Azure AD + associazione a Partner Center + azione `microsoft/store-submission`). **AGGIORNAMENTO 2026-08-09: la prima sottomissione è partita.** Icone, `MakeAppx` nel workflow, scheda in italiano e inglese, classificazione IARC (PEGI 3), giustificazione di `runFullTrust` e note per il collaudo: tutto fatto e inviato. Stato: **in certification** (Submission ✓, Pre-processing ✓). La scadenza della prenotazione è rispettata. Cosa resta è in **P3.9** e **P3.10**. Procedura reale, con i cinque punti in cui la mia guida sbagliava, in [STORE.md](STORE.md) |
| P3.7 | **L'OCR incolla il dato all'etichetta, e il riconoscitore non parte** | Trovato dal banco delle scansioni (A.9), non immaginato. Sui documenti degradati l'OCR perde lo spazio e produce `IBANIT60X0542811101000000123456`, `Tel.02 1234567`, un numero di carta attaccato ai puntini di guida di un modulo, `NT86O02008…` con «IT» letto «NT». In tutti e quattro i casi il dato **passerebbe il proprio validatore** — il mod-97 e il Luhn tornano — ma il pattern non arriva nemmeno a proporlo, perché i lookbehind `(?<![\w.+])` lo rifiutano quando è preceduto da lettere o da un punto. Risultato: **perdita silenziosa**, nemmeno un sospetto. Allentare quei lookbehind è facile; farlo **senza pagare falsi positivi** va misurato sui documenti a verità zero prima di toccare qualsiasi cosa | **DONE** (1.12) — allentati **IBAN e carte**, dove c'è un'aritmetica capace di smentire la forma: ammessa la parola incollata davanti, **mai una cifra** (una cifra vorrebbe dire ritagliare un pezzo da un numero più lungo). **Non i telefoni**: lì non esiste nessun conto che possa dire di no, quindi allentare sarebbe stato allentare e basta — aggiunto invece un pattern che *chiede di più* (`Tel.02…`). **Guadagno**: persi in silenzio da 60 a 46 su 640 (−23%); le scansioni da scanner in ordine passano da 5, 2, 2 a **0, 0, 0** a 300/200/150 DPI. **Costo**: zero falsi positivi.<br><br>**Ma quel primo zero non poteva fallire**, ed è la parte che conta: sui documenti usati per misurarlo i pattern nuovi avevano proposto **zero candidati**, e un costo di zero che non ha modo di essere diverso da zero non è una misura. Rifatto con banchi capaci di dire di no, compresa una prova a volume su 200 000 candidati che spiega perché sulle carte siamo stati stretti: il mod-97 lascia passare lo **0,01%**, il Luhn il **10,03%**. 30 test nuovi, visti **rossi** sul codice di prima (21 su 30; i 9 verdi sono le guardie, che devono restare verdi in entrambi gli stati).<br><br>Ha prodotto due voci: **P3.14** (un caso su quattro era attribuito male dal banco) e i **residui** qui sotto |
| P3.6 | **NER opzionale per i nomi (modello ONNX leggero)** | Serve a una cosa sola che le liste non possono fare: leggere il **ruolo nella frase**. «Lavoro a Milano» e «ho parlato con Mario Milano» contengono la stessa parola, e oggi il motore o la lascia passare o la segna come sospetto. Il guadagno è sui cognomi che coincidono con parole comuni — Chiesa, Costa, Monte, Villa. **Il costo va detto:** un modello fa sparire il *perché*. Oggi ogni sostituzione ha una regola citabile e due esecuzioni danno lo stesso esito; un modello dà un punteggio, e il giorno che sbaglia non si può spiegare a un cliente perché un nome è rimasto. Quindi: spento di default, **mai al posto** dei validatori — il modello propone, contesto e aritmetica decidono, i sospetti restano. Vedi issue #4. **Precisazione (2026-08-09): non serve installare nessuna «AI».** `onnxruntime` è già una dipendenza dichiarata dalla 1.9.0 e RapidOCR porta con sé 30,3 MB di modelli `.onnx` che girano già oggi in locale, offline, sul processore: un NER sarebbe un altro file caricato dalla stessa libreria. Il costo vero è altrove — peso nel portable (15–60 MB), una licenza in più da rispettare, e la riga «Nessun modello» che i due README e la landing usano come argomento di vendita | **CHIUSO il 2026-08-09: misurato, non conviene** — approvato e poi indagato per davvero. Non si ferma per la licenza né per il peso: **per il guadagno, che è zero nel cancello difendibile**.<br><br>**Cosa è stato misurato**, su corpora che non abbiamo scritto noi: 27 moduli amministrativi italiani in bianco (3,33 M caratteri, scaricati da Agenzia Entrate, INPS, ADM, Giustizia, CCIAA), 15 moduli IRS in bianco, 5 Gazzette Ufficiali. Due modelli provati davvero, non solo letti.<br><br>**Il vincolo è validato**: NER libero → 326 sostituzioni sbagliate sui moduli in bianco; passandolo per le prove di casa → **1**. Questo risultato resta valido per qualunque modello futuro, e vale più della decisione stessa.<br><br>**Ma dentro il vincolo il guadagno è 0** su 4,5 M caratteri, con entrambi i modelli. La ragione è precisa: nei casi «titolo davanti» e «firma» il cognome è **una parola sola**, e una parola sola ambigua è difficile per un modello quanto per una regex — il candidato con licenza pulita ne recupera il **24%** col titolo e lo **0%** sulle firme. Il gruppo di controllo (42 cognomi senza collisione, stesse cornici) fa **38-39/42**: la caduta è del modello, non del banco.<br><br>**Licenze, che squalificano quasi tutto**: WikiNEuRal e spaCy-IT sono CC-BY-NC; GLiNER v1 idem; WikiANN dichiara «unknown»; `Italian_NER_XXL` e `gliner-pii-edge` non dichiarano i dati di addestramento. **L'unica catena verificata end-to-end è `osiria/*` → WikiNER → CC-BY-4.0**, e l'unico membro già in ONNX pesa **63,9 MiB** — il portable passerebbe da ~165 a ~230 MB (+39%), e coprirebbe **solo l'italiano**.<br><br>**Buco da ricordare**: `scripts/gen_third_party.py` legge i metadati dei pacchetti Python. Un `.onnx` scaricato a parte **non comparirebbe** in `THIRD_PARTY.md`: la riga andrebbe scritta a mano o il generatore esteso.<br><br>**Dove il guadagno c'è davvero, e non costa niente**: nelle Gazzette la forma ricorrente è `Il Ministro: COGNOME` — titolo davanti, cognome in **maiuscolo**, una parola sola. Non lo prende il motore e non lo prende il modello da 64 MiB (3/42). È la stessa forma che `_RE_NAME_PAIR_UPPER` già insegue nelle intestazioni email. **Una regola di casa che estenda `_RE_TITLE_NAME` al cognome singolo in maiuscolo dopo i due punti costa zero megabyte, zero licenze e zero modelli**, ed è la cosa da misurare prima di riaprire questa voce → **P3.18** |
| P3.9 | **Il link allo Store, e la sezione sull'avviso di Windows da riscrivere** | Due cose, e la seconda conta più della prima. Il link `https://apps.microsoft.com/detail/9N7SJ4W88KQC` è già definitivo — lo Store ID non cambia — ma **oggi risponde `410 Gone`**: verificato, non supposto. Pubblicarlo prima vorrebbe dire un pulsante morto proprio sulla strada della fiducia, quella che esiste per togliere l'avviso «editore sconosciuto»: chi ci clicca è la persona più diffidente, e troverebbe un errore. È lo stesso modo di rompersi in silenzio da cui nasce la disciplina del nome fisso `MrRao-Portable.zip`. **Quando risponde `200`**: aggiungere il link (non sostituire la portable, che resta la strada principale) e **riscrivere la sezione sull'avviso di Windows nei due README** — oggi dice solo «ecco come si supera», da allora potrà dire «installalo dallo Store e non compare». Il pulsante di scaricamento sta in 17 punti su 7 file, ma il link Store va in pochi punti scelti. Controllo: `curl -sS -o /dev/null -w "%{http_code}" -L https://apps.microsoft.com/detail/9N7SJ4W88KQC` | TODO (attende la certificazione) |
| P3.10 | **La catena di pubblicazione automatica non è mai stata eseguita** | Configurata il 2026-08-09: i quattro segreti ci sono e la registrazione Entra ha il suo ruolo. Ma **configurata non è provata**: la prima volta che si scriverà `si` in `pubblica_store` sarà anche la prima volta che quel percorso gira davvero. Va lanciata guardando l'esecuzione, non a fine giornata. **Il punto più probabile di rottura è il ruolo:** è stato assegnato `Developer` e non `Manager`, di proposito — Manager dà accesso completo all'account e permette di gestire utenti e tenant, che su una credenziale dentro GitHub Secrets è sproporzionato. Se fallisse per permessi, il ruolo si allarga in pochi secondi da Partner Center: meglio allargarlo con una prova in mano che stringerlo dopo un incidente | TODO |
| P3.11 | **«Nessun modello» non è vero già oggi, e va riscritto prima di qualunque NER** | Emerso parlando di P3.6, ma **non dipende da P3.6**: è una promessa pubblica sbagliata adesso. `README.it.md` dice «Il riconoscimento è codice, non una rete neurale… niente da scaricare»; `PRIVACY.md` dice «Nessun modello, nessuna rete neurale». Intanto **RapidOCR spedisce ~30 MB di modelli `.onnx` dentro il portable**, ed è una rete neurale che gira su ogni scansione. Dire «nessun modello **AI**» peggiora le cose: un modello OCR *è* un modello AI, e la frase diventerebbe più precisa e più falsa. La cosa vera, che è anche il valore vero, riguarda **la decisione**: l'OCR trasforma pixel in testo e non decide niente; cosa sia un dato personale lo decidono regole e aritmetica, a valle. È lo stesso principio di casa — il pattern propone, il validatore decide — e spiega perché il banco A.9 trova quello che trova: quando l'OCR legge male, il motore non può decidere bene (vedi P3.7). Riscrivere in README.it.md, README.md, PRIVACY.md e nelle due landing che la citano. **Nella stessa passata**: `02-carta-bianca.html` dice ancora «390+ test», fermo a venti release fa | **DONE** (1.12) — e i modelli sono **quattro**, non tre: oltre ai 30,3 MB di RapidOCR c'è **magika**, il riconoscitore di tipo file di Google, 3,16 MB, tirato dentro da MarkItDown (`_markitdown.py:15` import, `:121` istanza, `:724` `identify_stream`) e raccolto esplicitamente nel bundle. **Non gira solo sulle scansioni: gira su ogni conversione.** La licenza è coperta (`THIRD_PARTY.md:52`, Apache) ma la dipendenza **non è dichiarata in requirements.txt**: arriva di rimbalzo. La promessa ora è *la **decisione** non passa da nessun modello*, e vale il rovescio, che è la parte utile: quando l'OCR legge male, il motore non può decidere bene. Trovata strada facendo la lacuna che è diventata **P3.15** |

---

| P3.12 | **Landing in inglese, non una traduzione** | Siamo bilingui ovunque tranne che sulla porta d'ingresso: README, interfaccia, documento prodotto e scheda Microsoft Store esistono in due lingue, la landing **solo in italiano** (`<html lang="it">` su tutti e tre i file tracciati). Il motore riconosce NHS number, National Insurance number, SSN, ITIN, routing ABA, SIN, ABN, TFN, codice postale britannico e la riga MRZ dei passaporti: è stato costruito **anche** per chi non è italiano, e quella persona arriva su una pagina che non può leggere. **Non è una traduzione**: la pagina italiana si regge su esempi che a un lettore straniero non dicono niente — Gazzetta Ufficiale, Agenzia delle Entrate, il codice fiscale come esempio principale. La pagina inglese deve **partire dai formati anglosassoni** e usare le prove che li riguardano davvero: i **99 moduli fiscali statunitensi** fra i documenti a verità zero e i **1 500 messaggi in inglese** del corpus di prosa. Più corta, e con meno cose. **⚠ IL VINCOLO DI ONESTÀ, che è la cosa più facile da perdere qui:** il riconoscimento dei nomi in inglese è **deliberatamente più stretto** di quello italiano — lo dice già `README.md:32` — e una pagina inglese che promettesse la stessa copertura sarebbe la bugia peggiore possibile, perché la farebbe proprio a chi non può verificarla leggendo gli esempi. Serve anche `hreflang` fra le due pagine e un rimando dai README. Il gate ora copre le landing tracciate (vedi **P3.15**), quindi la pagina nuova ci entra da sola.<br><br>**QUALE PAGINA VEDE CHI ARRIVA** (deciso il 2026-08-09): browser in italiano → pagina italiana; **qualunque altra lingua → inglese**. Non «inglese solo per l'inglese»: l'inglese è la lingua di ripiego per tutto il resto del mondo, l'italiano è il caso speciale.<br><br>**Il selettore di lingua resta in alto**, nello stesso stile degli altri pulsanti e **accanto a «Scarica»** — non un link di servizio in fondo alla pagina: chi arriva sulla pagina sbagliata deve vedere subito come cambiarla.<br><br>**⚠ Il vincolo tecnico da sapere prima di cominciare, non dopo:** la landing è **statica** su Cloudflare Pages, e la pagina ha una **CSP con le impronte degli inline calcolate da `_rebuild.py`**. Quindi: (a) leggere `Accept-Language` va fatto lato server con una Pages Function (`functions/_middleware.js`), perché `_redirects` non sa condizionare sulla lingua; (b) un rimando fatto in JavaScript costerebbe un lampo di pagina sbagliata, non funzionerebbe senza JS, e **richiederebbe di rigenerare le impronte CSP**; (c) la scelta fatta col selettore deve restare, altrimenti il rimando automatico la annulla al ricaricamento | **DONE** (1.12) — pubblicata su `rao.valor-cyber.com/en/`. Sei blocchi contro nove, aperta sui formati che riguardano chi legge, con le prove fatte in inglese.<br><br>**Il vincolo di onestà è stato risolto in modo diverso da come è scritto qui sopra, per decisione dell'utente**, e vale scriverlo perché la prima stesura faceva l'opposto: c'era una sezione intera che spiegava la pagina *per differenza* dall'italiano — «i nomi in inglese sono più stretti», i moduli italiani citati accanto a quelli americani, le 6 000 mail italiane di fianco alle 1 500 inglesi. Tolta: *«a chi valuta questo programma non serve sapere cosa fa in un'altra lingua»*. **Il limite sui nomi non è sparito**: resta dov'è verificabile e dove conta davvero — `README.md:32` e `PRIVACY.md` — e la voce «Limiti» della pagina inglese lo dice in una riga senza fare paragoni. Una landing non è il posto dove si custodisce un limite.<br><br>Al posto di quella sezione è entrata la **«minaccia»** della pagina italiana, che spiega *perché* il programma esiste e in inglese mancava, più la sezione **contatti** |
| P3.13 | **Il corpus dei 127 documenti non è nel repository, e nessun test lo esercita** | Scoperto lavorando a P3.7. «127 documenti a verità zero» è l'affermazione su cui poggiano i numeri più forti che pubblichiamo — sta nei due README, in `PRIVACY.md`, in `ARCHITECTURE.md`, nella landing e ora anche nella scheda del Microsoft Store. Ma in `tests/dati/` ci sono tre corpora di **testo** e nessuno dei 127; nessun test li apre. **L'affermazione non è falsa** — le misure sono state fatte davvero — ma **non è riproducibile da chi legge il repository**, e non c'è niente che si accorga se un giorno smettesse di valere. Su un progetto la cui disciplina è «le affermazioni dei documenti sono sotto test», è l'eccezione proprio dove peserebbe di più. **CHIUSO il 2026-08-09, per decisione dell'utente.** Il numero esatto è stato tolto da ogni documento: si dice **«oltre cento documenti amministrativi pubblici»** e basta. Non è un ripiego — dire *cosa sono* è più utile di dire *quanti*: chi volesse rifare la misura sa da dove partire, mentre «127» prometteva una verificabilità che non c'era.<br><br>La motivazione, che vale anche per le prossime volte: *«non è che ogni cosa debba essere dimostrabile, già siamo eccessivamente trasparenti, il codice è lì a disposizione»*. È una posizione difendibile — le misure sono state fatte davvero, e il motore è pubblico e ispezionabile riga per riga.<br><br>**Cosa NON è stato fatto, e perché è giusto così**: le misure precise che vengono da quel corpus restano al loro posto (2 739 sostituzioni sbagliate sulla soglia prosa/modulo, 8 904 di `name_guess`, zero sui documenti d'identità). Cancellarle avrebbe tolto **il perché** da quelle decisioni, lasciando scritto «pretendiamo due riscontri sui moduli» senza più la ragione. Toccato: i due README, `ARCHITECTURE.md`, `PRIVACY.md`, `CHANGELOG.md`, il commento in `mr_rao/privacy.py` e le due landing | **CHIUSO** |
| P3.14 | **Il banco sotto-conta i dati segnalati** | Trovato da P3.7. `_sospetto_copre` in `scripts/bench_scansioni.py` confronta il campione **mascherato** del sospetto con il valore atteso: su un IBAN il cui codice paese è stato letto male (`NT86O…` invece di `IT86O…`) i primi due caratteri non coincidono, quindi il confronto fallisce e il dato viene contato **PERSA** anche se il motore lo ha regolarmente **segnalato**. Conseguenza: una parte di quello che pubblichiamo come «perso in silenzio» in realtà un avviso lo produce.<br><br>**CHIUSO COME DOCUMENTATO, il 2026-08-09.** Il **prodotto non ha nessun difetto**: il motore segnala regolarmente quel dato, ed è il metro che lo attribuisce male. Non c'è niente da correggere in `mr_rao/`.<br><br>Resta scritto qui perché **un numero pubblicato eredita l'errore**: la quota «persa in silenzio» in `docs/PRIVACY.md` conta come persi anche dati che un sospetto lo producono. L'errore è quindi **pessimistico** — ci fa apparire peggiori di quanto siamo — che è la direzione innocua, e il motivo per cui non vale una correzione urgente. Ma se un giorno quei numeri miglioreranno all'improvviso senza che nessuno abbia toccato il motore, **la spiegazione è questa**, ed è meglio trovarla scritta che ricostruirla | **CHIUSO** (documentato, nessun difetto nel prodotto) |
| P3.15 | **Le pagine pubblicate invecchiavano in silenzio** | Trovato facendo P3.11. `check_docs.py` esiste per impedire ai documenti di invecchiare senza che nessuno se ne accorga, e guardava **solo i `.md`**. Le landing HTML no — e infatti `docs/landing/index.html` ha dichiarato **v1.7.2** mentre `APP_VERSION` era 1.11.0: venti release di scarto, e nessun controllo capace di vederlo | **DONE** (1.12) — ottava invariante, `landing_invecchiate()`. **Tre dettagli che non sono dettagli**: usa `git ls-files` e non un glob (le bozze `02-*`/`03-*` sono gitignorate, un glob le avrebbe incluse facendo fallire il gate su file che non fanno parte del progetto); **regex dedicata**, perché le landing scrivono il numero attaccato a una `v` in un distintivo (`· v1.7.2`) e mai nella forma discorsiva che cerca la regex dei `.md`, e la `v` è obbligatoria apposta — un `\d+\.\d+\.\d+` nudo avrebbe pescato `127.0.0.1`, che nelle landing compare cinque volte; **due guardie contro il controllo morto** (zero landing tracciate è un problema, e zero versioni trovate è un problema che **nomina la regex** da aggiornare). Visto fallire in quattro modi, mutando anche il controllo stesso. 18 test |
| P3.18 | **`Il Ministro: COGNOME` — il cognome singolo in maiuscolo dopo i due punti** | Lasciata da P3.6, ed è la parte utile di quell'indagine. Nelle Gazzette Ufficiali la forma ricorrente non è «nome cognome»: è un **titolo davanti, due punti, e un cognome solo in maiuscolo**. Oggi non lo prende il motore — serve l'adiacenza di due parole — e **non lo prende nemmeno un modello NER da 64 MiB** (3 casi su 42 misurati). È la stessa forma che `_RE_NAME_PAIR_UPPER` già insegue nelle intestazioni delle email, quindi il precedente in casa c'è.<br><br>**Perché viene prima di qualunque modello**: costa zero megabyte, zero licenze, zero dipendenze, e agisce esattamente dove il NER ha fallito. Se il guadagno c'è, la voce P3.6 non va nemmeno riaperta.<br><br>**Il costo va misurato prima**, e il banco esiste già: sui documenti a verità zero le sostituzioni sbagliate **non devono salire**. Attenzione al fatto che un titolo seguito dai due punti è anche l'intestazione di un campo su un modulo (`Responsabile: SETTORE TECNICO`), che è precisamente il modo in cui questa regola può fare danni | TODO |
| P3.17 | **Il sito pubblicato non si aggiorna da solo, e lo si scopre guardandolo** | Domanda dell'utente il 2026-08-09, e la risposta ha trovato un buco vero. Ci sono **due passaggi**, e vanno tenuti distinti.<br><br>**(a) Il numero di versione nella landing è scritto a mano.** Automatico è solo il *controllo*: `landing_invecchiate()` (P3.15) fallisce se una pagina dichiara una versione diversa da `APP_VERSION`. È una guardia, non un automatismo — si rifiuta di lasciar passare il numero sbagliato, non lo corregge. Alla 1.12.0 sono stati cinque punti da cambiare a mano. **Questa metà va bene così**: un gate che *corregge* invece di *fermare* toglie l'occasione di accorgersi che una pagina va riletta, non solo rinumerata.<br><br>**(b) Il push su GitHub non pubblica niente.** Il progetto Cloudflare Pages è a **caricamento diretto**, non collegato al repository: finché non gira `_rebuild.py` + `wrangler pages deploy`, il sito resta indietro rispetto a git **senza che niente lo dica**. È successo il 2026-08-09: la pagina inglese era corretta, committata e pushata, e online c'era ancora la vecchia — se ne è accorto l'utente guardando il sito. **È lo stesso modo di rompersi in silenzio che il gate esiste per impedire, spostato di un passo più in là**: il gate garantisce che il repository sia coerente, e nessuno garantisce che il pubblicato sia il repository.<br><br>**Le due strade, con il prezzo di ciascuna.** *Automatizzare il deploy* (action su push a `main` che tocca `docs/landing/`): serve un token API Cloudflare nei segreti, e pubblica **qualunque cosa** finisca su main — una landing modificata e non riletta va online da sola, che su una pagina di marketing è meno grave che sul motore ma non è niente. *Un controllo invece di un'automazione*: un passo che scarica la pagina pubblicata e confronta la versione dichiarata con `APP_VERSION`, e **dice** che il sito è indietro senza toccarlo. Costa un `curl` e non chiede nessuna credenziale nuova. **Da preferire la seconda**, per la stessa ragione della metà (a) | TODO |
| P3.16 | **«Fatture / contabili» era il profilo predefinito con un altro nome** | Segnalato dall'utente, verificato confrontando le **opzioni risolte** e non i dizionari: `default` e `fatture` producevano `ConvertOptions` **identiche campo per campo**. Causa archeologica: l'unica differenza del profilo era spegnere `name_guess`, che nella **1.7.2** è stato spento *di default* — da quel giorno l'istruzione non istruiva più niente.<br><br>**Il danno non è tecnico, è di fiducia**: chi sceglieva «Fatture» credeva di aver detto qualcosa al programma, e non aveva detto niente. Una tendina che offre due strade verso lo stesso posto insegna che le tendine non contano.<br><br>**Perché nessuno se n'è accorto per quattro release**, che vale più del difetto: i test controllavano che ogni profilo fosse coerente **con sé stesso** e con l'interfaccia, mai che fosse **diverso dagli altri**. Non esisteva un confronto fra profili, quindi non esisteva modo di vedere un clone | **DONE** (1.12) — voce rimossa da `profiles.py`, `i18n.py`, `app.js` e `index.html`; `tests/test_profili_distinti.py`, dove il secondo test **è la prova che il primo può fallire** (ricostruisce il difetto storico e verifica che venga preso) |

### P3.6: la decisione e i suoi vincoli

**Decisione del 2026-08-09: si fa.** Con la forma descritta qui, che non è
un dettaglio implementativo — è la ragione per cui si può fare.

**L'ostacolo di prima non esiste più, ed è bene sapere perché.** Il veto era
«contraddice la riga *nessun modello*». Quella riga è stata tolta con
P3.11, e non per fare spazio al NER: **era falsa già prima**, con o senza.
Nel portable ci sono quattro `.onnx` — RapidOCR e magika — per 33 MB.

Scrivere «nessun modello **AI**», che era la correzione istintiva, avrebbe
peggiorato: un modello OCR *è* un modello AI, e la frase sarebbe diventata
più precisa e più falsa.

**Il vincolo vero invece è rimasto, e adesso è più affilato.** La promessa
pubblica ora è: *la decisione non passa da nessun modello*. Questo separa
nettamente due posizioni:

- **a monte** — OCR e magika leggono; cosa sia un dato personale lo
  decidono a valle regex e aritmetica. La promessa regge;
- **dentro la decisione** — è lì che finirebbe un NER lasciato libero, ed è
  lì che la promessa cadrebbe. Non per una questione di parole: di fatto.

#### La forma obbligatoria

1. **Il modello propone, le regole decidono.** Il NER segnala candidati; per
   diventare una sostituzione devono comunque superare le prove che il
   motore già usa per i nomi — titolo davanti, formula di chiusura, nome
   accanto a un indirizzo di posta, adiacenza nome+cognome.
2. **Non abbassa mai l'asticella.** Un candidato che oggi resta un sospetto
   non deve diventare una sostituzione solo perché il modello è convinto.

   **⚠ Contraddizione sciolta il 2026-08-09.** Questa regola e l'elenco al
   punto 1 dicevano due cose incompatibili: l'elenco include *l'adiacenza
   nome+cognome* fra le prove valide, ma nei casi di adiacenza il motore
   oggi produce **proprio un sospetto** — quindi usarla avrebbe fatto
   esattamente ciò che il punto 2 vieta. La misura l'ha reso concreto: è
   l'unico cancello con guadagno diverso da zero, e ha **precisione circa
   1 su 3** sui documenti amministrativi.

   **Decisione: vince il punto 2.** L'adiacenza resta una prova valida solo
   quando è il motore a stabilirla con i propri elenchi; **non** diventa
   una prova perché un modello dice che quella sequenza è una persona. Chi
   implementerà il NER deve leggere questa riga prima dell'elenco sopra.
3. **I sospetti restano**: quello che non passa le prove si segnala, come
   adesso.
4. **Spento di default.**

#### Il collaudo, che è una domanda sola

> *Questa sostituzione la so ancora spiegare citando una regola?*

Se sì, il NER è dentro le regole di casa. Se no, è fuori — e allora va tolta
dai documenti la frase «ogni sostituzione si spiega indicando la regola che
l'ha prodotta». **Non si possono avere entrambe**, e la seconda vale più del
NER.

#### Cosa va misurato prima di spedirlo

- **Falsi positivi sui 127 documenti a verità zero: non devono salire.**
  Il guadagno atteso sono i cognomi che coincidono con parole comuni
  (Chiesa, Costa, Monte, Villa); se il prezzo è redigere mezzo verbale
  amministrativo, il prezzo è troppo alto.
- **Il peso nel portable** (15–60 MB attesi) e la licenza del modello.
- Il README ora **nomina i modelli con i pesi**: ne aggiunge una riga, e
  quella riga deve guadagnarsi il posto.

#### `name_guess` è già un NER, ed è la prova che il vincolo è giusto

Prima di scrivere codice nuovo conviene guardare quello che c'è:
`name_guess` (`mr_rao/privacy.py`) fa già il mestiere del NER, in modo
primitivo — indovina dalla **forma superficiale** invece che dal ruolo nella
frase. La regola è: due o più parole maiuscole di fila di cui nessuna
«sembra una parola italiana» sono nome e cognome, **senza nessun riscontro
negli elenchi**.

L'unica difesa è `_looks_like_word`: la parola finisce con uno di una
cinquantina di suffissi italiani. Un elenco di cinquanta desinenze che prova
a descrivere tutto l'italiano non può reggere — «Quadro» finisce in `-dro`,
«Imposta» in `-osta`, «Lorda» in `-orda`, e per il codice non sono parole
italiane.

Il conto, su documenti che non contengono **un solo** dato personale:
8 904 sostituzioni sbagliate su venti moduli dell'Agenzia delle Entrate in
bianco, 14 376 su otto Gazzette, 2 888 su novantanove moduli fiscali
statunitensi. Spenta di default dalla 1.7.2 (#5).

**Il difetto non è che indovinava: è che decideva da solo.** Nessuna
corroborazione richiesta. Il vincolo scelto qui sopra — *il modello propone,
le regole decidono* — è esattamente la cura: se `name_guess` avesse dovuto
solo proporre e poi passare le prove del motore (titolo davanti, formula di
chiusura, adiacenza a un indirizzo di posta), su un modulo in bianco quelle
prove non esistono e non avrebbe toccato niente.

Quindi non è solo la funzione che il NER sostituira': e' la **dimostrazione
empirica** che il vincolo e' quello giusto, pagata 8 904 errori.

**Conseguenza operativa: quando il NER arriva, `name_guess` va ritirato, non
affiancato.** Due indovini con due regole diverse, di cui uno senza
corroborazione, sono peggio di uno solo.

**FATTO NELLA 1.13.0, e senza aspettare il NER.** La misura sui corpora
indipendenti ha reso la questione autonoma: 27 moduli amministrativi
scaricati dagli enti passano da 27 sostituzioni sbagliate a 2 529 (×94), i
moduli IRS da 15 a 622. Non serviva un sostituto per togliere una regola
che sbagliava così. Ritirata da motore, interfaccia, riga di comando e
documenti; `--name-guess` e `--no-name-guess` restano accettati e inerti.

E la ragione per cui nessuno se n'era accorto vale piu' del difetto, perche'
riguarda il metodo e non il codice: *«il banco a due corpora li avevamo
scritti noi, e un corpus scritto a mano contiene solo le trappole a cui chi
lo scrive ha pensato»*. Il NER va misurato su corpora che non abbiamo
scritto noi, altrimenti si ripete lo stesso errore con uno strumento piu'
sofisticato.

#### Ordine di lavoro

**Dopo P3.7.** Il NER lavora sui casi dubbi; P3.7 riguarda IBAN e carte che
il validatore riconoscerebbe e che stiamo perdendo **in silenzio**. Dati
certi prima di dati probabili.

---

## P4 — Debito tecnico

| ID | Item | Stato |
|----|------|--------|
| P4.1 | Rinominare cartella repo `markitdown-webapp` → `mr-rao` | TODO |
| P4.2 | Rimuovere shim MarkItDown quando nessuno li usa più | **NON SI APPLICA** — verificato: nei sorgenti non è rimasto nessuno shim, MarkItDown è una dipendenza viva. I ponti di compatibilità superstiti sono altri e hanno ancora senso: `paddleocr`→`rapidocr`, `--no-name-guess` che non fa niente, `file1`/`file2` nella rotta di confronto. Toglierli romperebbe script altrui senza guadagnarci nulla |
| P4.3 | Spezzare `app.js` in moduli ES se cresce ancora | TODO |
| P4.6 | **Su touch le spiegazioni dell'interfaccia non esistono** | Trovato facendo P1.5. I suggerimenti `data-tip` — circa quaranta, e sono il posto dove il prodotto spiega **perché** fa quello che fa — si aprono su `mouseover` (`static/js/app.js` ~883). Senza mouse non c'è modo di aprirli: su telefono e tablet sono di fatto invisibili. Nessuna regola CSS può supplire, serve un gestore per il tocco. Su un prodotto che si difende spiegandosi, perdere le spiegazioni proprio dove lo schermo è piccolo è il caso peggiore | **BASSA PRIORITÀ, per decisione dell'utente (2026-08-09)**: *«da tablet non mi interessa se non si aprono le quaranta spiegazioni dell'interfaccia»*. La ragione regge: il prodotto si usa dal computer, e da tablet il percorso vero è convertire, non leggere le spiegazioni. L'analisi qui sopra resta scritta perché il giorno che il tablet diventasse un caso d'uso reale, il difetto è già trovato e non va ricercato |
| P4.7 | **`renderDiff()` scrive stili in linea e vince sui media query** | Trovato facendo P1.5. `static/js/app.js` ~311 mette `max-height:240px` direttamente sul `<pre>` del testo originale. Essendo in linea batte `@media (max-height: 640px)`, quindi il confronto prima/dopo non si adatta agli schermi bassi — e il confronto è «il controllo che conta» secondo i nostri stessi documenti. Va spostato in CSS | TODO |
| P4.4 | CSS già estratto in `static/css/app.css` | **DONE** |
| P4.5 | **Migrare da `rapidocr_onnxruntime` a `rapidocr`** — fatto in 1.9.0. Non era manutenzione: la 1.2.3 perdeva gli spazi fra le parole (`PartitaIVA12345678903-tel.+390951234567`) e sullo stesso documento il filtro privacy trovava **1** dato personale invece di **4** — IBAN, partita IVA e telefono restavano in chiaro. L'API non era compatibile (`RapidOCROutput` invece della tupla), `onnxruntime` va dichiarato a parte, e l'intera suite passava anche col motore OCR rotto, perche' ogni test lo sostituiva con testo finto: aggiunto `tests/test_ocr_motore.py` | **DONE** (1.9.0) |

---

## Non fare (per ora)

- Nuovi preset / nuovi formati file “per completezza”
- Rewrite framework frontend (React/Vue): overhead ingiustificato
- Auth / multi-utente: fuori scope tool locale
- Cloud sync di qualsiasi tipo (rompe il value prop)

---

## Ordine di lavoro consigliato

**Riscritto il 2026-08-09, dopo la 1.12.0.** Il vecchio ordine era fatto di
voci ormai chiuse, e A.9 non è più in attesa di documenti.

```
P3.9  (fuori catena: aspetta la certificazione Microsoft, non noi)
 │
P0.3  ← l'ultima P0 aperta, e l'unica che l'utente incontra ogni giorno
 │
P3.6  (NER) ← approvato, e adesso è il turno: P3.7 è chiuso
 │
P3.10 → P3.4   (le due metà della distribuzione: automazione, firma)
 │
P4.7 → P4.3 → P4.1
 │
P3.1 / P3.2 / P3.3   solo su richiesta esplicita
```

**P3.9 sta fuori dalla catena perché non dipende da noi.** Il link allo
Store risponde `410` finché la certificazione non finisce: si controlla, non
si lavora.

**P0.3 resta in cima fra le cose che dipendono da noi.** È l'unica P0 rimasta
aperta, ed è ferma da più release di ogni altra voce di questo elenco.

**P3.6 è sbloccato.** L'ordine scritto nella sua scheda — *dopo P3.7, dati
certi prima di dati probabili* — è stato rispettato: P3.7 è chiuso nella
1.12.0.

**A.9 non è più in attesa.** È stato misurato su scansioni vere ed è sceso a
bassa priorità: quel che resta è ritarare i profili, cioè correggere una
lusinga di circa quattro punti su un numero già pubblicato.

---

## P0-bis — Esito audit 1.3.0 (chiuso)

Aggiunto dopo l'audit di agosto 2026. Tutti verificati eseguendo, non ipotizzati.

| ID | Item | Stato |
|----|------|-------|
| A.1 | Il repository committato non era importabile; metà delle correzioni 1.1.2/1.1.3 viveva solo sul disco | **DONE** (1.3.0) |
| A.2 | Cartelle predefinite dentro OneDrive → contraddiceva «zero cloud» | **DONE** (1.3.0) |
| A.3 | `GET /api/folders/defaults` creava directory (raggiungibile con un `<img src>`) | **DONE** (1.3.0) |
| A.4 | `THIRD_PARTY.md` sbagliava la licenza di Scrubadub e ometteva python-stdnum (LGPL) | **DONE** (1.3.0) |
| A.5 | `taskkill /F` nel `.bat` poteva troncare i `.md` in scrittura | **DONE** (1.3.0) |
| A.6 | `APP_VERSION` ferma a 1.2.1 col changelog già a 1.2.4 | **DONE** (1.3.0) |

### Lezioni da non ripetere

- **Le licenze non si scrivono a mano.** L'elenco manuale sbagliava una licenza
  e ne ometteva un'altra con obblighi veri. Ora si genera.
- **Un default può smentire il claim del prodotto.** Nessun bug nel codice:
  solo una cartella predefinita nel posto sbagliato.
- **Il changelog non è una prova.** Dichiarava rilasciate correzioni che in git
  non c'erano.

## P2-bis — Igiene di rilascio

| ID | Item | Perché | Stato |
|----|------|--------|-------|
| P2.5 | `gen_third_party.py --check` dentro il quality gate | Le licenze scadono in silenzio | **ERA GIÀ FATTO** — è nel gate, con la via d'uscita `MR_RAO_GATE_NO_LICENCE_CHECK` per i runner puliti, dove il confronto fallirebbe per il motivo sbagliato. Questa riga è rimasta TODO per mesi: anche il backlog invecchia |
| P2.6 | Gate: `APP_VERSION` senza voce di changelog = errore | Ha già sbagliato una volta | **DONE** (1.11) — si aggancia alle **intestazioni**, non al numero cercato nel testo: qui le voci si citano a vicenda, e una menzione di sfuggita avrebbe fatto passare il controllo. Zero intestazioni riconosciute = errore, non «pulito», altrimenti un cambio di formato lo renderebbe verde per sempre |
| P2.7 | Verifica «HEAD è importabile» in CI | È già successo di committarne uno rotto | **DONE** (1.11) — `scripts/check_import.py` importa i 21 moduli **uno per uno**, svuotando `sys.modules` fra l'uno e l'altro: senza, il primo import tira dentro gli altri e una coppia circolare passa inosservata (misurato). Gira in CI, nell'hook **e nel gate locale**, dove mancava proprio a chi lo usa più spesso |
| P2.8 | Valutare la rimozione di Scrubadub | Misurato su testo inglese: stesse redazioni con e senza, e da solo spezzava il testo. Rimosso | **DONE** (1.3.3) |

## P0-ter — Riconoscimento tollerante agli errori OCR

Emerso testando il repo appena clonato su un PDF scansionato vero.

Stesso contenuto, due strade: letto da **immagine** produce 3 redazioni, letto
da **PDF scansionato** ne produce 1. L'OCR storpia i caratteri — `A01` diventa
`AD1`, `IBAN IT60X…` diventa `TBAN1TB0X…` — e le espressioni regolari non
riconoscono più il codice, che resta nel testo deformato ma ancora identificante.

| ID | Item | Note | Stato |
|----|------|------|-------|
| A.7 | Avviso nel risultato quando la redazione ha lavorato su testo OCR | Mitigazione immediata: chi legge sa che lì deve controllare | **DONE** (1.3.2) |
| A.8 | Riconoscimento tollerante alle confusioni tipiche dell'OCR sui formati a struttura fissa | Fatto per CF e IBAN, fino a 2 correzioni, e si accetta solo se il checksum torna. Attenzione: il checksum **non basta** — la prima versione trasformava un numero d'ordine in un IBAN valido. Serve anche restringere i candidati | **DONE** (1.6.0) |
| A.9 | Banco di prova con scansioni a qualità decrescente | Serve un numero, non un'impressione: quante redazioni si perdono a 300, 200, 150 DPI | **MISURATO IN SIMULAZIONE** (1.11) — `scripts/bench_scansioni.py`, ripetibile (stessa impronta su tre esecuzioni) e con due controprove. **La risposta è che non è il DPI**: fra 300 e 100 DPI su una scansione pulita la copertura non peggiora; il crollo è sulla *fotocopia sbiadita a 200 DPI*, dove il 39% dei dati resta in chiaro **senza che nessuno lo dica**. PRIVACY.md aggiornato: la riga «quello che resta viene segnalato» non reggeva alla misura.<br><br>**AGGIORNAMENTO 2026-08-09 — misurato su scansioni vere, e declassato a bassa priorità.** `scripts/misura_degrado_reale.py` misura da scansioni reali i parametri che qui erano numeri scelti a mano; `scripts/spazzola_degrado.py` gira una manopola alla volta e misura **con lo stesso strumento** la pagina generata, così i due assi sono confrontabili invece che omonimi. Cosa si sa adesso: una scansione vera ha **contrasto 0,337** e **rumore 1,40** (4 pagine grezze di pubblico dominio; una sola fonte, quindi colloca e non tara). Il rumore **non ha effetto misurabile** su quasi tutto l'intervallo — il nostro era dieci volte troppo alto e non cambiava niente. Il contrasto invece decide tutto: la copertura tiene fino a ~0,34 e crolla subito sotto (92% → 79% → 62% → 0%). **Una scansione vera cade sul ciglio del dirupo.**<br><br>**Perché bassa priorità.** L'obbligo di dichiarare il limite è assolto: la tabella sta in PRIVACY.md, la landing dichiara il 47% e i 4 su 28, il README dice che quando l'OCR legge male il motore non può decidere bene. **Quel che resta è solo l'accuratezza di un numero già pubblicato**, e l'errore è piccolo e in una direzione sola: il profilo «ufficio» ha contrasto misurato 0,733 contro lo 0,337 del reale, quindi la riga «scanner in ordine → 89-97%» è misurata su una pagina **più facile della realtà** — circa 4 punti, un elemento su 24. La «fotocopia» simulata (0,408) è invece **vicina** al reale: la riga pessimistica è realistica, quella ottimistica no.<br><br>**Cosa resterebbe da fare**: ritarare i profili sui valori misurati e ripubblicare la tabella. Un corpus più grande e da più apparecchi servirebbe (Wikimedia ha bloccato le richieste a piena risoluzione dopo quattro pagine, chiedendo di non insistere) | **BASSA PRIORITÀ** — il limite è dichiarato, resta da correggere una lusinga di ~4 punti |

**Perché A.8 è fattibile senza peggiorare i falsi positivi.** Un IBAN ha un
checksum: si possono generare le varianti plausibili di una stringa dubbia e
accettarne una solo se il mod-97 torna. Lo stesso vale per il codice fiscale,
che ha un carattere di controllo. Su formati senza checksum questa strada non
si può percorrere, e infatti non va percorsa.

## P1-bis — Interfaccia in inglese (chiuso in 1.8.0)

Tradurre l'interfaccia era una **funzionalità**, non una passata di
traduzione, e andava fatta in un ordine preciso: prima il motore, poi le
parole.

| ID | Item | Note | Stato |
|----|------|------|-------|
| P1.6 | Estrarre le stringhe della UI in un dizionario `it` / `en` + selettore lingua | `mr_rao/i18n.py`: 326 chiavi fra template, JS e messaggi del server; lingua dedotta dal browser, scelta esplicita ricordata in un cookie | **DONE** (1.8.0) |
| P1.7 | **Prima** di P1.6: rendere i riconoscitori estendibili ad altri Paesi | Pacchetti `core` / `it` / `en`, cumulativi e selezionabili: 7 riconoscitori universali, 8 italiani, 8 anglosassoni. La priorità è per **tipo di dato** e non per pacchetto, così CF e SSN convivono | **DONE** (1.8.0) |

**Perché in quest'ordine.** L'inglese nell'interfaccia dice «questo strumento
è per te» a chi parla inglese. Se il filtro privacy avesse ignorato un
National Insurance Number o un SSN, la promessa sarebbe stata tradita nel
punto che conta di più. Per questo il motore è arrivato prima delle parole,
e non il contrario.

---

## Metriche di “fatto” per P0

Anche queste riscritte il 2026-08-07: la prima diceva «browser aperto entro
3s», che era la vecchia idea sbagliata di dove si debba finire.

- [ ] Click destro su un documento pulito → il `.md` compare accanto
      all'originale e la finestra si chiude, senza chiedere niente
- [ ] Click destro su un documento con dati personali → prima di chiudersi
      dice **quante** sostituzioni e **quanti** sospetti, e dove trovare il file
- [ ] Il conteggio dei sospetti compare anche da riga di comando
- [ ] Nessuna console che flasha e sparisce quando c'era qualcosa da leggere
- [ ] Funziona sia da install Python sia da portable exe  
