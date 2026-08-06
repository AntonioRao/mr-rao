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
| P2.1 | Test E2E portable (health + convert PDF/txt) in CI locale | Build 390 MB fragile | TODO |
| P2.2 | Test job cancel / watch start-stop | Race conditions | TODO |
| P2.3 | Test shell integration (mock) | Regressioni SendTo | TODO |
| P2.4 | Gate pre-commit automatico (hook git opzionale) | Disciplina | TODO |

---

## P3 — Feature di profondità (no bloat)

| ID | Item | Note | Stato |
|----|------|------|--------|
| P3.1 | OCR multi-lingua reale (modelli) o togliere la claim | Oggi lingua è advisory | TODO |
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

## Metriche di “fatto” per P0

- [ ] Click destro → Invia a Mr. Rao → browser aperto entro 3s  
- [ ] Markdown del file visibile in UI  
- [ ] Nessuna console che flasha e sparisce senza spiegazione  
- [ ] Funziona sia da install Python sia da portable exe  
