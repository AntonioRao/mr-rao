# Microsoft Store

Perché esiste questa strada: chi installa dallo Store **non vede l'avviso
«editore sconosciuto»**, perché il pacchetto lo firma Microsoft dopo la
certificazione. È l'unico modo gratuito per togliere quell'avviso.

L'altra opzione di Partner Center, «EXE or MSI app», sembrava più comoda —
si pubblica l'installer che c'è già — ma pretende che sia **tu** a firmarlo
Authenticode con un certificato a pagamento, e lo Store non lo firma al posto
tuo. Riporta al problema di partenza, quindi è esclusa.

## Cosa c'è già

| | |
|---|---|
| Nome prenotato | **Mr. Rao** |
| Store ID | `9N7SJ4W88KQC` (pubblico: sta nell'indirizzo della scheda) |
| Manifesto | [`packaging/AppxManifest.xml`](../packaging/AppxManifest.xml) |
| Immagini | `packaging/Assets/` — 13 misure, versionate |
| Pacchetto | lo costruisce `portable.yml`, dalla stessa build dello zip |

Il pacchetto **non viene firmato da noi**, ed è il punto di tutta la
faccenda: lo firma Microsoft.

## Due vincoli che decidono cosa si può automatizzare

**Solo prodotti gratuiti.** L'aggiornamento via GitHub Actions non è
disponibile per le app a pagamento. Mr. Rao è gratuito, quindi passa.

**La prima volta si fa a mano.** L'automazione *aggiorna* un'app già
pubblicata e viva sullo Store: non la inserisce. La prima sottomissione —
descrizione, schermate, classificazione per età, mercati — si compila in
Partner Center, e non c'è modo di aggirarlo.

> **Scadenza.** La prenotazione del nome decade se l'app non viene inviata
> entro tre mesi dalla prenotazione.

## Come si pubblica, oggi: a mano

**È il percorso in uso.** L'automazione esiste ma è spenta, e il perché sta
nella sezione dopo.

1. **Actions → Portable → Run workflow**, lasciando vuoti tutti i campi. Il
   pacchetto si costruisce in camera pulita, si firma con Sigstore e resta
   allegato all'esecuzione.
2. Dall'esecuzione, scarica l'artefatto `MrRao-Portable`: dentro c'è
   `MrRao-<versione>.msix`.
3. In Partner Center, sull'app **Mr. Rao**, crea la sottomissione e carica
   quel file.

Alla prima sottomissione vanno compilate anche descrizione, schermate,
classificazione per età e mercati. Quella parte non si automatizza in nessun
caso, nemmeno più avanti.

## Perché l'automazione è spenta

Non è incompiuta: è **scritta, provata e in attesa**. Si accende scrivendo
`si` nel campo `pubblica_store`, e finché i quattro segreti non ci sono, il
workflow si ferma subito dicendo quali mancano.

È spenta per una ragione di proporzioni, decisa il 2026-08-09. Farla
funzionare richiede un **tenant Microsoft Entra** associato all'account: il
Partner Center è nato con un account Microsoft personale, e sotto «Azure AD
Directories» non c'è nessuna directory. Crearne uno significa una nuova
utenza amministrativa, una password, e un *client secret* che scade e va
ruotato.

Dall'altra parte della bilancia: la prima pubblicazione resta manuale
comunque, e gli aggiornamenti sono tre clic ogni release. Per un progetto
che rilascia ogni tanto, il tenant è parecchia infrastruttura per poco
guadagno.

Quando le release diventeranno frequenti, la sezione qui sotto dice cosa
serve.

## I quattro segreti, e da dove si prendono

Vanno in **Settings → Secrets and variables → Actions** del repository, con
**esattamente** questi nomi — il workflow li cerca così, e un nome diverso
diventa un errore di autenticazione a metà pubblicazione:

| Segreto | Dove si trova |
|---|---|
| `AZURE_AD_TENANT_ID` | [entra.microsoft.com](https://entra.microsoft.com/) → Identity → Overview → *Tenant ID* |
| `AZURE_AD_APPLICATION_CLIENT_ID` | Entra → Identity → Applications → App registrations → la tua app → *Application (client) ID* |
| `AZURE_AD_APPLICATION_SECRET` | stessa app → Certificates & secrets → New client secret. **Il valore si vede una volta sola** |
| `SELLER_ID` | Partner Center → Account settings → *Publisher ID* / *Seller ID* |

Prima però servono due passaggi in Partner Center:

1. **associare un tenant Microsoft Entra** all'account Partner Center (o
   crearne uno nuovo da lì);
2. in **Account settings → User management → Microsoft Entra applications**,
   aggiungere la registrazione dell'app e assegnarle il ruolo **Manager**.
   Senza quel ruolo l'autenticazione riesce e la pubblicazione no.

> Il *client secret* lo crei e lo incolli tu. È una credenziale: non passa da
> nessun'altra parte, e non va scritta in un file del repository.

## Come si pubblichera' un aggiornamento, quando l'automazione sara' accesa

Dalla scheda **Actions** → workflow **Portable** → *Run workflow*, e nel campo
`pubblica_store` scrivere `si`.

Lasciato vuoto non succede niente: il pacchetto si costruisce, si firma e
resta scaricabile dall'esecuzione. **Nessuna esecuzione pubblica da sola** —
una release che parte per conto suo non è un automatismo, è una sorpresa.

Il workflow controlla che i quattro segreti ci siano *prima* di iniziare,
perché scoprirlo a metà è il momento peggiore.

## Cosa cambia rispetto al pacchetto portable

Non è la stessa confezione, e le differenze sono volute:

- il **menu contestuale** non si scrive nel registro: è dichiarato nel
  manifesto, e Windows lo applica e lo rimuove insieme al pacchetto. Di
  sponda risolve un difetto vecchio — disinstallando non restano voci
  orfane;
- **niente collegamento sul Desktop**: MSIX crea solo la voce nel menu
  Start, per scelta di Microsoft;
- **niente `Installa Mr Rao.bat`**: installa e disinstalla Windows;
- resta fuori anche `mr_rao_shell.ps1`, che in un pacchetto sotto
  certificazione sarebbe codice morto;
- le **licenze entrano**: pystray è LGPL, e l'obbligo di redistribuzione
  vale per ogni confezione.
