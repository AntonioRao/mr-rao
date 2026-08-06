# Privacy — Mr. Rao

## Principi

1. **Tutto locale** — nessun invio a servizi esterni
2. **Font di sistema** — nessuna richiesta a Google Fonts
3. **Cronologia** solo in memoria, mai su disco
4. **File temporanei** cancellati a conversione finita

## Come funziona il riconoscimento

Ogni riconoscitore è **un'espressione regolare più un validatore**: il
pattern propone un candidato, il validatore decide se è davvero un dato
personale. È quello che tiene bassi i falsi positivi senza rinunciare alla
copertura — un IBAN si accetta solo se il mod-97 torna, una carta solo se
passa il controllo di Luhn, un numero di dieci cifre è un telefono solo se
ha un prefisso, un separatore o una parola di contesto davanti.

Nessun modello, nessuna rete neurale: il motore è deterministico. Lo stesso
documento dà sempre lo stesso risultato, e ogni sostituzione si può
spiegare guardando la regola che l'ha prodotta.

## Cosa viene sostituito

| Tipo | Segnaposto | Come viene deciso |
|------|-----------|-------------------|
| Email | `{{EMAIL}}` | Forma dell'indirizzo |
| Indirizzi web | `{{URL}}` | `http`, `https`, `www.` — solo questi |
| Telefoni | `{{PHONE}}` | Prefisso `+39`, cellulari `3xx`, parola di contesto (`cell`, `tel`, `fax`), oppure fisso con separatori |
| Codice fiscale | `{{CODICE_FISCALE}}` | Struttura a 16 caratteri. Il **carattere di controllo** non rifiuta, segnala |
| P.IVA | `{{PARTITA_IVA}}` | Prefisso `IT` o contesto fiscale vicino |
| IBAN | `{{IBAN}}` | **Mod-97** (ISO 13616) |
| Coordinate non-IBAN | `{{BBAN}}` | CIN+ABI+CAB+conto, con contesto bancario vicino |
| Carte di pagamento | `{{CARD}}` | **Luhn** (ISO/IEC 7812) |
| Indirizzi | `{{ADDRESS}}` | Via, viale, piazza, corso, largo, contrada e altri, con civico, CAP e comune |
| Nomi di persona | `{{NAME}}` | Vedi sotto |
| Chiavi e password | `{{SECRET}}` | Token, chiavi API, JWT, blocchi di chiave privata, `password: ...` |
| Date di nascita | `{{DATE}}` | **Spento di serie.** Solo con contesto di nascita accanto |
| Importi | `{{AMOUNT}}` | **Spento di serie.** Valuta, migliaia o contesto contabile |

## I nomi di persona: quattro segnali

Un elenco di nomi non è mai completo, e affidarsi solo a quello lascia
passare tutti i cognomi non comuni. Valgono quindi anche le regole di
contesto, dal segnale più forte al più debole:

1. **Titolo professionale davanti** — Dott., Ing., Geom., Avv., Sig.
2. **Nome accanto a un indirizzo di posta** — `Tizio Caio <t.caio@x.it>`.
   È il caso più frequente nelle email.
3. **Nome proprio riconosciuto** che tira dentro la parola successiva.
4. **Euristica del cognome** — due parole maiuscole di fila che non sono
   parole italiane sono quasi sempre nome e cognome.

La quarta è l'unica che può sbagliare, ed è l'unica che si può spegnere da
sola: casella **«Deduci i cognomi sconosciuti»**, campo
`privacy_name_guess`, opzione `--no-name-guess`. È spenta di serie nel
profilo **Fatture**, dove le denominazioni sociali abbondano.

Due presidi la tengono a bada: un elenco di parole italiane che capita di
trovare con l'iniziale maiuscola (mesi, saluti, enti, città, termini
amministrativi) e un controllo sulle terminazioni — «Industriale» e
«Tecnico» finiscono come finiscono le parole, non come finiscono i cognomi.

## Come è verificato

Il banco di prova sono **due** testi, non uno:

- una **mail italiana** con nomi, indirizzi, recapiti, URL, IBAN, P.IVA,
  codice fiscale e importo: deve sparire tutto;
- un **verbale amministrativo** pieno di «Comitato Tecnico», «Piano
  Industriale», «Fase Uno», numeri di protocollo, date e codici gara:
  **non deve sparire niente**.

Il secondo conta quanto il primo. Un filtro che redige tutto è inutile
esattamente come uno che non redige niente, e il verbale è quello che
impedisce di guadagnare copertura peggiorando lo strumento.

## I sospetti

I riconoscitori cercano forme **valide**. L'OCR produce forme **quasi**
valide: `A01` letto `AD1`, `IT60` letto `lT60`. La struttura non torna, il
dato resta nel testo — e resta leggibile da una persona.

Sostituire senza certezza vorrebbe dire redigere mezzo documento. Ma
tacere è peggio: «3 redazioni» su un documento pulito e «3 redazioni» su
un documento che il riconoscitore non ha saputo leggere sono lo stesso
numero e due situazioni opposte.

Per questo, dopo la sostituzione, un passaggio sul testo rimasto segnala
ciò che somiglia a un dato personale senza esserlo abbastanza da poterlo
togliere. Compaiono nel rapporto come `suspects`, e nell'interfaccia
accanto al conteggio: **«🛡️ 3 redazioni · ⚠️ 2 da controllare»**.

I campioni sono mascherati (`RS••••••••••••2S`): quanto basta a
ritrovarli nel documento, non a leggerli.

Un documento amministrativo pulito — protocolli, delibere, codici gara,
date — produce **zero** sospetti. Se ogni numero diventasse un avviso,
l'avviso non varrebbe più niente.

## Report

La risposta API include `redaction: { total, counts }`, l'interfaccia mostra
il totale e la scheda **«Confronto privacy»** mostra il testo prima e dopo.
Quella scheda è il controllo che conta: è lì che si vede cosa è stato tolto
e, soprattutto, cosa è sfuggito.

## Limiti dichiarati

- **Nessun elenco di cognomi è completo.** L'euristica copre molto ma non
  tutto, e un cognome che assomiglia a una parola italiana può restare.
- **Sulle scansioni la protezione è più debole.** I riconoscitori cercano un
  codice scritto correttamente: se l'OCR legge `A01` come `AD1`, il codice
  non viene riconosciuto. Il risultato lo segnala con un avviso.
- **I formati sono italiani.** Un numero di telefono tedesco o un codice
  fiscale spagnolo non hanno un riconoscitore dedicato.
- **Non sostituisce una valutazione DPIA o un parere legale.**
