# FAQ per chi ispeziona il motore di redazione

*This document in English: [PRIVACY_FAQ.en.md](PRIVACY_FAQ.en.md).*

Undici domande che un reviewer (umano o assistito da AI) fa aprendo
[`mr_rao/privacy.py`](../mr_rao/privacy.py), i test e questo documento.
Le risposte sono allineate al codice: se il codice cambia e questa pagina
no, vince il codice.

Per il funzionamento per tipo di dato: [PRIVACY.md](PRIVACY.md).  
Per il threat model del server locale: [SECURITY.md](../SECURITY.md).

---

## 1. È un motore di «anonimizzazione» GDPR?

**No — non nel senso forte del termine.**

In gergo EDPB/WP29 l’*anonimizzazione* è irreversibile e rende la
re-identificazione ragionevolmente impossibile. Mr. Rao fa **redazione
assistita** (e in parte pseudonimizzazione grezza): sostituisce pezzi di
testo con segnaposto (`{{CODICE_FISCALE}}`, `{{NAME}}`, …) e lascia il
resto del documento intatto — ruoli, fatti, struttura, cronologia degli
eventi: tutto ciò che identifica una persona **senza nominarla**. Gli
importi si possono togliere, ma la casella è spenta di default, quindi
con le impostazioni predefinite restano anche loro.

Usarlo per *ridurre* l’esposizione prima di un incolla in un’AI, con
controllo umano del prima/dopo, è lo scopo dichiarato. Usarlo per dire
«questo file non contiene più dati personali» **non** lo è.

Il codice e la documentazione parlano di redazione, sostituzione e
limiti — non di certificazione o DPIA automatica.

---

## 2. Come decide cosa togliere? C’è un modello?

**La decisione non passa da nessun modello.**

Ogni riconoscitore è una **coppia**: espressione regolare che propone un
candidato + **validatore** che accetta o rifiuta.

Esempi nel codice:

| Dato | Validatore |
|------|------------|
| IBAN | mod-97 (ISO 13616) |
| Carta | Luhn (ISO/IEC 7812) |
| Codice fiscale | struttura a 16 + carattere di controllo (informativo / recovery) |
| Partita IVA | 11 cifre + check all’italiana (informativo) |
| Telefono | prefisso, cellulare `3xx`, separatori o parola di contesto |
| Importo | valuta, migliaia o contesto contabile (spento di default) |

Lo stesso input produce sempre lo stesso output. Ogni sostituzione si può
spiegare indicando la regola. File principale:
[`mr_rao/privacy.py`](../mr_rao/privacy.py).

Reti neurali nel pacchetto ce ne sono due, e stanno tutte **a monte** di
questa tabella: RapidOCR (~30 MB di modelli `.onnx`) legge le scansioni,
magika (~3 MB, caricato da MarkItDown) indovina il tipo di file. Girano
offline sul processore e non decidono niente: consegnano del testo, e da lì
in poi comandano le regole. Dettaglio in
[PRIVACY.md](PRIVACY.md#come-funziona-il-riconoscimento).

---

## 3. Perché non usate Presidio / NER / un LLM per i nomi?

**Scelta di prodotto, non ignoranza dello stato dell’arte.**

Obiettivi vincolanti del tool:

1. **100% locale**, zero chiamate di rete nel codice applicativo  
2. **Deterministico** e ispezionabile da un CISO o da un collega  
3. **Nessun modello nella decisione** — quelli già inclusi (OCR, tipo di file) leggono e basta, e non c’è niente da scaricare o addestrare  
4. Specializzazione **documenti italiani** (CF, P.IVA, IBAN, abitudini di scrittura)

Presidio + NLP o un LLM locale alzerebbero il recall sui nomi in molti casi,
al prezzo di peso, di risultati non più ripetibili, di dipendenze in più e di
un motore che non si verifica leggendolo. Qui i nomi usano **quattro
segnali** (titolo, ruolo davanti ai due punti, email, elenco — ognuno con un
riscontro) e liste in
[`mr_rao/it_names.py`](../mr_rao/it_names.py) — incompleti per definizione.

A chi serve una pipeline multi-lingua enterprise conviene guardare altrove
(o estendere questo motore: è AGPL). A chi serve un pre-filtro offline e
ispezionabile prima di ChatGPT, questo è il perimetro giusto.

---

## 4. I cognomi rari e i nomi non in lista vengono sempre tolti?

**No.**

Segnali, dal più forte al più debole:

1. Titolo professionale (Dott., Ing., Avv., …)
2. Ruolo, due punti, cognome in maiuscolo (`Il Ministro: GIORGETTI`) — la
   firma degli atti pubblici italiani, aggiunta nella 1.17.0
3. Nome accanto a un’email
4. Nome proprio noto che «tira» la parola dopo


C'era una quinta regola — due parole maiuscole che non sembrano parole
italiane — che decideva **senza nessun riscontro**: è stata **ritirata nella
1.13.0**, perché su ventisette moduli amministrativi in bianco costava 2 529
sostituzioni sbagliate contro 27. Il prezzo è dichiarato: un nome fuori
elenco e senza contesto ora resta, e non produce nemmeno un sospetto.

Un cognome raro senza contesto può
restare. Un cognome che è anche parola comune può restare. Per questo
esiste il confronto **prima / dopo** nell’UI: non è cosmesi, è il
controllo previsto.

---

## 5. Cosa succede con le scansioni e l’OCR che sbaglia un carattere?

**La protezione è più debole sul testo sporco — e il motore lo tratta in due modi.**

I riconoscitori esatti cercano forme *valide*. L’OCR produce forme
*quasi* valide (`O`/`0`, `l`/`I`, …).

Dalla 1.5.x in poi:

- **Sospetti** — ciò che assomiglia a un dato e non è stato sostituito
  compare nel report (`suspects`) e in UI come «da controllare», con
  campione mascherato.  
- **Recupero OCR (1.6.x)** — per CF e IBAN: fino a **due** confusioni
  tipiche; si sostituisce **solo** se il checksum del candidato corretto
  torna. Non decide un’euristica: decide l’aritmetica.

Limiti restanti:

- tre o più errori → spesso né recovery né certezza  
- telefono e nome **non** hanno checksum  
- il degrado **è stato misurato** dalla 1.11 (`scripts/bench_scansioni.py`,
  tabella in [PRIVACY.md](PRIVACY.md#limiti-dichiarati)): su una fotocopia
  sbiadita a 200 DPI si perde in silenzio il **38%** dei dati, e i sospetti
  ne intercettano una minoranza. Resta vero però che **la carta è simulata,
  non vera**: il banco degrada le immagini in modo controllato e ripetibile,
  non sostituisce un corpus di scansioni fatte davvero  

Vedi anche l’avviso se l’OCR viene troncato per timeout: il testo in cima
al documento lo dichiara.

---

## 6. Come evitate di redigere protocolli, «Comitato Tecnico», date e numeri interni?

**Con un secondo banco di prova, non solo con il primo.**

Il filtro che toglie tutto è inutile quanto quello che non toglie nulla.
I test usano **due** testi:

| Testo | Atteso |
|-------|--------|
| Mail italiana con molte categorie di dato personale | sparisce ciò che deve |
| Verbale / atto pieno di enti, piani, protocolli, codici gara | **zero** redazioni spurie |

Zero non è un modo di dire: i test asseriscono `report.total == 0` sul
verbale. È una riga che si va a leggere in mezzo minuto, ed è il motivo per
cui questa pagina può permettersi di non arrotondare altrove.

Presidi tipici:

- validatori (mod-97, Luhn) contro numeri lunghi casuali  
- contesto per telefoni, P.IVA, importi, date di nascita  
- la regola che indovinava i cognomi senza riscontri è stata **ritirata**
  (1.13.0): era la fonte principale delle redazioni spurie sui moduli  
- IBAN: almeno una lettera già presente nelle prime due posizioni nel
  recupero OCR (regressione: un numero d’ordine diventava un IBAN
  «valido» al mod-97)

File rilevanti: `tests/test_privacy*.py`, `tests/test_sospetti.py`,
esempi nel README.

---

## 7. Il report «N redazioni» basta per fidarsi?

**No. Zero redazioni non significa «documento pulito».**

Due silenzi diversi:

- non c’erano dati personali riconoscibili  
- c’erano, ma in forma che il motore non ha saputo validare  

I **sospetti** esistono per spezzare l’ambiguità. Il confronto prima/dopo
è il controllo che conta. Un filtro automatico di cui ci si fida
ciecamente è un rischio — è scritto anche in UI e README.

I campioni nei sospetti sono mascherati (`RS••••••••••••2S`): abbastanza
da ritrovarli nel testo, non da leggerli dal report da soli.

---

## 8. Che succede se passo lo stesso documento due volte, o a pezzi?

**I segnaposto non sono numerati.** Due persone diverse diventano lo stesso
`{{NAME}}`:

```
Scrivi a Mario Rossi <m.rossi@a.it> e a Luigi Bianchi <l.bianchi@b.it>
   →  Scrivi a {{NAME}} <{{EMAIL}}> e a {{NAME}} <{{EMAIL}}>
```

Sono due proprietà vere e opposte, e conviene saperle prima di scoprirle:

- **in uscita non si può ricollegare chi era chi.** È un bene per
  l'esposizione, e conferma la domanda 1: non è uno pseudonimizzato su cui
  fare join, né una tabella di corrispondenze da custodire. Non esiste
  nessuna mappa da rubare, perché non viene mai costruita;
- **un documento spezzato in pezzi perde il contesto fra un pezzo e
  l'altro.** I nomi si riconoscono anche dal contesto — un titolo davanti,
  un'email accanto, un nome proprio che tira il cognome. Se il titolo resta
  nel primo blocco e il nome finisce nel secondo, quel segnale non c'è più.

La seconda è la cosa che si rompe davvero incollando un documento lungo a
blocchi in una chat. **Conviene convertire il documento intero e incollare
il risultato**, non convertire i pezzi.

Due passaggi dello stesso file danno invece lo stesso risultato: il motore è
deterministico (domanda 2), non c'è stato che si accumuli fra una
conversione e l'altra.

---

## 9. Posso usarlo in studio / azienda come controllo privacy «ufficiale»?

**Come controllo *compensativo unico*: no.  
Come tool nel processo: sì, se lo inquadrate onestamente.**

Inquadramento sensato:

1. Conversione e redazione **locali**  
2. Revisione umana del risultato (e dei sospetti)  
3. Solo allora invio a un modello o a un consulente  

**Il controllo è il passo 2, non il passo 1.** Lo strumento rende quella
revisione praticabile su volumi che a mano non si reggerebbero; non la
sostituisce, e non sposta la responsabilità di chi firma l'invio. Chi cita
il passo 1 e il passo 3 saltando quello in mezzo sta descrivendo un altro
processo.

Non sostituisce:

- valutazione d’impatto / policy interne  
- DLP enterprise, classificazione automatica su larga scala  
- obblighi contrattuali con i clienti sulla minimizzazione  

Licenza **AGPL-3.0**: uso interno e consulenza a pagamento sono
compatibilissimi; se *modificate* il software e lo offrite *come servizio
di rete* ad altri, scatta l’obbligo di offrire il sorgente della vostra
versione (sez. 13). Dettaglio in [LICENSE](../LICENSE) e README.

---

## 10. Dove guardare nel codice e nei test (mappa per reviewer / AI)?

| Cosa | Dove |
|------|------|
| Pipeline e riconoscitori | [`mr_rao/privacy.py`](../mr_rao/privacy.py) — `apply_privacy_filter`, validatori, `find_suspects`, `cf_ocr_recover`, `iban_ocr_recover` |
| Liste nomi / parole comuni | [`mr_rao/it_names.py`](../mr_rao/it_names.py) |
| Opzioni da form/CLI/profili | `PrivacyOptions`, `options_from_form`, [`mr_rao/profiles.py`](../mr_rao/profiles.py) |
| Principi e limiti | [PRIVACY.md](PRIVACY.md) |
| Test duali e regressioni | `tests/test_privacy.py`, `tests/test_privacy_riconoscitori.py`, `tests/test_sospetti.py` |
| Sicurezza server locale (altro pezzo) | [SECURITY.md](../SECURITY.md), `tests/test_security.py`, `tests/test_limiti_ocr.py` |
| Lezioni da bug reali | [CHANGELOG.md](CHANGELOG.md) — ogni voce dice il bug, non solo la funzione |

Punto d’ingresso per un’analisi automatica: leggere il docstring di
modulo di `privacy.py`, poi `apply_privacy_filter` (ordine delle fasi),
poi i test che fallivano sulle regressioni citate nel changelog.

---

## 11. Se trovate un buco o un overclaim, cosa fare?

1. **Riprodurre** con un pezzo di testo minimo (niente documenti reali di
   clienti in issue pubbliche).  
2. Dire cosa vi aspettavate e cosa è successo.  
3. Preferire una issue su GitHub; per qualcosa che ritenete sensibile
   (es. bypass sistematico su una classe di documenti), contatto privato
   all’autore come in [SECURITY.md](../SECURITY.md).

Contributi che alzano la qualità senza gonfiare i falsi positivi sul
verbale amministrativo sono i più utili: un riconoscitore che «prende
tutto» peggiora lo strumento.

---

## In una frase

> Mr. Rao non garantisce l’assenza di dati personali nel testo in uscita.
> Applica regole e checksum sui formati italiani, segnala i casi dubbi,
> e chiede una revisione umana. È ispezionabile e ripetibile; non è una
> certificazione di anonimizzazione.

Se questa frase e il codice non vi bastano, non usatelo come unico
controllo — e fate bene.
