# Microsoft Store

Perché esiste questa strada: chi installa dallo Store **non vede l'avviso
«editore sconosciuto»**, perché il pacchetto lo firma Microsoft dopo la
certificazione. È l'unico modo gratuito per togliere quell'avviso.

**La certificazione è passata il 2026-08-11 e l'app è pubblicata.** Questo
documento non descrive più un piano: descrive una strada percorsa fino in
fondo, e le istruzioni restano perché il prossimo aggiornamento riparte da
lì.

| | |
|---|---|
| Scheda pubblica | <https://apps.microsoft.com/detail/9N7SJ4W88KQC> |
| Store ID | `9N7SJ4W88KQC` |
| Collegamento dall'app Store di Windows | `ms-windows-store://pdp/?productid=9N7SJ4W88KQC` |

I due indirizzi non sono intercambiabili: il primo si apre ovunque, il secondo
solo su Windows con lo Store installato. Per questo nei README c'è **solo**
quello web — un link che fuori da Windows non fa niente, su una pagina che
esiste per farsi dare fiducia, è peggio di nessun link.

L'altra opzione di Partner Center, «EXE or MSI app», sembrava più comoda —
si pubblica l'installer che c'è già — ma pretende che sia **tu** a firmarlo
Authenticode con un certificato a pagamento, e lo Store non lo firma al posto
tuo. Riporta al problema di partenza, quindi è esclusa.

## Cosa c'è già

| | |
|---|---|
| Nome | **Mr. Rao** — prenotato il 2026-08-09, pubblicato il 2026-08-11 |
| Store ID | `9N7SJ4W88KQC` (pubblico: sta nell'indirizzo della scheda) |
| Manifesto | [`packaging/AppxManifest.xml`](../packaging/AppxManifest.xml) |
| Immagini del pacchetto | `packaging/Assets/` — 13 misure, versionate |
| Schermate della scheda | `packaging/Store/` — orizzontali, dentro i limiti |
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
> entro tre mesi dalla prenotazione: **2026-11-09**. Rispettata: la prima
> sottomissione è partita il **2026-08-09**.

## Stato

**Submission 1 inviata il 2026-08-09, certificata e pubblicata il
2026-08-11.** Portava la versione con cui era stata costruita, non l'ultima:
è il primo aggiornamento a riallineare lo Store a `APP_VERSION`.

> **Perché lo Store è rimasto indietro rispetto a git, e perché andava bene
> così.** Mentre la submission era in certificazione il repository ha
> continuato ad avanzare. **Non si tocca una submission in certificazione**:
> sostituire il pacchetto vuol dire ricominciare la coda da capo, in cambio di
> niente. La regola applicata è stata: si aspetta la prima pubblicazione, poi
> si allinea la build dello Store a dove è arrivato GitHub — con una
> submission nuova, che è la strada normale per gli aggiornamenti e quella
> descritta nella Parte 2.

> **Cosa cambia adesso che la scheda è viva.** L'indirizzo
> <https://apps.microsoft.com/detail/9N7SJ4W88KQC> rispondeva `410 Gone`
> finché la certificazione non è finita, ed era il motivo per cui non stava
> nei README: un pulsante morto proprio sulla strada della fiducia, premuto
> dalla persona più diffidente. Adesso risponde, e il link ci sta.

---

# Parte 1 — La prima pubblicazione, passo per passo

**Questa parte è stata riscritta dopo averla fatta davvero.** La versione
precedente era ricostruita dalla documentazione e sbagliava in più punti —
sono segnati con «⚠ diverso da come sembrava».

## L'ordine conta, e non è quello che sembra

Il **pacchetto va caricato per primo**, prima della scheda. Le lingue della
scheda **non esistono finché non c'è un pacchetto**: le legge dal manifesto
(`<Resource Language="it-IT"/>`, `en-US`). Finché manca, la pagina «Store
listings» resta a girare a vuoto senza spiegare perché — e non è un guasto,
è quell'ordine.

## 0. Il pacchetto

Da **Actions → Portable → Run workflow**, lasciando vuoti tutti i campi. Il
pacchetto si costruisce in camera pulita, si firma con Sigstore e resta
allegato all'esecuzione: si scarica l'artefatto `MrRao-Portable`, che
contiene `MrRao-<versione>.msix`.

Nome del file da caricare: **`MrRao-<versione>.msix`**, circa 170 MB. Il nome
lo compone `scripts/make_msix.py` da `APP_VERSION`, quindi cambia a ogni
release: non c'è un nome fisso da cercare, si guarda cosa c'è dentro
l'artefatto.

## 1. Pricing and availability

| Campo | Cosa mettere |
|---|---|
| Markets | **All markets** |
| Visibility | Public — «Available in the Store» |
| Pricing | **Free** |
| Free trial | No free trial |
| Sale pricing, Organizational licensing | lasciare com'è |
| Publish date | «as soon as it passes certification» |

## 2. Properties

| Campo | Cosa mettere |
|---|---|
| Category | **Productivity** |
| Subcategory | nessuna |
| Privacy policy URL | `https://github.com/AntonioRao/mr-rao/blob/main/docs/PRIVACY.md` |
| Website | `https://github.com/AntonioRao/mr-rao` |
| Support contact info | `https://github.com/AntonioRao/mr-rao/issues` |
| System requirements | niente da spuntare: gira su qualunque Windows 10/11 x64 |

**La privacy policy è obbligatoria e in questo caso non è un adempimento**:
è la ragione per cui il programma esiste. `PRIVACY.md` dice cosa il motore
toglie, cosa lascia e **cosa la misura dice che non regge** — compresa la
riga sulle scansioni sbiadite. Vale la pena che la legga chi certifica.

**⚠ diverso da come sembrava.** La domanda sulla privacy non è una casella
da spuntare ma una tendina, e la risposta data è **«Yes, my product uses
personal information»**. Qui sopra c'era scritto di rispondere no, ed era
sbagliato: Mr. Rao **legge documenti pieni di dati personali**, è
esattamente il suo mestiere. Che non li trasmetta e non li raccolga è
un'altra affermazione, e la fa la privacy policy. Rispondere «no» sarebbe
stato comodo e non vero — e su questo prodotto è l'affermazione peggiore da
sbagliare.

### Product declarations

Le caselle da lasciare **non spuntate**, e il perché:

- *«This app has been tested to meet accessibility guidelines»* — no.
  Nessuno verrebbe a controllare, ed è proprio per questo: non abbiamo fatto
  nessuna verifica di accessibilità, e spuntarla sarebbe un'affermazione non
  sostenuta su una scheda pubblica.
- *«Windows can include this product's data in automatic backups to
  OneDrive»* — **arriva spuntata di default, e va tolta.** Contraddice la
  sola cosa che il programma promette, ed è il difetto che questo
  repository ha già pagato una volta: le cartelle che finivano nel cloud.
- *«Customers can use Windows 10/11 features to record and broadcast clips
  of this product»* — anche questa arriva spuntata. Serve ai giochi, e su
  uno strumento che mostra documenti altrui è un default che non vogliamo.
- *«This app incorporates generative AI features»* — no: il motore è
  deterministico, e dirlo altrimenti sarebbe pubblicità falsa al contrario.

Resta spuntata *«Customers can install this product to alternate drives»*:
è vera e non toglie niente a nessuno.

## 3. Age ratings

Questionario IARC. Le risposte, tutte «no»: nessuna violenza, nessun
contenuto sessuale, nessun linguaggio volgare, nessun gioco d'azzardo,
nessun acquisto in-app, nessuna pubblicità, nessuna condivisione di
contenuti fra utenti, nessuna raccolta di dati personali, nessuna posizione
geografica, nessun accesso a internet.

Esito atteso: **PEGI 3 / ESRB Everyone**.

> Se il questionario chiede se l'app *si connette a internet*: **no**. Il
> manifesto non dichiara nessuna capability di rete, e la CI ha un test che
> lo verifica. Il server locale su `127.0.0.1` non è una connessione di rete
> verso l'esterno, ed è bene dirlo nelle note per la certificazione.

## 4. Packages

Si carica `MrRao-<versione>.msix`. Device family: **Desktop**.

Il pacchetto non è firmato da noi ed è corretto così: la firma la mette
Microsoft dopo la certificazione.

## 5. Store listing (italiano)

**Product name:** Mr. Rao

**Short description** (max 500 caratteri):

> Converte PDF, Word, Excel, scansioni ed email in Markdown pulito, con i
> dati personali già rimossi. Tutto sul tuo computer: il file non si muove,
> nessuna connessione a internet.

**Description** — da incollare così com'è:

> **Devi dare un documento in pasto a un assistente AI. Ti servono due
> cose: il testo pulito, e non consegnare al fornitore il codice fiscale
> del tuo cliente.**
>
> I convertitori online risolvono il primo problema creando il secondo: per
> convertire il file glielo devi caricare. Se quel file è una fattura, una
> cartella clinica, un contratto o un thread email con dentro persone
> reali, l'hai appena spedito a un server di cui non sai nulla.
>
> Mr. Rao fa la conversione **e** l'anonimizzazione sul tuo computer. Il
> file non si muove.
>
> **COSA CONVERTE**
> PDF, Word, Excel, PowerPoint, HTML, CSV, testo, email .eml, e immagini e
> scansioni con riconoscimento ottico dei caratteri. In uscita: Markdown,
> testo semplice o documento Word — tutti e tre già anonimizzati.
>
> **COME DECIDE COSA TOGLIERE**
> Ogni riconoscitore è una coppia: un'espressione che propone candidati e un
> controllo aritmetico che decide. Un IBAN deve passare il mod-97, una carta
> di pagamento la formula di Luhn, un codice fiscale il proprio carattere di
> controllo. Il numero deve dimostrare di essere quello che sembra.
>
> Per questo un numero di protocollo, una data e un codice d'ordine restano
> dov'erano: il programma non redige quello che non deve.
>
> Riconosce nomi, indirizzi, recapiti telefonici, email, codice fiscale,
> partita IVA, IBAN, carte di pagamento, date di nascita, carte d'identità,
> patenti e passaporti. Oltre ai formati italiani anche quelli britannici,
> statunitensi, canadesi e australiani.
>
> **QUANDO NON È SICURO, LO DICE**
> Se la prova è debole il dato non viene sostituito: viene **segnalato**. Il
> documento resta intero e chi rilegge sa dove guardare. Un programma che
> cancella tutto per sicurezza non è più utile di uno che non cancella
> niente.
>
> **DUE LISTE TUE**
> I nomi che ricorrono in ogni pratica li conosci solo tu: una lista di
> termini da nascondere sempre, e una di termini da non toccare mai.
>
> **COSA NON FA**
> Non manda niente a nessun server, non ha account, non chiede
> registrazione, non raccoglie statistiche d'uso. Non chiede nessuna
> autorizzazione di rete, e lo si può verificare dalla scheda di questa
> pagina.
>
> Non è il documento originale con sopra dei rettangoli neri — quella è la
> trappola classica della redazione, i rettangoli si tolgono e il testo è
> ancora lì sotto. Qui il documento viene rigenerato dal testo già redatto:
> il dato non è coperto, è assente. Il prezzo è l'impaginazione
> dell'originale, che si perde.
>
> **NON È MAGIA, ED È MISURATO**
> Su una scansione ben fatta il motore copre la quasi totalità dei dati
> personali. Su una fotocopia sbiadita, dove il riconoscimento ottico
> incolla le parole fra loro, una parte resta in chiaro — e non sempre viene
> segnalata. Il numero preciso, con il metodo per rifarlo, è scritto nella
> documentazione del progetto invece che taciuto.
>
> **Il confronto prima/dopo è il controllo che conta: guardalo sempre.**
>
> Software libero sotto licenza GNU AGPL-3.0. Codice sorgente, misure e
> documentazione: github.com/AntonioRao/mr-rao

**Product features** (le voci brevi in cima alla scheda):

- Converte PDF, Word, Excel, scansioni ed email in Markdown pulito
- Rimuove i dati personali prima che tu li incolli da qualche parte
- Funziona senza internet: il documento non lascia il computer
- Il numero deve passare un controllo aritmetico per essere sostituito
- Quando la prova è debole segnala invece di cancellare
- Riconoscimento ottico per immagini e scansioni
- Esporta in Markdown, testo semplice o documento Word
- Menu contestuale: tasto destro su un file e converti
- Interfaccia e risultato in italiano o in inglese
- Software libero AGPL-3.0, codice pubblico e verificabile

**Search terms** (max 7, 30 caratteri l'uno):

`anonimizzazione` · `markdown` · `GDPR` · `PDF in markdown` ·
`dati personali` · `OCR` · `privacy`

**Screenshots:** i tre file `*-it.png` in `packaging/Store/`, nell'ordine
`01-conversione`, `02-risultato`, `03-controlli`.

**⚠ diverso da come sembrava — le schermate sono per lingua.** La scheda
inglese vuole le proprie (`*-en.png`, con l'interfaccia inglese): riciclare
quelle italiane sarebbe spedire il manuale sbagliato. E lo Store accetta PNG
solo **fra 1366x768 e 3840x2160**: le schermate del README sono 1500x2420,
troppo alte, e sarebbero state respinte all'invio. Le genera
`scripts/make_screenshot.py --store`, che controlla anche le misure.

I **loghi** invece **non servono**: Partner Center li dichiara «Optional» e
di default usa quelli del pacchetto, dove le tredici immagini ci sono già.

**Copyright:** © 2026 Antonio Andrea Rao — GNU AGPL-3.0

**Developed by:** Antonio Andrea Rao

## 6. La giustificazione per `runFullTrust`

**⚠ non era previsto qui, e invece è obbligatorio.** Appena caricato il
pacchetto, Partner Center segnala *«Package acceptance validation warning:
the following restricted capabilities require approval: runFullTrust»* e
apre un campo **obbligatorio** in Submission Options.

Non è un problema del nostro pacchetto: `runFullTrust` è la capability che
dichiara **ogni** programma Win32 impacchettato in MSIX — è il meccanismo
stesso del Desktop Bridge. Non esiste un modo di impacchettare un
eseguibile Python senza. È un *warning*, non un errore: il pacchetto viene
accettato e risulta **Validated**.

Cosa deve dire la giustificazione, e perché queste cose:

1. **che è un'app desktop Win32 impacchettata**, non una UWP che potrebbe
   girare a fiducia parziale;
2. **cosa fa davvero il processo**: legge i file che l'utente apre o
   trascina, gira il motore di conversione e l'OCR in locale, apre un server
   su `127.0.0.1` e lancia il browser predefinito come interfaccia;
3. **cosa non fa**: nessun accesso di rete in uscita, nessuna telemetria,
   nessun account, nessun driver o servizio, nessuna modifica alle
   impostazioni di sistema;
4. **che il manifesto non dichiara nessuna capability di rete**, e che c'è
   un test automatico che lo verifica — è un'affermazione controllabile, non
   una promessa;
5. il collegamento al codice sorgente pubblico.

## 7. Notes for certification

**⚠ non stanno in Submission Options**, come lasciava intendere il nome: si
scrivono in **Supplemental info → Additional Testing Information**, e si
salvano con «Save description» in cima alla pagina, non con un pulsante in
fondo.

Vanno scritte perché **senza, il collaudo può concludere che l'app non fa
niente**:

> L'applicazione avvia un server locale su 127.0.0.1 e apre il browser
> predefinito sulla propria interfaccia. È un'applicazione desktop che usa
> il browser come interfaccia: **non si connette a internet**, e il
> manifesto non dichiara nessuna capability di rete.
>
> Per provarla: avviare Mr. Rao dal menu Start, attendere che si apra la
> pagina, trascinare nell'area di rilascio un qualunque PDF o file di testo
> che contenga dati personali inventati. Il risultato compare nella pagina,
> con il conteggio di quanti dati sono stati sostituiti.
>
> Il primo avvio può richiedere qualche secondo: il motore di
> riconoscimento ottico viene caricato in memoria.
>
> L'app non richiede account, non raccoglie dati e non ha acquisti interni.

## 8. Invio

**Submit for certification** si accende da solo quando i requisiti sono
soddisfatti. Fidarsi di quel pulsante, non dei badge laterali: a invio
pronto «Submission options» risultava ancora **Incomplete** pur avendo tutti
i campi compilati e salvati — un badge rimasto indietro, non un ostacolo.

Dopo l'invio si può ancora annullare («Cancel certification») finché non è
pubblicata.

---

# Parte 2 — L'automazione degli aggiornamenti

Serve dalla **seconda** pubblicazione in poi: la prima è stata manuale — e lo
sarebbe rimasta comunque, perché l'automazione aggiorna e non inserisce. **La
prima è avvenuta il 2026-08-11**, quindi da adesso questa parte è la strada
normale.

**Configurata il 2026-08-09, eseguita per la prima volta il 2026-08-13 —
e si è fermata sull'autenticazione.** I quattro segreti ci sono (il passo
che li conta è passato) e la registrazione ha il suo ruolo, ma `msstore
reconfigure` risponde `Really failed to auth` dopo tre tentativi, e il
lavoro si ferma **prima** di spedire: allo Store non è arrivato niente.

Il valore di questo esito è che si è visto dove si rompe. La causa non è
leggibile dal log — il CLI non dice *quale* delle quattro credenziali
rifiuta — ma il sospetto principale è quello che questo stesso documento
segnala poco più sotto: nel campo `AZURE_AD_APPLICATION_SECRET` va la
colonna **Valore**, non «ID segreto», e il valore si vede **una volta
sola**. Chi lo ricopia dopo trova solo l'ID, che ha una forma simile e
non funziona.

Da verificare in quest'ordine, dal più probabile al meno: il *Valore* del
segreto client; che l'app in Partner Center sia sotto **Microsoft Entra
applications** col ruolo *Developer*; il Seller ID preso da **Legal
info**; l'ID tenant.

Finché non è chiarito, **l'aggiornamento si carica a mano** da Partner
Center: è la strada già collaudata, e l'MSIX esce comunque dalla stessa
build (artefatto `MrRao-Portable` dell'esecuzione, che scade in 7 giorni).

Si accende scrivendo `si` nel campo `pubblica_store` quando si lancia il
workflow. Finché i quattro segreti non ci sono, il workflow si ferma subito
dicendo **quali** mancano, invece di scoprirlo a metà pubblicazione.

## I quattro segreti, e da dove si prendono

Vanno in **Settings → Secrets and variables → Actions** del repository, con
**esattamente** questi nomi — il workflow li cerca così, e un nome diverso
diventa un errore di autenticazione a metà pubblicazione:

**Tutti e quattro configurati il 2026-08-09.** Qui sotto c'è dove si
trovano, per quando andranno rifatti — il *client secret* scade.

| Segreto | Dove si trova |
|---|---|
| `AZURE_AD_TENANT_ID` | [entra.microsoft.com](https://entra.microsoft.com/) → Panoramica → *ID tenant* |
| `AZURE_AD_APPLICATION_CLIENT_ID` | Entra → **Registrazioni app** → scheda **«Tutte le applicazioni»** → *ID applicazione (client)* |
| `AZURE_AD_APPLICATION_SECRET` | stessa app → Certificati e segreti → Nuovo segreto client. **Il valore si vede una volta sola** |
| `SELLER_ID` | Partner Center → Account settings → **Legal info** → *Seller ID* |

**⚠ due dettagli che fanno perdere tempo.** Dopo la registrazione, l'app non
compare sotto «Applicazioni di cui si è proprietari» ma solo sotto **«Tutte
le applicazioni»**. E il **Seller ID non è in *Identifiers***, dov'è
ragionevole cercarlo e dove questo documento diceva di guardare: è in
**Legal info**, insieme a User Id e ai publisher ID.

## Nell'ordine, cosa fare

1. **Entra → Registrazioni app → Nuova registrazione.** Nome
   `mr-rao-store-publisher`, tipo «Solo tenant singolo», **nessun URI di
   reindirizzamento**: quello serve a far accedere delle persone, e qui non
   accede nessuno — un programma si autentica da solo col segreto. Metterlo
   sarebbe superficie in più che non si usa.
2. **Certificati e segreti → Nuovo segreto client.** Scadenza: la più corta
   sostenibile, perché una credenziale che non scade è una credenziale che
   nessuno ruota. Serve la colonna **Valore**, non «ID segreto», e **si
   legge una volta sola**: si incolla subito in GitHub.
3. **Partner Center → Account settings → User management → Microsoft Entra
   applications → Add Microsoft Entra application.** Scegliere **«Add»**,
   non «Create»: la registrazione esiste già.

   ### Il ruolo: **Developer**, non Manager

   **⚠ qui questo documento diceva Manager, ed era la scelta sbagliata.**

   `Developer` recita: *«può caricare pacchetti e inviare app e add-on…
   non può accedere a informazioni finanziarie né alle impostazioni
   dell'account»*. È esattamente il mestiere del workflow, e niente di più.

   `Manager` invece dà accesso completo all'account e permette di
   **gestire utenti, ruoli e tenant**. Su una credenziale che vive dentro
   GitHub Secrets è sproporzionato: se trapelasse, con Developer si può
   pubblicare un pacchetto — grave ma circoscritto — con Manager si prende
   l'account.

   E c'è una trappola nell'interfaccia: **spuntare «Manager» seleziona da
   solo tutti e quattro gli altri ruoli**, compresi *Finance Contributor* e
   *Business Contributor*, cioè profili di pagamento e dati finanziari. Se
   si clicca senza guardare si concede molto più di quanto si crede.

   Se un giorno una pubblicazione automatica fallisse per permessi, il
   ruolo si allarga da questa stessa pagina in pochi secondi — meglio
   allargarlo con una prova in mano che stringerlo dopo.

   A cose fatte l'app compare **due volte**, come *Microsoft Entra Apps* e
   come *Service Principal*: è normale, sono due facce della stessa
   registrazione.
4. **Account settings → Legal info → *Seller ID***.

> Il *client secret* lo crei e lo incolli tu, direttamente in GitHub. È una
> credenziale: non passa da nessun'altra parte, e non va scritta in un file
> del repository.

## Come si pubblica un aggiornamento

Dalla scheda **Actions** → workflow **Portable** → *Run workflow*, e nel campo
`pubblica_store` scrivere `si`.

Lasciato vuoto non succede niente: il pacchetto si costruisce, si firma e
resta scaricabile dall'esecuzione. **Nessuna esecuzione pubblica da sola** —
una release che parte per conto suo non è un automatismo, è una sorpresa.

Va ricordata una cosa a ogni release: **il manifesto porta la sua versione**.
`packaging/AppxManifest.xml` dichiara `<APP_VERSION>.0`, e c'è un test che lo
tiene agganciato a `config.py`. Lo Store rifiuta un pacchetto con una
versione non superiore alla precedente.

---

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
