# Backlog & piano di priorità — Mr. Rao

Lo stato delle voci vale alla **1.12.0**. La fonte di verità resta git e il
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
| P1.5 | Mobile / narrow viewport polish | Uso da tablet | TODO |
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
| P3.4 | Portable firmato / zip release versionato | Distribuzione team | **METÀ FATTA** (1.11) — archivio versionato, archivio a nome fisso e `SHA256SUMS.txt`. Il nome fisso **non deve cambiare**: è ciò che tiene in piedi `/releases/latest/download/...` nei README e nella landing, e la versione la porta già il tag. La **firma** resta fuori: richiede un certificato, e Azure Trusted Signing non valida gli individui nell'UE. Alternativa gratuita da valutare: SignPath Foundation — ma il publisher che Windows mostra è «SignPath Foundation», non l'autore |
| P3.5 | **Documenti d'identità: carta d'identità, patente, passaporto** | Oggi non c'è nessun riconoscitore. Sono fra i dati più sensibili che passano da uno studio, e hanno formati regolari — la patente italiana ha una struttura fissa, il passaporto una riga MRZ leggibile a vista. Va fatto col metodo di casa: il pattern propone, un validatore decide, e il verbale amministrativo deve restare a zero | **DONE** (1.11) — carta d'identità elettronica, patente e passaporto, interruttore proprio (`documenti`), non dentro `fiscal`. Questi numeri **non hanno una cifra di controllo** e la loro forma è identica a quella di mille protocolli: si sostituiscono solo con il tipo di documento scritto vicino, altrimenti diventano un sospetto. Sui 127 documenti a verità zero: zero sostituzioni sbagliate |
| P3.8 | **Microsoft Store (MSIX), l'unica strada gratuita che toglie davvero l'avviso di SmartScreen** | Chi installa dallo Store non vede nessun avviso: il pacchetto lo firma Microsoft. E dal 2026 l'account sviluppatore è **gratuito**, per individui e per aziende. Ma non è un passo di confezionamento, è un **riadattamento dell'integrazione col sistema**: in MSIX i registri sono virtualizzati, quindi il menu contestuale non si scrive più con lo script PowerShell ma si **dichiara nel manifesto** (`windows.fileTypeAssociation`); il collegamento sul Desktop non esiste per costruzione (solo voce nel menu Start); e l'installatore `.bat` sparisce. Servono manifesto, icone in tutte le misure, `MakePri`, e il superamento della certificazione. Da verificare anche l'attrito noto fra i termini di licenza dello Store e le licenze della famiglia GPL. **Non risolve il percorso principale**: chi scarica lo zip da GitHub vede l'avviso esattamente come prima | **IN CORSO** — nome «Mr. Rao» prenotato su Partner Center (Store ID `9N7SJ4W88KQC`), manifesto in `packaging/AppxManifest.xml` con l'identita' vera assegnata dallo Store e le dieci associazioni di file dichiarate. **Scadenza: la prenotazione del nome decade se l'app non viene inviata entro tre mesi (dal 2026-08-09, quindi entro il 2026-11-09).** Mancano: icone in tutte le misure richieste, `MakeAppx`/`MakePri` nel workflow, e la catena di pubblicazione (registrazione Azure AD + associazione a Partner Center + azione `microsoft/store-submission`). **AGGIORNAMENTO 2026-08-09: la prima sottomissione è partita.** Icone, `MakeAppx` nel workflow, scheda in italiano e inglese, classificazione IARC (PEGI 3), giustificazione di `runFullTrust` e note per il collaudo: tutto fatto e inviato. Stato: **in certification** (Submission ✓, Pre-processing ✓). La scadenza della prenotazione è rispettata. Cosa resta è in **P3.9** e **P3.10**. Procedura reale, con i cinque punti in cui la mia guida sbagliava, in [STORE.md](STORE.md) |
| P3.7 | **L'OCR incolla il dato all'etichetta, e il riconoscitore non parte** | Trovato dal banco delle scansioni (A.9), non immaginato. Sui documenti degradati l'OCR perde lo spazio e produce `IBANIT60X0542811101000000123456`, `Tel.02 1234567`, un numero di carta attaccato ai puntini di guida di un modulo, `NT86O02008…` con «IT» letto «NT». In tutti e quattro i casi il dato **passerebbe il proprio validatore** — il mod-97 e il Luhn tornano — ma il pattern non arriva nemmeno a proporlo, perché i lookbehind `(?<![\w.+])` lo rifiutano quando è preceduto da lettere o da un punto. Risultato: **perdita silenziosa**, nemmeno un sospetto. Allentare quei lookbehind è facile; farlo **senza pagare falsi positivi** va misurato sui 127 documenti a verità zero prima di toccare qualsiasi cosa | TODO |
| P3.6 | **NER opzionale per i nomi (modello ONNX leggero)** | Serve a una cosa sola che le liste non possono fare: leggere il **ruolo nella frase**. «Lavoro a Milano» e «ho parlato con Mario Milano» contengono la stessa parola, e oggi il motore o la lascia passare o la segna come sospetto. Il guadagno è sui cognomi che coincidono con parole comuni — Chiesa, Costa, Monte, Villa. **Il costo va detto:** un modello fa sparire il *perché*. Oggi ogni sostituzione ha una regola citabile e due esecuzioni danno lo stesso esito; un modello dà un punteggio, e il giorno che sbaglia non si può spiegare a un cliente perché un nome è rimasto. Quindi: spento di default, **mai al posto** dei validatori — il modello propone, contesto e aritmetica decidono, i sospetti restano. Vedi issue #4. **Precisazione (2026-08-09): non serve installare nessuna «AI».** `onnxruntime` è già una dipendenza dichiarata dalla 1.9.0 e RapidOCR porta con sé 30,3 MB di modelli `.onnx` che girano già oggi in locale, offline, sul processore: un NER sarebbe un altro file caricato dalla stessa libreria. Il costo vero è altrove — peso nel portable (15–60 MB), una licenza in più da rispettare, e la riga «Nessun modello» che i due README e la landing usano come argomento di vendita | **APPROVATO il 2026-08-09, da fare** — vedi la scheda «P3.6: la decisione e i suoi vincoli» qui sotto |
| P3.9 | **Il link allo Store, e la sezione sull'avviso di Windows da riscrivere** | Due cose, e la seconda conta più della prima. Il link `https://apps.microsoft.com/detail/9N7SJ4W88KQC` è già definitivo — lo Store ID non cambia — ma **oggi risponde `410 Gone`**: verificato, non supposto. Pubblicarlo prima vorrebbe dire un pulsante morto proprio sulla strada della fiducia, quella che esiste per togliere l'avviso «editore sconosciuto»: chi ci clicca è la persona più diffidente, e troverebbe un errore. È lo stesso modo di rompersi in silenzio da cui nasce la disciplina del nome fisso `MrRao-Portable.zip`. **Quando risponde `200`**: aggiungere il link (non sostituire la portable, che resta la strada principale) e **riscrivere la sezione sull'avviso di Windows nei due README** — oggi dice solo «ecco come si supera», da allora potrà dire «installalo dallo Store e non compare». Il pulsante di scaricamento sta in 17 punti su 7 file, ma il link Store va in pochi punti scelti. Controllo: `curl -sS -o /dev/null -w "%{http_code}" -L https://apps.microsoft.com/detail/9N7SJ4W88KQC` | TODO (attende la certificazione) |
| P3.10 | **La catena di pubblicazione automatica non è mai stata eseguita** | Configurata il 2026-08-09: i quattro segreti ci sono e la registrazione Entra ha il suo ruolo. Ma **configurata non è provata**: la prima volta che si scriverà `si` in `pubblica_store` sarà anche la prima volta che quel percorso gira davvero. Va lanciata guardando l'esecuzione, non a fine giornata. **Il punto più probabile di rottura è il ruolo:** è stato assegnato `Developer` e non `Manager`, di proposito — Manager dà accesso completo all'account e permette di gestire utenti e tenant, che su una credenziale dentro GitHub Secrets è sproporzionato. Se fallisse per permessi, il ruolo si allarga in pochi secondi da Partner Center: meglio allargarlo con una prova in mano che stringerlo dopo un incidente | TODO |
| P3.11 | **«Nessun modello» non è vero già oggi, e va riscritto prima di qualunque NER** | Emerso parlando di P3.6, ma **non dipende da P3.6**: è una promessa pubblica sbagliata adesso. `README.it.md` dice «Il riconoscimento è codice, non una rete neurale… niente da scaricare»; `PRIVACY.md` dice «Nessun modello, nessuna rete neurale». Intanto **RapidOCR spedisce ~30 MB di modelli `.onnx` dentro il portable**, ed è una rete neurale che gira su ogni scansione. Dire «nessun modello **AI**» peggiora le cose: un modello OCR *è* un modello AI, e la frase diventerebbe più precisa e più falsa. La cosa vera, che è anche il valore vero, riguarda **la decisione**: l'OCR trasforma pixel in testo e non decide niente; cosa sia un dato personale lo decidono regole e aritmetica, a valle. È lo stesso principio di casa — il pattern propone, il validatore decide — e spiega perché il banco A.9 trova quello che trova: quando l'OCR legge male, il motore non può decidere bene (vedi P3.7). Riscrivere in README.it.md, README.md, PRIVACY.md e nelle due landing che la citano. **Nella stessa passata**: `02-carta-bianca.html` dice ancora «390+ test», fermo a venti release fa | TODO |

---

| P3.12 | **Landing in inglese, non una traduzione** | Siamo bilingui ovunque tranne che sulla porta d'ingresso: README, interfaccia, documento prodotto e scheda Microsoft Store esistono in due lingue, la landing **solo in italiano** (`<html lang="it">` su tutti e tre i file tracciati). Il motore riconosce NHS number, National Insurance number, SSN, ITIN, routing ABA, SIN, ABN, TFN, codice postale britannico e la riga MRZ dei passaporti: è stato costruito **anche** per chi non è italiano, e quella persona arriva su una pagina che non può leggere. **Non è una traduzione**: la pagina italiana si regge su esempi che a un lettore straniero non dicono niente — Gazzetta Ufficiale, Agenzia delle Entrate, il codice fiscale come esempio principale. La pagina inglese deve **partire dai formati anglosassoni** e usare le prove che li riguardano davvero: i **99 moduli fiscali statunitensi** fra i documenti a verità zero e i **1 500 messaggi in inglese** del corpus di prosa. Più corta, e con meno cose. **⚠ IL VINCOLO DI ONESTÀ, che è la cosa più facile da perdere qui:** il riconoscimento dei nomi in inglese è **deliberatamente più stretto** di quello italiano — lo dice già `README.md:32` — e una pagina inglese che promettesse la stessa copertura sarebbe la bugia peggiore possibile, perché la farebbe proprio a chi non può verificarla leggendo gli esempi. Serve anche `hreflang` fra le due pagine e un rimando dai README. Il gate ora copre le landing tracciate (vedi P3.13), quindi la pagina nuova ci entra da sola.<br><br>**QUALE PAGINA VEDE CHI ARRIVA** (deciso il 2026-08-09): browser in italiano → pagina italiana; **qualunque altra lingua → inglese**. Non «inglese solo per l'inglese»: l'inglese è la lingua di ripiego per tutto il resto del mondo, l'italiano è il caso speciale.<br><br>**Il selettore di lingua resta in alto**, nello stesso stile degli altri pulsanti e **accanto a «Scarica»** — non un link di servizio in fondo alla pagina: chi arriva sulla pagina sbagliata deve vedere subito come cambiarla.<br><br>**⚠ Il vincolo tecnico da sapere prima di cominciare, non dopo:** la landing è **statica** su Cloudflare Pages, e la pagina ha una **CSP con le impronte degli inline calcolate da `_rebuild.py`**. Quindi: (a) leggere `Accept-Language` va fatto lato server con una Pages Function (`functions/_middleware.js`), perché `_redirects` non sa condizionare sulla lingua; (b) un rimando fatto in JavaScript costerebbe un lampo di pagina sbagliata, non funzionerebbe senza JS, e **richiederebbe di rigenerare le impronte CSP**; (c) la scelta fatta col selettore deve restare, altrimenti il rimando automatico la annulla al ricaricamento | TODO |
| P3.13 | **Il corpus dei 127 documenti non è nel repository, e nessun test lo esercita** | Scoperto lavorando a P3.7. «127 documenti a verità zero» è l'affermazione su cui poggiano i numeri più forti che pubblichiamo — sta nei due README, in `PRIVACY.md`, in `ARCHITECTURE.md`, nella landing e ora anche nella scheda del Microsoft Store. Ma in `tests/dati/` ci sono tre corpora di **testo** e nessuno dei 127; nessun test li apre. **L'affermazione non è falsa** — le misure sono state fatte davvero — ma **non è riproducibile da chi legge il repository**, e non c'è niente che si accorga se un giorno smettesse di valere. Su un progetto la cui disciplina è «le affermazioni dei documenti sono sotto test», è l'eccezione proprio dove peserebbe di più. **CHIUSO il 2026-08-09, per decisione dell'utente.** Il numero esatto è stato tolto da ogni documento: si dice **«oltre cento documenti amministrativi pubblici»** e basta. Non è un ripiego — dire *cosa sono* è più utile di dire *quanti*: chi volesse rifare la misura sa da dove partire, mentre «127» prometteva una verificabilità che non c'era.<br><br>La motivazione, che vale anche per le prossime volte: *«non è che ogni cosa debba essere dimostrabile, già siamo eccessivamente trasparenti, il codice è lì a disposizione»*. È una posizione difendibile — le misure sono state fatte davvero, e il motore è pubblico e ispezionabile riga per riga.<br><br>**Cosa NON è stato fatto, e perché è giusto così**: le misure precise che vengono da quel corpus restano al loro posto (2 739 sostituzioni sbagliate sulla soglia prosa/modulo, 8 904 di `name_guess`, zero sui documenti d'identità). Cancellarle avrebbe tolto **il perché** da quelle decisioni, lasciando scritto «pretendiamo due riscontri sui moduli» senza più la ragione. Toccato: i due README, `ARCHITECTURE.md`, `PRIVACY.md`, `CHANGELOG.md`, il commento in `mr_rao/privacy.py` e le due landing | **CHIUSO** |
| P3.14 | **Il banco sotto-conta i dati segnalati** | Trovato da P3.7. `_sospetto_copre` in `scripts/bench_scansioni.py` confronta il campione **mascherato** del sospetto con il valore atteso: su un IBAN il cui codice paese è stato letto male (`NT86O…` invece di `IT86O…`) i primi due caratteri non coincidono, quindi il confronto fallisce e il dato viene contato **PERSA** anche se il motore lo ha regolarmente **segnalato**. Conseguenza: una parte di quello che pubblichiamo come «perso in silenzio» in realtà un avviso lo produce.<br><br>**CHIUSO COME DOCUMENTATO, il 2026-08-09.** Il **prodotto non ha nessun difetto**: il motore segnala regolarmente quel dato, ed è il metro che lo attribuisce male. Non c'è niente da correggere in `mr_rao/`.<br><br>Resta scritto qui perché **un numero pubblicato eredita l'errore**: la quota «persa in silenzio» in `docs/PRIVACY.md` conta come persi anche dati che un sospetto lo producono. L'errore è quindi **pessimistico** — ci fa apparire peggiori di quanto siamo — che è la direzione innocua, e il motivo per cui non vale una correzione urgente. Ma se un giorno quei numeri miglioreranno all'improvviso senza che nessuno abbia toccato il motore, **la spiegazione è questa**, ed è meglio trovarla scritta che ricostruirla | **CHIUSO** (documentato, nessun difetto nel prodotto) |

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
| P4.6 | **Su touch le spiegazioni dell'interfaccia non esistono** | Trovato facendo P1.5. I suggerimenti `data-tip` — circa quaranta, e sono il posto dove il prodotto spiega **perché** fa quello che fa — si aprono su `mouseover` (`static/js/app.js` ~883). Senza mouse non c'è modo di aprirli: su telefono e tablet sono di fatto invisibili. Nessuna regola CSS può supplire, serve un gestore per il tocco. Su un prodotto che si difende spiegandosi, perdere le spiegazioni proprio dove lo schermo è piccolo è il caso peggiore | TODO |
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

```
A.9  (in parallelo: aspetta dei documenti, non del codice)
 │
P0.1 → P0.2 → P0.3 → P0.4
 │
P1.8 → P1.4 / P1.5
 │
P2.9 → P2.2 / P2.3 / P2.4
 │
P3 solo se richiesta esplicita
```

**A.9 sta fuori dalla catena perché non dipende da noi.** È l'unica voce che
può togliere un limite oggi dichiarato: PRIVACY.md ammette che il banco OCR
è sintetico, cioè che l'efficacia sulle scansioni è *stimata, non misurata*.
Per misurarla servono documenti passati davvero da uno scanner — e finché
non ci sono, quella riga in PRIVACY.md deve restare dov'è.

**P0 resta in cima fra le cose che dipendono da noi**: è l'unica che
l'utente incontra tutti i giorni, ed è ferma da più release di ogni altra.

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
| A.9 | Banco di prova con scansioni a qualità decrescente | Serve un numero, non un'impressione: quante redazioni si perdono a 300, 200, 150 DPI | **MISURATO IN SIMULAZIONE** (1.11) — `scripts/bench_scansioni.py`, ripetibile (stessa impronta su tre esecuzioni) e con due controprove. **La risposta è che non è il DPI**: fra 300 e 100 DPI su una scansione pulita la copertura non peggiora; il crollo è sulla *fotocopia sbiadita a 200 DPI*, dove il 39% dei dati resta in chiaro **senza che nessuno lo dica**. PRIVACY.md aggiornato: la riga «quello che resta viene segnalato» non reggeva alla misura.<br><br>**AGGIORNAMENTO 2026-08-09 — misurato su scansioni vere, e declassato a bassa priorità.** `scripts/misura_degrado_reale.py` misura da scansioni reali i parametri che qui erano numeri scelti a mano; `scripts/spazzola_degrado.py` gira una manopola alla volta e misura **con lo stesso strumento** la pagina generata, così i due assi sono confrontabili invece che omonimi. Cosa si sa adesso: una scansione vera ha **contrasto 0,337** e **rumore 1,40** (4 pagine grezze di pubblico dominio; una sola fonte, quindi colloca e non tara). Il rumore **non ha effetto misurabile** su quasi tutto l'intervallo — il nostro era dieci volte troppo alto e non cambiava niente. Il contrasto invece decide tutto: la copertura tiene fino a ~0,34 e crolla subito sotto (92% → 79% → 62% → 0%). **Una scansione vera cade sul ciglio del dirupo.**<br><br>**Perché bassa priorità.** L'obbligo di dichiarare il limite è assolto: la tabella sta in PRIVACY.md, la landing dichiara il 45% e i 4 su 29, il README dice che quando l'OCR legge male il motore non può decidere bene. **Quel che resta è solo l'accuratezza di un numero già pubblicato**, e l'errore è piccolo e in una direzione sola: il profilo «ufficio» ha contrasto misurato 0,733 contro lo 0,337 del reale, quindi la riga «scanner in ordine → 89-97%» è misurata su una pagina **più facile della realtà** — circa 4 punti, un elemento su 24. La «fotocopia» simulata (0,408) è invece **vicina** al reale: la riga pessimistica è realistica, quella ottimistica no.<br><br>**Cosa resterebbe da fare**: ritarare i profili sui valori misurati e ripubblicare la tabella. Un corpus più grande e da più apparecchi servirebbe (Wikimedia ha bloccato le richieste a piena risoluzione dopo quattro pagine, chiedendo di non insistere) | **BASSA PRIORITÀ** — il limite è dichiarato, resta da correggere una lusinga di ~4 punti |

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
