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
> entro tre mesi dalla prenotazione: **2026-11-09**.

---

# Parte 1 — La prima pubblicazione, passo per passo

## 0. Il pacchetto

Da **Actions → Portable → Run workflow**, lasciando vuoti tutti i campi. Il
pacchetto si costruisce in camera pulita, si firma con Sigstore e resta
allegato all'esecuzione: si scarica l'artefatto `MrRao-Portable`, che
contiene `MrRao-<versione>.msix`.

Nome del file da caricare: **`MrRao-1.11.0.msix`**, circa 170 MB.

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

### Product declarations

Le caselle da lasciare **non spuntate**, e il perché:

- *«This app accesses, collects or transmits personal information»* — no. Il
  programma legge i documenti che gli dai e li elabora sul posto; niente
  esce dal computer e niente viene raccolto da noi.
- *«This app depends on non-Microsoft drivers or NT services»* — no.
- *«This app has been tested for accessibility»* — no, e non spuntarla:
  dichiararlo senza aver fatto una verifica di accessibilità sarebbe
  un'affermazione non sostenuta.

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

Si carica `MrRao-1.11.0.msix`. Device family: **Desktop**.

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

**Screenshots:** i tre file in `packaging/Store/`, nell'ordine
`01-conversione`, `02-risultato`, `03-controlli`.

**Copyright:** © 2026 Antonio Andrea Rao — GNU AGPL-3.0

**Developed by:** Antonio Andrea Rao

## 6. Notes for certification

Da scrivere nel campo delle note, perché **senza, il collaudo può concludere
che l'app non fa niente**:

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

---

# Parte 2 — L'automazione degli aggiornamenti

Serve solo dalla **seconda** pubblicazione in poi: la prima resta manuale
comunque, perché l'automazione aggiorna e non inserisce.

Si accende scrivendo `si` nel campo `pubblica_store` quando si lancia il
workflow. Finché i quattro segreti non ci sono, il workflow si ferma subito
dicendo **quali** mancano, invece di scoprirlo a metà pubblicazione.

## I quattro segreti, e da dove si prendono

Vanno in **Settings → Secrets and variables → Actions** del repository, con
**esattamente** questi nomi — il workflow li cerca così, e un nome diverso
diventa un errore di autenticazione a metà pubblicazione:

| Segreto | Dove si trova | Stato |
|---|---|---|
| `AZURE_AD_TENANT_ID` | [entra.microsoft.com](https://entra.microsoft.com/) → Identity → Overview → *Tenant ID* | **fatto** (2026-08-09) |
| `AZURE_AD_APPLICATION_CLIENT_ID` | Entra → Identity → Applications → App registrations → la tua app → *Application (client) ID* | da fare |
| `AZURE_AD_APPLICATION_SECRET` | stessa app → Certificates & secrets → New client secret. **Il valore si vede una volta sola** | da fare |
| `SELLER_ID` | Partner Center → Account settings → *Publisher ID* / *Seller ID* | da fare |

## Nell'ordine, cosa fare

1. **Entra → App registrations → New registration.** Nome: `mr-rao-store-publisher`.
   Account types: «Accounts in this organizational directory only». Nessun
   Redirect URI: questa registrazione non fa accedere nessuno, serve solo a
   farsi riconoscere da un programma. Copiare l'*Application (client) ID*.
2. **Certificates & secrets → New client secret.** Scadenza: la più corta
   che sia sostenibile, perché una credenziale che non scade è una
   credenziale che nessuno ruota. **Il valore si legge una volta sola**:
   incollarlo subito in GitHub e poi chiudere la pagina.
3. **Partner Center → Account settings → User management → Microsoft Entra
   applications → Add Azure AD application.** Scegliere la registrazione
   appena creata e assegnarle il ruolo **Manager**. Senza quel ruolo
   l'autenticazione riesce e la pubblicazione no — che è il modo più
   confuso di fallire.
4. **Account settings → Account settings (o Legal info) → *Seller ID***.
   Copiarlo.

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
