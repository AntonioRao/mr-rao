# Backlog & piano di priorità — Mr. Rao

Lo stato delle voci vale alla **1.10.0**, piu' il lavoro gia' su `main` e non ancora rilasciato (segnato «1.11»). La fonte di verità resta git e il
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
| P3.8 | **Microsoft Store (MSIX), l'unica strada gratuita che toglie davvero l'avviso di SmartScreen** | Chi installa dallo Store non vede nessun avviso: il pacchetto lo firma Microsoft. E dal 2026 l'account sviluppatore è **gratuito**, per individui e per aziende. Ma non è un passo di confezionamento, è un **riadattamento dell'integrazione col sistema**: in MSIX i registri sono virtualizzati, quindi il menu contestuale non si scrive più con lo script PowerShell ma si **dichiara nel manifesto** (`windows.fileTypeAssociation`); il collegamento sul Desktop non esiste per costruzione (solo voce nel menu Start); e l'installatore `.bat` sparisce. Servono manifesto, icone in tutte le misure, `MakePri`, e il superamento della certificazione. Da verificare anche l'attrito noto fra i termini di licenza dello Store e le licenze della famiglia GPL. **Non risolve il percorso principale**: chi scarica lo zip da GitHub vede l'avviso esattamente come prima | **IN CORSO** — nome «Mr. Rao» prenotato su Partner Center (Store ID `9N7SJ4W88KQC`), manifesto in `packaging/AppxManifest.xml` con l'identita' vera assegnata dallo Store e le dieci associazioni di file dichiarate. **Scadenza: la prenotazione del nome decade se l'app non viene inviata entro tre mesi (dal 2026-08-09, quindi entro il 2026-11-09).** Mancano: icone in tutte le misure richieste, `MakeAppx`/`MakePri` nel workflow, e la catena di pubblicazione (registrazione Azure AD + associazione a Partner Center + azione `microsoft/store-submission`). Il *client secret* lo crea e lo incolla nei GitHub Secrets l'autore: non passa da qui |
| P3.7 | **L'OCR incolla il dato all'etichetta, e il riconoscitore non parte** | Trovato dal banco delle scansioni (A.9), non immaginato. Sui documenti degradati l'OCR perde lo spazio e produce `IBANIT60X0542811101000000123456`, `Tel.02 1234567`, un numero di carta attaccato ai puntini di guida di un modulo, `NT86O02008…` con «IT» letto «NT». In tutti e quattro i casi il dato **passerebbe il proprio validatore** — il mod-97 e il Luhn tornano — ma il pattern non arriva nemmeno a proporlo, perché i lookbehind `(?<![\w.+])` lo rifiutano quando è preceduto da lettere o da un punto. Risultato: **perdita silenziosa**, nemmeno un sospetto. Allentare quei lookbehind è facile; farlo **senza pagare falsi positivi** va misurato sui 127 documenti a verità zero prima di toccare qualsiasi cosa | TODO |
| P3.6 | **NER opzionale per i nomi (modello ONNX leggero)** | Serve a una cosa sola che le liste non possono fare: leggere il **ruolo nella frase**. «Lavoro a Milano» e «ho parlato con Mario Milano» contengono la stessa parola, e oggi il motore o la lascia passare o la segna come sospetto. Il guadagno è sui cognomi che coincidono con parole comuni — Chiesa, Costa, Monte, Villa. **Il costo va detto:** un modello fa sparire il *perché*. Oggi ogni sostituzione ha una regola citabile e due esecuzioni danno lo stesso esito; un modello dà un punteggio, e il giorno che sbaglia non si può spiegare a un cliente perché un nome è rimasto. Quindi: spento di default, **mai al posto** dei validatori — il modello propone, contesto e aritmetica decidono, i sospetti restano. Vedi issue #4. **Precisazione (2026-08-09): non serve installare nessuna «AI».** `onnxruntime` è già una dipendenza dichiarata dalla 1.9.0 e RapidOCR porta con sé 30,3 MB di modelli `.onnx` che girano già oggi in locale, offline, sul processore: un NER sarebbe un altro file caricato dalla stessa libreria. Il costo vero è altrove — peso nel portable (15–60 MB), una licenza in più da rispettare, e la riga «Nessun modello» che i due README e la landing usano come argomento di vendita | TODO |

---

## P4 — Debito tecnico

| ID | Item | Stato |
|----|------|--------|
| P4.1 | Rinominare cartella repo `markitdown-webapp` → `mr-rao` | TODO |
| P4.2 | Rimuovere shim MarkItDown quando nessuno li usa più | **NON SI APPLICA** — verificato: nei sorgenti non è rimasto nessuno shim, MarkItDown è una dipendenza viva. I ponti di compatibilità superstiti sono altri e hanno ancora senso: `paddleocr`→`rapidocr`, `--no-name-guess` che non fa niente, `file1`/`file2` nella rotta di confronto. Toglierli romperebbe script altrui senza guadagnarci nulla |
| P4.3 | Spezzare `app.js` in moduli ES se cresce ancora | TODO |
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
| A.9 | Banco di prova con scansioni a qualità decrescente | Serve un numero, non un'impressione: quante redazioni si perdono a 300, 200, 150 DPI | **MISURATO IN SIMULAZIONE** (1.11) — `scripts/bench_scansioni.py`, ripetibile (stessa impronta su tre esecuzioni) e con due controprove. **La risposta è che non è il DPI**: fra 300 e 100 DPI su una scansione pulita la copertura non peggiora; il crollo è sulla *fotocopia sbiadita a 200 DPI*, dove il 39% dei dati resta in chiaro **senza che nessuno lo dica**. PRIVACY.md aggiornato: la riga «quello che resta viene segnalato» non reggeva alla misura. **Non è chiuso**: la carta è simulata, servono scansioni vere |

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
