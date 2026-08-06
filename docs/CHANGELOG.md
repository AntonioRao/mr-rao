# Changelog

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
