# Sicurezza

## Modello di minaccia

Mr. Rao è un **attrezzo locale monoutente**. Serve un server web perché
l'interfaccia sta nel browser, non perché sia un servizio di rete.

Cosa questo comporta:

- **Non c'è autenticazione.** Chiunque raggiunga la porta può convertire file
  e avviare la sorveglianza di una cartella.
- **Va tenuto su `127.0.0.1`.** È il default. `docker-compose.yml` pubblica la
  porta solo su localhost apposta.
- **Esporlo in rete è una scelta consapevole** e richiede un reverse proxy con
  autenticazione davanti. Senza, stai dando a chiunque un convertitore che
  scrive file sul tuo disco.

## Difese presenti

Un server su localhost è raggiungibile da **qualunque pagina** aperta nel
browser dell'utente. Due attacchi distinti, due controlli distinti:

| Attacco | Difesa |
|---------|--------|
| **DNS rebinding** — un dominio dell'attaccante che risolve a `127.0.0.1` per leggere le risposte | Header `Host` in allow-list (`MR_RAO_ALLOWED_HOSTS`) |
| **CSRF** — una POST cross-site (multipart non richiede preflight CORS) che avvia una conversione o una sorveglianza | Rifiuto di `Origin` cross-site sui metodi che modificano stato |
| **Effetti collaterali da GET** — `<img src="http://127.0.0.1:5000/...">` su una pagina qualsiasi | Le GET sono in sola lettura: nessuna crea file o cartelle |

Ogni difesa ha il suo test in [`tests/test_security.py`](tests/test_security.py)
e [`tests/test_user_folders.py`](tests/test_user_folders.py).

## Trattamento dei file

- I file caricati vivono in un file temporaneo di sistema, cancellato subito
  dopo la conversione.
- Le pagine rasterizzate durante l'OCR stanno in una directory temporanea che
  si cancella da sola, anche se il processo muore a metà.
- La cronologia dell'interfaccia è solo in memoria del browser: chiudendo la
  pagina sparisce.
- I risultati dei job restano in RAM per un'ora al massimo, con un tetto sul
  numero conservato.

## Limiti noti

- **La schermatura dei dati personali non è una garanzia.** I riconoscitori
  sono buoni ma non perfetti, soprattutto sui nomi. La scheda «prima / dopo»
  esiste perché tu possa controllare: usala prima di condividere un documento.
- **Annullare una conversione non la interrompe istantaneamente.** Il flag
  viene letto a ogni confine di stadio; una singola chiamata alla libreria di
  conversione non è interrompibile dall'esterno.

## Segnalare un problema

Apri una issue descrivendo:

1. cosa hai fatto,
2. cosa ti aspettavi,
3. cosa è successo.

Per una vulnerabilità che ritieni sensibile, scrivi in privato all'autore
invece di aprire una issue pubblica.

Non serve un proof-of-concept elaborato: anche «questo endpoint fa X e non
dovrebbe» è una segnalazione utile.
