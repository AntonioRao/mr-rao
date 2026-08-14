# Contribuire a Mr. Rao

*This document in English: [CONTRIBUTING.en.md](CONTRIBUTING.en.md).*

Grazie per l'interesse. Prima una cosa da sapere, così non perdi tempo.

## La licenza

Mr. Rao è software libero sotto **GNU AGPL-3.0** ([LICENSE](LICENSE)).
Aprendo una pull request accetti che il tuo contributo venga distribuito sotto
la stessa licenza.

### E una cosa in più, dichiarata apertamente

Aprendo una pull request concedi anche ad **Antonio Andrea Rao**, titolare del
copyright del progetto, il diritto non esclusivo, perpetuo, irrevocabile,
gratuito e trasferibile di usare, modificare e licenziare il tuo contributo
**anche con termini diversi dall'AGPL** — licenze commerciali comprese, e
**compresa l'inclusione in prodotti distinti e anche proprietari**, non solo
in questo. Resti autore del tuo codice e mantieni ogni diritto di riusarlo
dove e come vuoi.

Nella stessa concessione rientra una **licenza sui brevetti**: se hai brevetti
che il tuo contributo violerebbe, concedi il diritto di usarlo senza doverteli
chiedere. Senza questa riga la concessione sul diritto d'autore lascerebbe in
piedi un'arma che non c'entra con il diritto d'autore, ed è il motivo per cui
la clausola sta anche nella licenza Apache e in ogni CLA serio.

E **dichiari due cose sul contributo**: che è tuo o che hai il diritto di
cederlo, e che non contiene codice preso da un progetto con una licenza
incompatibile. È la parte che a te non costa nulla e che al progetto serve
davvero: senza, ogni riga ricevuta è una scommessa sulla provenienza.

Il progetto si riserva anche l'uso del nome «Mr. Rao». **Il nome non è
coperto dall'AGPL**: chi copia il codice, e ne ha pieno diritto, non può
pubblicarlo con questo nome.

**Perché serve, detto senza giri di parole.** L'AGPL permette l'uso
commerciale, ma impone a chi modifica il programma o lo offre in rete di
pubblicare il proprio sorgente. Alcune aziende non possono accettare quel
vincolo e chiedono una licenza diversa. Concederla è possibile solo a chi
detiene *tutti* i diritti: basta un contributo senza questa clausola perché
quella strada si chiuda per l'intero progetto, e riaprirla vorrebbe dire
ritrovare ogni autore e chiedere il permesso a ognuno.

È la stessa clausola che usano Qt e MySQL, per la stessa ragione.

Se non ti va bene — ed è una posizione legittima, non un capriccio — scrivilo
nella pull request invece di accettare qualcosa che non condividi. Si trova un
altro modo: per esempio descrivere il difetto e lasciare che sia il progetto a
scrivere la correzione.

La clausola vale per **tutto** quello che entra nel repository. Prima diceva
«per i contributi di poche righe non ci interessa», e quella frase era un
buco: nessuno ha mai stabilito quante siano poche righe, e una funzione da
cinque righe è codice quanto una da cento. Un refuso o una parola cambiata
restano fuori lo stesso, ma perché **non sono opere dell'ingegno**, non
perché glielo concediamo noi.

**Come si accetta.** C'è una casella da spuntare nel modello di pull request
([`.github/pull_request_template.md`](.github/pull_request_template.md)).
Serve a lasciare una traccia datata dell'accettazione: una clausola che sta
solo in un file che nessuno è obbligato ad aprire vale poco il giorno in cui
qualcuno dice «io non l'ho mai letta».

In pratica: usalo, modificalo, ridistribuiscilo. L'unico obbligo serio scatta
se lo offri ad altri via rete — in quel caso devi rendere disponibile il
sorgente della tua versione (articolo 13).

## Cosa è utile

Guarda il [backlog](docs/BACKLOG.md): è aggiornato e onesto su cosa manca.
In particolare sono benvenuti:

- **Riconoscitori per altri Paesi.** L'architettura in `mr_rao/privacy.py` è
  già a pattern + validatore: aggiungere NIF spagnoli o SIREN francesi è
  soprattutto lavoro di regole, non di impianto.
- **Falsi positivi e falsi negativi dell'anonimizzazione.** Se un dato personale
  ti è sfuggito, o un codice prodotto è stato scambiato per un IBAN, apri una
  issue con un esempio **inventato** (mai dati reali).
- **Anteprima Markdown.** Il renderer è in `static/js/markdown.js`, scritto in
  casa e provato da `node` dentro pytest. Se trovi un documento che rende male,
  il caso va aggiunto lì. Una regola non negoziabile: **non deve mai emettere
  un `<img>` remoto**, perché sarebbe una chiamata di rete partita dal
  documento che si sta anonimizzando.
- **Test.** Ce ne sono 2133 test e non bastano mai. (Il numero è scritto prima
  della parola «test» di proposito: è così che `scripts/check_docs.py` lo
  trova. Scritto al contrario era rimasto fermo a 161 per venti release.)

## Cosa serve prima di una PR

```bash
scripts\quality_gate.bat
```

Sono **sei** passi, e vale la pena saperli per nome: quando uno diventa rosso,
il messaggio dice quale.

1. `compileall` — la sintassi;
2. `scripts/check_import.py` — l'import di ogni modulo, uno per uno. Un import
   circolare supera il passo 1 a pieni voti;
3. `mr_rao.cli health` — le dipendenze ci sono e si caricano;
4. `scripts/gen_third_party.py --check` — le licenze di terze parti sono
   allineate ai pacchetti installati;
5. `pytest`;
6. `scripts/check_docs.py` — i documenti pubblicati dicono ancora la verità:
   versioni, conteggi di test, link, segnaposto, opzioni della riga di comando.

### Il gate pre-commit, se lo vuoi

C'è un hook `pre-commit` **opzionale**: nessuno te lo installa alle spalle,
lo attivi tu e lo togli quando vuoi.

```bash
venv\Scripts\python scripts\install_hooks.py --install
venv\Scripts\python scripts\install_hooks.py --status
venv\Scripts\python scripts\install_hooks.py --uninstall
```

Non copia niente dentro `.git/hooks`: punta `core.hooksPath` a `.githooks/`,
così l'hook che gira è sempre quello del repository e non una copia vecchia
rimasta sul tuo computer. Disinstallare è togliere quella riga di
configurazione.

**Cosa esegue, e perché non tutto il gate.** Solo `compileall` e
`scripts/check_import.py`: insieme mezzo secondo. Il gate completo ne costa
una ventina, quasi tutti di pytest — e venti secondi a ogni commit non sono
tanti in assoluto, sono tanti nel punto sbagliato. Un hook lento non viene
tolto, viene aggirato: si impara `--no-verify` e da quel momento non gira più
nemmeno la metà veloce. Quindi l'hook risponde a una sola domanda, quella che
ha senso fare a ogni commit: *questo albero si carica?* Se vuoi anche i test:

```bash
MR_RAO_HOOK_FULL=1 git commit ...
```

Quella variabile aggiunge **pytest e nient'altro** (`.githooks/pre-commit`):
non è «tutto il gate». Licenze e documenti pubblicati restano fuori dall'hook
in ogni caso, e si controllano lanciando `scripts\quality_gate.bat`.

Due cose dette apertamente invece di lasciartele scoprire:

- l'hook controlla **l'albero di lavoro**, non l'indice. Se hai modifiche
  `.py` fuori stage, quello che viene controllato non è esattamente quello
  che stai committando — e te lo dice a schermo. Ricostruire l'indice in una
  copia separata sarebbe più esatto e molto più facile da sbagliare in modo
  distruttivo;
- **non sostituisce `scripts\quality_gate.bat`** prima di una pull request.

Se sviluppi su Linux o macOS: `.githooks/` è forzato a LF da `.gitattributes`.
Non è pedanteria di stile — uno shebang `#!/bin/sh` con un `\r` in coda su
Linux non parte affatto, e l'errore che ricevi è `not found`, che indica il
file e non la causa. Su Windows la `sh` di Git il `\r` lo tollera, quindi chi
lavora solo lì il difetto non lo vedrebbe mai e lo spedirebbe agli altri.

Tre regole che il progetto si è dato dopo averle pagate care:

0. **Non escono funzioni senza documentazione.** Non è buona volontà, è una
   condizione del gate. È successo due volte: il pacchetto anglosassone è
   uscito nella 1.8.0 con dieci riconoscitori mai entrati nella tabella di
   `PRIVACY.md`, e i documenti d'identità sono stati spediti mentre il
   backlog li dava ancora da fare. In entrambi i casi il gate diceva verde,
   perché guardava versioni, conteggi e link — cose che con una funzione
   nuova non c'entrano niente.

   Ora `scripts/check_docs.py` verifica due cose che con una funzione nuova
   c'entrano eccome:

   - ogni **segnaposto** che il motore può emettere è nella tabella di
     `docs/PRIVACY.md`. Un riconoscitore nuovo ne porta uno nuovo, e da lì
     non si scappa;
   - ogni **opzione della riga di comando** è in `docs/CLI.md`. Il parser
     viene interrogato, non letto con un'espressione regolare: un controllo
     che approssima ciò che verifica si perde proprio il caso scritto in un
     modo che non aveva previsto.

   Entrambi i controlli sono stati visti fallire prima di essere creduti.


1. **Un test di regressione va verificato fallire sul codice di prima.**
   Un test che passa anche col bug non dimostra nulla. Se correggi qualcosa,
   togli la correzione, guarda il test diventare rosso, rimettila.

2. **Le licenze non si scrivono a mano.** Se aggiungi una dipendenza, rigenera
   l'elenco:
   ```bash
   venv\Scripts\python scripts\gen_third_party.py
   ```
   E se la dipendenza è copyleft (LGPL, MPL, GPL), aggiungi anche testo e
   notice in `licenses/`, come è stato fatto per **pystray** (LGPL-3.0) —
   oggi l'unica che richiede una cartella dedicata. Le MPL-2.0 presenti
   (`certifi`, `tqdm`) stanno in `THIRD_PARTY.md` fra gli obblighi
   particolari, con il rimando al progetto: MPL chiede di dire dove trovare
   il sorgente, non di allegarlo.
   Il gate controlla l'allineamento, non la completezza degli adempimenti:
   quella resta responsabilità di chi aggiunge.

## Stile

- Codice e commenti in inglese; testi rivolti all'utente in italiano.
- I commenti spiegano **perché**, non cosa: il cosa si legge dal codice.
- Niente dipendenze nuove senza una ragione forte. Ogni pacchetto in più è
  peso nel portable e una licenza in più da rispettare.

## Segnalare un bug

Servono tre righe: cosa hai fatto, cosa ti aspettavi, cosa è successo.
Con formato del file e versione (la trovi nel piè di pagina o con
`python -m mr_rao.cli --version`).

**Non allegare mai documenti reali.** Se serve un campione, costruiscine uno
finto: il progetto esiste proprio per non far girare i documenti veri.
