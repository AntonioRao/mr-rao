# Backlog & piano di priorità — Mr. Rao

Ultimo aggiornamento: UI Design System 2.0 (glass / aurora / float).

## Principio

> Meno ingressi confusi, più coerenza.  
> Non aggiungere feature finché i journey OS ↔ UI non sono prevedibili.

---

## P0 — Coerenza UX / OS (impatto alto)

| ID | Item | Perché | Stato |
|----|------|--------|--------|
| P0.1 | **SendTo / Apri con → UI con risultato** | Oggi apre solo CLI convert + shell; l'utente si aspetta il browser | TODO |
| P0.2 | Flusso unificato: convert → apri `http://127.0.0.1:5000` con job/result in sessione o query | Un solo mental model | TODO |
| P0.3 | Se server già su: riusa porta, non aprire seconda istanza cieca | Evita porte occupate / finestre morte | TODO (parziale: portcheck) |
| P0.4 | Feedback visibile su fallimento shell (message box o log file) | Shell che flasha e sparisce = zero fiducia | TODO |

**Design proposto P0.1**

1. `open_with` / SendTo lanciano `MrRao.exe --ui <file>` (o bat equivalente).  
2. Se server non up → start + wait health.  
3. POST convert (sync o job) → redirect browser a `/` con risultato in memoria (job_id).  
4. UI apre tab risultato automaticamente.

---

## P1 — UX prodotto (dopo P0)

| ID | Item | Perché | Stato |
|----|------|--------|--------|
| P1.1 | **UI Design System 2.0** (glass, aurora, float, glow) | Schermata disordinata post-feature dump | **DONE** |
| P1.2 | Gerarchia a step 1–4: Carica → Imposta → Risultato → Extra | Riduce carico cognitivo | **DONE** (1.2.1) |
| P1.2b | Ripristino funzionalità/tooltip 1.1.4 sul layout 2.0 (senza snellire il prodotto) | 1.2.0 aveva sfoltito troppo | **DONE** (1.2.1) |
| P1.3 | Empty states e microcopy coerenti | Professionalità | **DONE** |
| P1.4 | Preview Markdown più fedele (liste, tabelle) | Anteprima debole | TODO |
| P1.5 | Mobile / narrow viewport polish | Uso da tablet | TODO |

---

## P2 — Affidabilità & qualità

| ID | Item | Perché | Stato |
|----|------|--------|--------|
| P2.1 | Test E2E portable (health + convert) | Il build avvia l'eseguibile, interroga `/api/health`, converte un `.docx` e confronta l'icona: se qualcosa non torna, **respinge il pacchetto**. Manca solo il giro in CI | **DONE in locale** (1.4.2) |
| P2.2 | Test job cancel / watch start-stop | Race conditions | TODO |
| P2.3 | Test shell integration (mock) | Regressioni SendTo | TODO |
| P2.4 | Gate pre-commit automatico (hook git opzionale) | Disciplina | TODO |

---

## P3 — Feature di profondità (no bloat)

| ID | Item | Note | Stato |
|----|------|------|--------|
| P3.1 | OCR multi-lingua reale (modelli aggiuntivi) | Il selettore che non faceva nulla è stato **rimosso** in 1.3.2: meglio nessun comando che uno che promette e non mantiene. Il modello attuale copre gli alfabeti latini | TODO |
| P3.2 | Diff semantico 2 PDF (non solo A/B stacked) | Compare attuale è merge etichettato | TODO |
| P3.3 | Tray: stato job + “apri ultimo risultato” | Tray oggi minimale | TODO |
| P3.4 | Portable firmato / zip release versionato | Distribuzione team | TODO |

---

## P4 — Debito tecnico

| ID | Item | Stato |
|----|------|--------|
| P4.1 | Rinominare cartella repo `markitdown-webapp` → `mr-rao` | TODO |
| P4.2 | Rimuovere shim MarkItDown quando nessuno li usa più | TODO |
| P4.3 | Spezzare `app.js` in moduli ES se cresce ancora | TODO |
| P4.4 | CSS già estratto in `static/css/app.css` | **DONE** |

---

## Non fare (per ora)

- Nuovi preset / nuovi formati file “per completezza”
- Rewrite framework frontend (React/Vue): overhead ingiustificato
- Auth / multi-utente: fuori scope tool locale
- Cloud sync di qualsiasi tipo (rompe il value prop)

---

## Ordine di lavoro consigliato

```
P0.1 → P0.2 → P0.3 → P0.4
         ↓
      P1.4 / P1.5
         ↓
      P2.x (test)
         ↓
      P3 solo se richiesta esplicita
```

---

## P0-bis — Esito audit 1.3.0 (chiuso)

Aggiunto dopo l'audit di agosto 2026. Tutti verificati eseguendo, non ipotizzati.

| ID | Item | Stato |
|----|------|-------|
| A.1 | Il repository committato non era importabile; metà delle correzioni 1.1.2/1.1.3 viveva solo sul disco | **DONE** (1.3.0) |
| A.2 | Cartelle predefinite dentro OneDrive → contraddiceva «zero cloud» | **DONE** (1.3.0) |
| A.3 | `GET /api/folders/defaults` creava directory (raggiungibile con un `<img src>`) | **DONE** (1.3.0) |
| A.4 | `THIRD_PARTY.md` sbagliava la licenza di Scrubadub e ometteva python-stdnum (LGPL) | **DONE** (1.3.0) |
| A.5 | `taskkill /F` nel `.bat` poteva troncare i `.md` in scrittura | **DONE** (1.3.0) |
| A.6 | `APP_VERSION` ferma a 1.2.1 col changelog già a 1.2.4 | **DONE** (1.3.0) |

### Lezioni da non ripetere

- **Le licenze non si scrivono a mano.** L'elenco manuale sbagliava una licenza
  e ne ometteva un'altra con obblighi veri. Ora si genera.
- **Un default può smentire il claim del prodotto.** Nessun bug nel codice:
  solo una cartella predefinita nel posto sbagliato.
- **Il changelog non è una prova.** Dichiarava rilasciate correzioni che in git
  non c'erano.

## P2-bis — Igiene di rilascio

| ID | Item | Perché | Stato |
|----|------|--------|-------|
| P2.5 | `gen_third_party.py --check` dentro il quality gate | Le licenze scadono in silenzio | TODO |
| P2.6 | Gate: `APP_VERSION` senza voce di changelog = errore | Ha già sbagliato una volta | TODO |
| P2.7 | Verifica «HEAD è importabile» in CI | È già successo di committarne uno rotto | TODO |
| P2.8 | Valutare la rimozione di Scrubadub | Misurato su testo inglese: stesse redazioni con e senza, e da solo spezzava il testo. Rimosso | **DONE** (1.3.3) |

## P0-ter — Riconoscimento tollerante agli errori OCR

Emerso testando il repo appena clonato su un PDF scansionato vero.

Stesso contenuto, due strade: letto da **immagine** produce 3 redazioni, letto
da **PDF scansionato** ne produce 1. L'OCR storpia i caratteri — `A01` diventa
`AD1`, `IBAN IT60X…` diventa `TBAN1TB0X…` — e le espressioni regolari non
riconoscono più il codice, che resta nel testo deformato ma ancora identificante.

| ID | Item | Note | Stato |
|----|------|------|-------|
| A.7 | Avviso nel risultato quando la redazione ha lavorato su testo OCR | Mitigazione immediata: chi legge sa che lì deve controllare | **DONE** (1.3.2) |
| A.8 | Riconoscimento tollerante alle confusioni tipiche dell'OCR sui formati a struttura fissa | Fatto per CF e IBAN, fino a 2 correzioni, e si accetta solo se il checksum torna. Attenzione: il checksum **non basta** — la prima versione trasformava un numero d'ordine in un IBAN valido. Serve anche restringere i candidati | **DONE** (1.6.0) |
| A.9 | Banco di prova con scansioni a qualità decrescente | Serve un numero, non un'impressione: quante redazioni si perdono a 300, 200, 150 DPI | TODO |

**Perché A.8 è fattibile senza peggiorare i falsi positivi.** Un IBAN ha un
checksum: si possono generare le varianti plausibili di una stringa dubbia e
accettarne una solo se il mod-97 torna. Lo stesso vale per il codice fiscale,
che ha un carattere di controllo. Su formati senza checksum questa strada non
si può percorrere, e infatti non va percorsa.

## P1-bis — Interfaccia in inglese (dopo il lancio)

Il README è bilingue, l'interfaccia no. Tradurla è una **funzionalità**, non
una passata di traduzione, e va fatta nell'ordine giusto.

| ID | Item | Note | Stato |
|----|------|------|-------|
| P1.6 | Estrarre le stringhe della UI in un dizionario `it` / `en` + selettore lingua | ~80 stringhe fra template, JS e messaggi del server: i tooltip sono lunghi apposta | TODO |
| P1.7 | **Prima** di P1.6: rendere i riconoscitori innestabili per Paese | Oggi riconosce solo dati italiani (CF, P.IVA, IBAN, nomi IT). Una UI inglese su un motore solo-italiano promette a un utente inglese di proteggere dati che non sa riconoscere — lo stesso errore del selettore lingua OCR | TODO |

**Perché in quest'ordine.** L'inglese nell'interfaccia dice «questo strumento
è per te» a chi parla inglese. Se poi il filtro privacy ignora un National
Insurance Number o un SSN, la promessa è tradita nel punto che conta di più.
Fino ad allora, la combinazione onesta è quella attuale: README in inglese
che spiega il perimetro italiano, interfaccia in italiano per chi la usa.

---

## Metriche di “fatto” per P0

- [ ] Click destro → Invia a Mr. Rao → browser aperto entro 3s  
- [ ] Markdown del file visibile in UI  
- [ ] Nessuna console che flasha e sparisce senza spiegazione  
- [ ] Funziona sia da install Python sia da portable exe  
