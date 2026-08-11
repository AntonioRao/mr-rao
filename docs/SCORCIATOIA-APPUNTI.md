# La scorciatoia da tastiera che redige gli appunti

*This document in English: [SCORCIATOIA-APPUNTI.en.md](SCORCIATOIA-APPUNTI.en.md).*

Copi il testo, premi la combinazione, incolli. Quello che arriva è già
redatto.

Non c'è niente da aprire, caricare o scaricare: **gli appunti sono il
posto**. Serve a togliere l'attrito — apri il programma, carica il file,
aspetta, scarica, copia — che è il vero motivo per cui un documento finisce
dentro una chat senza passare da qui.

## Come si usa

1. Seleziona il testo e fai **Ctrl+C**. Da un PDF, da Word, da Outlook, da
   una pagina web: indifferente, è testo negli appunti.
2. Premi **Ctrl+Alt+R**.
3. Compare una notifica: *«9 dati redatti · 2 da controllare»*.
4. Fai **Ctrl+V** dove stavi andando. Quello che arriva è redatto.

Il motore è lo stesso della conversione dei file — le stesse regole, gli
stessi controlli aritmetici, gli stessi test. Non esiste una seconda
implementazione che possa divergere.

## Cosa dice la notifica, e perché conta

Una trasformazione silenziosa è pericolosa: senza un messaggio non si
distingue «ha funzionato» da «non è partito». Quindi la notifica compare
**sempre**, anche quando non trova niente.

I due numeri non sono la stessa cosa:

- **redatti** — sostituiti. Quel dato non è più negli appunti.
- **da controllare** — i **sospetti**: il programma ha visto qualcosa che
  *somiglia* a un dato personale ma non ha superato il proprio controllo,
  e per non rovinare il testo **non l'ha tolto**.

Un «da controllare» maggiore di zero significa che negli appunti è rimasto
qualcosa che vale la pena guardare prima di incollare. La notifica dice i due
numeri e finisce lì: **non è cliccabile**, e non esiste un confronto
prima/dopo per il testo passato dalla scorciatoia. Il confronto sta
nell'interfaccia, e riguarda i file convertiti.

## Se la redazione toglie qualcosa che serviva

L'originale resta disponibile per la sessione: **«Ripristina l'originale»**
nel menu dell'icona vicino all'orologio. Sta **in memoria** e non viene mai
scritto su disco — sparisce quando il programma si chiude.

## Come si spegne

Con una variabile d'ambiente, e **solo** con quella: nell'interfaccia non c'è
un interruttore.

    MR_RAO_SCORCIATOIA=0

Una variabile sola per due cose — se è accesa e quale combinazione — perché
sono la stessa domanda, e tenerle separate permetterebbe lo stato incoerente
«accesa, combinazione vuota»: una scorciatoia che non risponde senza dire
perché.

La combinazione si cambia allo stesso modo, per esempio
`MR_RAO_SCORCIATOIA=ctrl+alt+m` se Ctrl+Alt+R è già occupata da altro. Se
la combinazione risulta già presa da un altro programma, Mr. Rao lo dice
all'avvio invece di restare zitto e non funzionare.

## Perché non è un keylogger, e come lo si verifica

Un programma che sta acceso e reagisce a una combinazione di tasti ha, da
fuori, la stessa sagoma di un programma che registra quello che scrivi. Per
uno strumento di privacy la somiglianza non basta smentirla a parole, quindi
qui c'è la differenza tecnica, che chiunque può controllare nel codice
(`mr_rao/appunti.py`, licenza AGPL).

**Windows offre due meccanismi diversi, e noi usiamo quello ristretto.**

- `SetWindowsHookEx(WH_KEYBOARD_LL)` è un **gancio di basso livello**: il
  programma riceve **ogni tasto** premuto sulla macchina, e decide lui cosa
  farne. È il meccanismo con cui si scrive un keylogger. **Mr. Rao non lo
  usa.**
- `RegisterHotKey` dichiara a Windows **una singola combinazione**. Windows
  la sorveglia lui e recapita un messaggio solo quando *quella* viene
  premuta. Il programma non vede né può vedere gli altri tasti. **È questo
  che usa Mr. Rao.**

Non è una differenza di buone intenzioni: è una differenza di cosa il
sistema operativo consegna al programma. Con `RegisterHotKey` gli altri tasti
non arrivano nemmeno.

Allo stesso modo, **gli appunti non vengono sorvegliati**. Non c'è nessun
controllo periodico del loro contenuto: vengono aperti solo quando la
combinazione scatta, letti una volta, riscritti una volta e richiusi. Fra
una pressione e l'altra il programma non sa e non può sapere cosa lei ha
copiato.

E resta vero tutto il resto: **niente rete** (nessuna richiesta esce dalla
macchina) e **niente disco** (né il testo originale né quello redatto
vengono scritti in un file).

## Il limite, detto

Dipende ancora dal fatto che lei si ricordi di premere. Toglie l'attrito,
non la decisione. Un testo incollato senza premere niente è un testo non
redatto, esattamente come prima.

Vale anche il limite del motore: quello che il motore non riconosce qui non
lo riconosce, né più né meno che sulla conversione di un file. I limiti
dichiarati stanno in [PRIVACY.md](PRIVACY.md#limiti-dichiarati).
