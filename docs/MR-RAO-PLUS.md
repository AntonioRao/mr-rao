# Mr. Rao Plus — l'ultimo metro

Mr. Rao lavora sui documenti, **prima**: apri un file, esce il testo redatto,
e quello che incolli in una chat lo hai già ripulito.

Ma il punto in cui i dati escono davvero, oggi, non è un file: è la **casella
di una chat con l'intelligenza artificiale**. Si scrive in fretta, si incolla
un pezzo di email, si preme Invio. Fra il pensiero e il server non c'è niente.

**Mr. Rao Plus** è un'estensione per il browser che sta in quel metro.

| | |
|---|---|
| **Microsoft Edge** | [scheda sullo store](https://microsoftedge.microsoft.com/addons/detail/mr-rao-plus/iecojbdclofpmlecldamgmdfofaanead) |
| **Google Chrome** | in arrivo — la scheda è in bozza |
| Licenza | **commerciale**, non AGPL. Mr. Rao resta AGPL-3.0 |
| Privacy | [rao.valor-cyber.com/plus/privacy](https://rao.valor-cyber.com/plus/privacy/) |

---

## Cosa fa, in concreto

Guarda quello che stai per mandare a ChatGPT, Claude, Copilot (personale e
Microsoft 365), Gemini, Grok — anche dentro X —, DeepSeek e Perplexity.

Se nel testo c'è un dato che non deve uscire, **lo toglie dalla casella prima
che il messaggio parta**, e ti mostra cosa ha tolto:

```
Bonifico su IT60X0542811101000000123456   →   Bonifico su {{IBAN_1}}
```

**Il primo invio non parte mai**, nemmeno quando la correzione riesce. Il
motivo è semplice: riscrivere il messaggio di qualcuno e spedirlo nello stesso
gesto vorrebbe dire mandare al posto suo una frase che non ha letto. Prima
leggi cosa è cambiato, poi premi di nuovo.

### Tre risposte, non due

Questa è la differenza che conta rispetto a un filtro qualunque.

1. **Toglie il dato e non manda** — quando trova qualcosa che non deve uscire.
2. **Manda e te lo dice** — quando trova qualcosa che non merita un blocco. Un
   indirizzo web è il caso tipico: fermare i link renderebbe l'estensione
   insopportabile in una settimana.
3. **Dichiara quello che non è riuscito a leggere** — e questo è il punto in
   cui quasi tutti i prodotti mentono. Un corpo che non si sa aprire non
   produce «pulito»: produce «non lo so, e te lo dico».

### Cosa riconosce

Gli stessi riconoscitori di Mr. Rao, perché è **lo stesso motore** portato in
TypeScript e verificato caso per caso contro l'originale:

IBAN e BBAN, codice fiscale (anche con errori da OCR), partita IVA, carte di
pagamento, targhe, riferimenti catastali e numeri di pratica, indirizzi,
email, telefoni, credenziali (chiavi, token, password), documenti d'identità,
e i codici stranieri con un conto dietro: SSN, ITIN, NINO, NHS, ABN, TFN, SIN,
routing number, MRZ dei passaporti.

E i **nomi di persona** — compresi quelli scritti tutti in minuscolo, come si
scrive nelle chat. È l'unica cosa che l'estensione fa e Mr. Rao no: nei
documenti i nomi hanno l'iniziale maiuscola e l'euristica «due parole
maiuscole che non sono parole italiane» è ciò che tiene bassi i falsi
positivi; in chat quella stessa euristica non vedrebbe niente.

---

## Come è fatto, e perché così

### Due strati, che sbagliano in modo diverso

**La casella di testo** è il meccanismo principale: il testo si analizza dove
viene scritto, con il motore che gira dentro il browser.

**I ganci di rete** — `fetch`, `XMLHttpRequest`, `WebSocket`, `sendBeacon` —
sono l'ultima rete: se un giorno il sito ridisegna la casella e la
sorveglianza smette di vedere, il gancio ferma comunque l'invio.

Due strati che sbagliano in modo diverso valgono più di uno solo fatto bene. E
questa architettura non è nata a tavolino: è nata da un fallimento misurato.
La prima versione guardava **solo** le richieste in uscita, e per sapere quale
richiesta fosse un invio serviva un elenco di indirizzi. Su ChatGPT, senza
accesso, l'invio passa da `/backend-anon/f/conversation` mentre l'elenco
diceva `/backend-api/…`. Per quella parola un IBAN è uscito davvero: risposta
arrivata, nessuna finestra, **nessun errore**. Silenzio.

### Niente rete, e si può verificare

L'estensione chiede **un permesso solo**, `storage`, per ricordare le tue
impostazioni. Non dichiara nessun `host_permissions`, non fa una sola chiamata
di rete — nemmeno verso di noi — e non esiste un server a cui potrebbe
mandare qualcosa.

Non è una promessa: il pacchetto **non è offuscato** apposta. Si apre, si
legge, si conta il numero di `fetch`.

### Se la protezione smette di funzionare, lo dice

C'è una sentinella che confronta quello che vede nella pagina con quello che è
passato dai nostri occhi. Se un messaggio esce e a noi non è passato davanti,
lo dice — perché un prodotto di sicurezza che si spegne in silenzio è
**peggio** di uno assente: chi lo usa continua a comportarsi come se ci fosse.

---

## I limiti, scritti qui e non solo qui

Gli stessi limiti stanno nella descrizione dello store e nelle note di
certificazione. Un limite dichiarato in un solo posto è un limite nascosto.

- **Gli allegati non vengono ispezionati.** L'estensione lavora sul testo che
  scrivi. Un PDF o un `.docx` allegato oggi passa senza essere guardato: è la
  cosa in cima alla lista delle prossime, e fino ad allora non deve sembrare
  coperta.
- **Sui nomi stranieri il riconoscimento è più debole.** Gli elenchi sono
  italiani: 2181 cognomi, nessun cognome inglese. «Mario Rossi» ferma il
  messaggio; «John Smith» arriva a un riscontro solo e diventa un indizio
  debole. Sui codici con un conto dietro — SSN, NINO, NHS, ABN, TFN — questa
  differenza non c'è.
- **La casella la disegna il sito.** Se un sito la cambia in modo che non
  riconosciamo più, quello strato smette di vedere. Per questo i ganci di rete
  restano, e per questo la sentinella esiste.
- **Non protegge da un sito ostile.** L'avversario di questo prodotto è la
  disattenzione — la tua, in un momento di fretta — non un sito che vuole
  rubarti i dati aggirando un'estensione.
- **Non è anonimizzazione GDPR forte.** È redazione assistita, come Mr. Rao:
  il contesto del messaggio resta, e serve la tua rilettura.

---

## Il rapporto con Mr. Rao

| | Mr. Rao | Mr. Rao Plus |
|---|---|---|
| Dove | sul tuo computer, sui file | nel browser, nella casella della chat |
| Quando | **prima**, mentre prepari il testo | nell'**ultimo metro**, mentre lo mandi |
| Motore | Python | lo stesso, portato in TypeScript |
| Licenza | AGPL-3.0, libero | commerciale |
| OCR | sì, legge le scansioni | no: dichiara di non aver potuto leggere |

Il port non è una riscrittura «migliorata»: un corpus di **239 casi** generato
eseguendo il motore Python originale gira a ogni build, e se i due motori
divergono la suite diventa rossa. Dove la divergenza è **voluta** — i nomi in
minuscolo — sta dietro un interruttore spento nel motore e acceso
nell'estensione, così il confronto resta un confronto con l'originale.

---

## Domande che arrivano sempre

**È gratis?** La 0.x sì. Quando diventerà a pagamento, chi c'era prima lo
saprà in anticipo — e la garanzia scritta è che **alla scadenza la protezione
continua**: cambia solo quello che l'estensione dice, non quello che fa.

**Manda i miei messaggi da qualche parte?** No, e non potrebbe: nessun
permesso verso host, nessuna chiamata di rete, codice leggibile.

**Se sbaglia e blocca una cosa che non è un dato?** C'è «mandalo lo stesso»,
che vale per un invio solo e scade dopo due minuti. E nelle impostazioni c'è
una lista «non toccare mai», dove metti i valori che nel tuo lavoro non sono
dati personali.

**Posso spegnerla su un sito?** Sì. E quando è spenta non dice «tutto pulito»:
dice «non sto guardando».
