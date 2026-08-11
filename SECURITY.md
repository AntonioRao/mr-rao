# Sicurezza

*This document in English: [SECURITY.en.md](SECURITY.en.md).*

## Modello di minaccia

Mr. Rao è un **tool locale monoutente**. Serve un server web perché
l'interfaccia sta nel browser, non perché sia un servizio di rete.

Cosa questo comporta:

- **Non c'è autenticazione.** Chiunque raggiunga la porta può convertire file
  e attivare il monitoraggio di una cartella.
- **Va tenuto su `127.0.0.1`.** È il default. `docker-compose.yml` pubblica la
  porta solo su localhost apposta.
- **Esporlo in rete è una scelta consapevole** e richiede un reverse proxy con
  autenticazione davanti. Senza, stai dando a chiunque un convertitore che
  scrive file sul tuo disco.

Un avvertimento su cosa Mr. Rao **non** è: non è una sandbox in cui aprire
allegati sospetti. Le librerie che usa per leggere PDF, Office e immagini sono
le stesse di qualunque altro programma, e girano senza isolamento. Aprici i
documenti che apriresti comunque — non quelli che non apriresti.

## Difese presenti

Un server su localhost è raggiungibile da **qualunque pagina** aperta nel
browser dell'utente. Attacchi distinti, controlli distinti:

| Attacco | Difesa |
|---------|--------|
| **DNS rebinding** — un dominio dell'attaccante che risolve a `127.0.0.1` per leggere le risposte | Header `Host` in allow-list (`MR_RAO_ALLOWED_HOSTS`), **anche quando si ascolta su `0.0.0.0`** |
| **CSRF** — una POST cross-site (multipart non richiede preflight CORS) che avvia una conversione o il monitoraggio di una cartella | `Sec-Fetch-Site` esterno rifiutato sui metodi che modificano stato, con `Origin` come ripiego |
| **Vicini di porta** — un'altra pagina su `127.0.0.1`, porta diversa: per `Origin` è lo stesso hostname | `Sec-Fetch-Site: same-site` rifiutato |
| **Effetti collaterali da GET** — `<img src="http://127.0.0.1:5000/...">` su una pagina qualsiasi | Le GET sono in sola lettura: nessuna crea file o cartelle |
| **Clickjacking** — l'app incorniciata in un'altra pagina per far cliccare «attiva monitoraggio» | `Content-Security-Policy: frame-ancestors 'none'` |
| **Immagini caricate da fuori** — un `<img>` che uscirebbe dalla macchina, e con lui la promessa «non esce niente» | `img-src 'self' data: blob:` nella stessa CSP: le sole immagini ammesse stanno in `/static` o sono roba dell'utente già in memoria |
| **Tipo indovinato dal browser** — una risposta interpretata come qualcosa che non è | `X-Content-Type-Options: nosniff` |
| **Indirizzo locale che esce nel `Referer`** — l'URL di una pagina locale finito nei log di un sito terzo | `Referrer-Policy: no-referrer` |
| **Occupazione di un worker** — una scansione lunghissima che tiene impegnato l'OCR | Tetto di pagine, di tempo (`MR_RAO_OCR_TIMEOUT`) e di dimensione dell'invio |

Le tre intestazioni escono su **ogni** risposta ([`mr_rao/app_factory.py`](mr_rao/app_factory.py)),
non solo sulla pagina: una difesa che vale per l'HTML e non per il JSON copre
il punto in cui nessuno attacca.

Perché **due** controlli anti-CSRF e non uno: il controllo su `Origin` è
condizionato alla presenza dell'header, e una navigazione da `<form>`
cross-site può arrivare senza. `Sec-Fetch-Site` lo mandano tutti i browser
attuali su ogni richiesta, quindi copre quel ramo; `Origin` resta per chi non
lo manda (curl, la CLI, un browser vecchio).

Ogni difesa ha il suo test in [`tests/test_security.py`](tests/test_security.py),
[`tests/test_limiti_ocr.py`](tests/test_limiti_ocr.py) e
[`tests/test_user_folders.py`](tests/test_user_folders.py). Non sono test
decorativi: disattivando una difesa il suo test diventa rosso — verificato
disattivandole una per una.

## Chiave di firma

`SECRET_KEY` è casuale a ogni avvio, e **non viene scritta su disco**.

Oggi non la usa niente: nessuna sessione, nessun cookie firmato. La ragione
del cambiamento è futura — il giorno che qualcuno scrive `session[...]`, che
in Flask è una riga, una costante scritta in un repository pubblico
diventerebbe la chiave con cui si firmano i cookie, e non si romperebbe nulla
che lo facesse notare.

Un file locale sarebbe stato peggio della costante: seguirebbe l'eseguibile
portable dentro OneDrive, nei backup e nello zip che passa a un collega.
Diventerà necessario solo quando serviranno sessioni che sopravvivono al
riavvio. `MR_RAO_SECRET` permette di fissarla, se quel giorno arriva prima.

## Esporre l'app in rete

Con `MR_RAO_HOST=0.0.0.0` l'allow-list degli host **non** diventa `*`: contiene
gli indirizzi e i nomi di questa macchina. L'accesso legittimo per IP o per
nome funziona; il dominio dell'attaccante, che nell'header `Host` porta il
proprio nome, no.

Dietro un reverse proxy con un nome pubblico serve dichiararlo:

```bash
MR_RAO_ALLOWED_HOSTS="mr-rao.azienda.it"
```

Senza, la risposta è un 403 che nomina la variabile invece di lasciare
indovinare.

## Trattamento dei file

- I file caricati finiscono in un file temporaneo di sistema, cancellato subito
  dopo la conversione.
- Le pagine rasterizzate durante l'OCR stanno in una directory temporanea che
  si cancella da sola, anche se il processo muore a metà.
- La cronologia dell'interfaccia è solo in memoria del browser: chiudendo la
  pagina sparisce.
- I risultati dei job restano in RAM per un'ora al massimo, con un tetto sul
  numero conservato.

## Limiti noti

- **L'anonimizzazione non è una garanzia.** I riconoscitori sono buoni ma non
  perfetti, soprattutto sui nomi. La scheda «prima / dopo» esiste perché tu
  possa controllare: usala prima di condividere un documento.
- **Su testo ottenuto via OCR la protezione è sensibilmente più debole.**
  Misurato: lo stesso contenuto letto da immagine produce 3 redazioni, letto da
  PDF scansionato ne produce 1, perché l'OCR storpia i caratteri (`IBAN IT60X…`
  diventa `TBAN1TB0X…`) e il pattern non corrisponde più. Il dato resta nel testo,
  deformato ma spesso ancora identificante. Il risultato porta un avviso esplicito.
- **Annullare una conversione non la interrompe istantaneamente.** Il flag
  viene letto al passaggio da uno stadio all'altro; una singola chiamata alla
  libreria di conversione non è interrompibile dall'esterno. Vale anche per il
  limite di tempo dell'OCR: ferma le pagine successive, non la pagina in corso.
- **Un OCR troncato per tempo produce un risultato parziale**, e quindi
  un'anonimizzazione parziale. Il documento lo dichiara in cima, non in fondo.
- **I percorsi del monitoraggio non sono confinati.** Chi usa l'interfaccia
  sceglie inbox e outbox dove vuole — è la funzione, non una svista: la
  hotfolder deve poter stare nei Documenti o su un disco di rete. La difesa è
  che nessuna pagina esterna possa avviarla (vedi sopra), e che la scrittura
  produca **solo** file `.md` senza mai sovrascriverne di esistenti.
- **Nessuna sandbox.** Il threat model non include documenti costruiti per
  attaccare i parser. Una sandbox seria su Windows (job object, AppContainer)
  è un progetto a sé; una finta non proteggerebbe da niente, e prometterla
  sarebbe peggio che non averla.

## Segnalare un problema

Apri una issue descrivendo:

1. cosa hai fatto,
2. cosa ti aspettavi,
3. cosa è successo.

Per una vulnerabilità che ritieni sensibile, scrivi in privato all'autore
invece di aprire una issue pubblica.

Non serve un proof-of-concept elaborato: anche «questo endpoint fa X e non
dovrebbe» è una segnalazione utile.
