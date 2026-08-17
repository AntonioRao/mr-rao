# Tutela del codice di Mr. Rao

Come sono applicate a questo progetto le misure descritte in `TUTELA-CODICE-METODO.md` (metodo
generale, riusabile — cartella di lavoro OneDrive), con i comandi, i numeri misurati e i limiti.

Premessa che vale più di tutto il resto, e qui più che altrove: **nessuna di queste misure impedisce
la copia**. Mr. Rao è un repository **pubblico** sotto AGPL-3.0 — la copia è già legale, l'ha resa
tale la licenza stessa. Le misure qui sotto non promettono di impedirla: rendono visibile, con un
comando, quando quella copia non rispetta gli obblighi che l'AGPL porta con sé (attribuzione, stessa
licenza sulle modifiche, sorgente disponibile a chi usa il servizio in rete).

## Superficie esposta, e perché solo due misure su quattro

| | |
|---|---|
| **Leggibile da chiunque** | l'intero repository. Codice, storia, commit: non c'è una parte nascosta da proteggere |
| **Servizio in rete** | nessuno. Il server Flask è **loopback-only** (`127.0.0.1`); l'unica superficie pubblica sono le pagine statiche di marketing (`docs/landing/publish/`), che non contengono il motore |
| **Consegne a destinatari identificabili** | nessuna. La distribuzione è download anonimo (GitHub Releases, Microsoft Store) |

Da questo: **1 e 2 hanno senso, 3 e 4 no.**

- **1 (intestazione) e 2 (impronte)** servono a far valere l'AGPL — dimostrare provenienza e
  segnalare l'assenza di attribuzione — che è esattamente il bersaglio giusto per un repository
  pubblico dove la copia è lecita.
- **3 (canarini) non ha un posto sensato.** Un canarino verificabile a distanza (il caso più forte,
  vedi il metodo) richiede un servizio in rete che risponda con qualcosa di verificabile — Mr. Rao non
  ne ha uno pubblico che esponga il motore. Un canarino "solo nel codice" degraderebbe alla stessa
  utilità di un'impronta in più, senza il vantaggio della verifica senza credenziali: non vale la
  complessità aggiuntiva.
- **4 (marcatura per copia) non ha un bersaglio.** Serve quando ci sono consegne a soggetti
  identificabili da distinguere l'uno dall'altro. Qui la distribuzione è anonima: non c'è "il
  destinatario X" a cui imputare una fuga, quindi non c'è niente da marcare in modo differenziato.

## 1 · Intestazione legale — `scripts/marca_copyright.py`

Titolare, anno, `SPDX-License-Identifier: AGPL-3.0-or-later` e il rimando alla licenza, in cima a
**167 sorgenti di prima parte** (`.py`, `.ps1`, `.sh`, `.bat`, `.js`, `.css`, `.html`).

```bash
python scripts/marca_copyright.py            # elenca cosa farebbe
python scripts/marca_copyright.py --scrivi   # applica (idempotente)
```

Esito all'applicazione (2026-08-16): **165 marcati**, **2 già a posto** (`app.py`,
`mr_rao/__init__.py` portavano già una nota AGPL completa in prosa inglese — riconosciuta e non
duplicata). Rilanciato subito dopo: 167/167 già marcati, zero scritture — idempotenza confermata.

Esclusi per costruzione: `docs/landing/publish/` (output **rigenerato** da `_rebuild.py` — marcare
l'output vorrebbe dire perdere l'intestazione alla build successiva senza che nessuno se ne accorga;
il sorgente vero, in `docs/landing/`, è marcato). Non c'è codice vendorizzato nel repository (le
dipendenze Python arrivano da pip, dichiarate in `THIRD_PARTY.md`): marcare codice altrui sarebbe
**falsa attribuzione**, lo stesso illecito da cui ci si difende, al contrario. Lo shebang, la riga di
codifica e `@echo off`/`chcp` nei `.bat` restano in cima; il BOM si conserva se un file lo ha già; il
testo dell'intestazione è ASCII puro per non introdurre in un `.ps1` senza BOM il primo carattere che
PowerShell 5.1 non saprebbe leggere.

**Effetto collaterale reale, trovato e risolto.** Tre file del motore di redazione
(`mr_rao/privacy.py`, `en_formats.py`, `it_names.py`) sono tracciati per contenuto SHA-256 da
`corpus/atteso.json` (misura 2 anni luce di distanza da questa: serve a tenere allineata
un'implementazione TypeScript separata, per un altro prodotto). L'intestazione ne cambia i byte,
quindi ne cambia l'impronta di contenuto — non il comportamento: rigenerato con
`scripts/esporta_corpus_conformita.py` e verificato a diff che **sono cambiati solo i tre hash**, gli
stessi 290 casi di prova producono le stesse 290 uscite. Anche `docs/landing/publish/*.html` è stato
rigenerato con `_rebuild.py` per lo stesso motivo: i sorgenti HTML marcati non corrispondevano più
all'output già pubblicato.

## 2 · Catalogo di impronte — `scripts/impronte.py`

**23 impronte** congelate in `provenance/impronte.json` (privato, ignorato da git): frasi
caratteristiche dei commenti italiani, identificatori inusuali, stringhe d'interfaccia — su
`mr_rao/` (core, 11), `static/js/` (web, 3), `scripts/` (4), `tests/` (3), i tre entry point in
radice (`avvio`, 2).

```bash
python scripts/impronte.py raccogli   # una volta sola; --rifai per ricominciare
python scripts/impronte.py verifica   # sono ancora tutte nel codice?
python scripts/impronte.py cerca      # le cerca su GitHub code search
```

Due quote non riempite, e lo dice da sé invece di tacerlo: `web/identificatore` (0 su 1) e
`web/interfaccia` (0 su 2) — i due file JS del front-end (1.686 righe in tutto) hanno pochi commenti
lunghi e nessuna stringa d'interfaccia che superi il filtro di lunghezza e densità italiana.

Fuori dal catalogo, di proposito: l'intestazione di copyright (identica in 167 file), tutto ciò che
contiene cifre, versioni, URL, i nomi `Mr. Rao`/`rao`/`antonio`/`andrea`, e il testo che compare anche
in un documento pubblicato (`.md`, `.html`, `.txt` — **incluso** `docs/landing/publish/`: quella pagina
è online per scelta nostra, e una frase che sta anche lì non dimostra che il codice sia stato copiato).

**Linea di base al 2026-08-16: 23 impronte cercate, 22 pulite, 1 riscontro — verificato, e non è una
copia.** `imp-03` (`_intestazioni_di_sicurezza`, identificatore) compare in
`SkyMistery/Digital_vIPI`, repository italiano non collegato: è il nome di un test xUnit
(`Le_intestazioni_di_sicurezza_ci_sono`) che verifica la presenza degli header di sicurezza HTTP —
"intestazioni di sicurezza" è la traduzione italiana standard di *security headers*, un termine
tecnico comune, non un'espressione rara. Un identificatore da solo passa i filtri di lunghezza e
morfologia italiana ma non garantisce l'improbabilità per caso che garantisce una frase intera:
questa impronta è debole e va sostituita al prossimo `raccogli --rifai`. Le altre 22, tutte frasi
intere di 45+ caratteri, zero riscontri fuori dal repository.

Lo strumento è tarato prima di credergli: la frase di prova (`if __name__ == '__main__':`) dà
18.579.456 risultati su GitHub — la ricerca sa trovare, quindi uno zero sulle impronte vere è un
risultato, non un lettore rotto.

## Le guardie, e la prova che sanno dire di no

In `tests/test_tutela_codice.py`, tutte con controllo positivo (l'elenco esaminato non è mai vuoto
prima di dichiarare "tutto a posto"):

- ogni sorgente di prima parte porta l'intestazione — il rosso **nomina** quale file manca;
- ogni impronta del catalogo è ancora nei sorgenti — il rosso **nomina** quale manca e dov'era attesa;
- `provenance/impronte.json` è ignorato da git (verificato su un percorso **dentro** la cartella, non
  sulla cartella: `provenance/` potesse non esistere ancora e il test direbbe comunque "ignorato" per
  il motivo sbagliato);
- con `provenance/impronte.json` assente (il caso della CI, dove il materiale privato non arriva) i due
  controlli sulle impronte **dichiarano il salto**, non passano in silenzio.

**Mutazioni eseguite, tutte viste fallire, su file reali del repository** (non solo su copie
temporanee):

| Guardia | Mutazione | Esito |
|---|---|---|
| intestazioni | tolte le 5 righe di header da `scripts/check_docs.py` | rosso, nomina il file: `1 sorgenti senza intestazione di copyright: ['scripts/check_docs.py']` |
| intestazioni | ripristinato | verde |
| impronte | riscritta la riga di `imp-01` in `app.py` | rosso, nomina l'impronta: `1 impronte non piu' nel codice: ['imp-01']` |
| impronte | ripristinato | verde |
| skip CI | rinominato `provenance/impronte.json` (assenza simulata) | 2 test **saltati** con il motivo scritto, 7 passano lo stesso |

Più due mutazioni sintetiche, incorporate nella suite come regressione permanente (`tmp_path`, non
toccano file veri): un file senza intestazione deve tornare "marcato" (da fare), una frase tolta da un
sorgente deve spostarsi da "presenti" a "mancanti".

**Difetto vero, trovato da una di queste mutazioni prima del commit.** La prima versione di
`marca_copyright.py` controllava la nota in prosa AGPL *prima* di quella SPDX. L'intestazione SPDX che
lo strumento stesso scrive contiene la frase "GNU Affero General Public License" — quindi un file
appena marcato, ricontrollato, cadeva nel ramo prosa invece che in quello SPDX, e il ramo che
aggiorna l'anno di copyright diventava codice morto: non sarebbe mai scattato su un file marcato da
noi. Trovato dal test `test_un_file_gia_marcato_non_viene_segnalato_due_volte`, corretto invertendo
l'ordine dei due controlli.

## Limiti, per intero

- **Il catalogo protegge dal clone, non dalla copia del disco.** `provenance/` è ignorato da git: una
  copia del *repository* non se lo porta dietro, una copia del *filesystem* sì.
- **Un'impronta trovata non è una sentenza.** `imp-03` lo dimostra: un riscontro va sempre letto, non
  solo contato. Un identificatore isolato è più debole di una frase intera — la prossima raccolta
  dovrebbe preferire le frasi.
- **Contro chi riscrive partendo dalle idee, nessuna delle due funziona.** Funzionano contro chi copia
  file interi o porzioni ampie, che è il caso che l'AGPL regola esplicitamente (obbligo di rendere
  disponibile il sorgente delle modifiche).
- **L'intestazione non impedisce niente da sola.** È la premessa per una discussione su licenza, non
  una barriera tecnica: chi la toglie non commette un reato ulteriore rispetto a chi non rispetta già
  l'AGPL — ma toglie a sé stesso la difesa "non sapevo fosse coperto".

## Se ci fosse un sospetto, in ordine

1. `python scripts/impronte.py cerca` — se il codice è finito altrove, questo lo dice per primo;
2. su un riscontro: leggere il contesto (come per `imp-03`) prima di concludere qualunque cosa — un
   nome o una frase comuni possono coincidere per davvero;
3. `python scripts/impronte.py verifica` sul proprio albero prima di qualunque confronto, per essere
   certi che le impronte cercate esistano ancora davvero qui;
4. se il sospetto regge: il file o repository in questione manca dell'intestazione o dell'attribuzione
   richiesta dall'AGPL — la richiesta di conformità parte da lì, non da qui.
