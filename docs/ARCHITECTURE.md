# Architettura Mr. Rao

## Panoramica

```
Browser ──HTTP──► Flask (routes) ──► jobs (thread pool) ──► converter
                                                         ├── eml_parser (+ BeautifulSoup4)
                                                         ├── markitdown (+ Magika)
                                                         ├── ocr_service (RapidOCR + pdfplumber)
                                                         └── privacy (sequenza a pacchetti: core + it + en)
CLI / SendTo ──► mr_rao.cli convert ──► stesso converter
Watch (UI/CLI) ──► watch_service loop ──► converter
Tray ──► open browser / quit
```

## Frontend (UI 2.0)

| Asset | Ruolo |
|-------|--------|
| `templates/index.html` | Markup semantico, gerarchia journey |
| `static/css/app.css` | Design system: glass, aurora, float, glow |
| `static/js/app.js` | Interazioni, job poll, tooltip, watch |
| `static/img/*` | Logo, favicon, ico Desktop |

**Journey UI principale**

1. Hero (brand)  
2. Drop zone (azione primaria)  
3. Control bar (profilo + privacy)  
4. Opzioni avanzate (collassate)  
5. Risultato (tabs + export)  
6. Secondari: sessione + cartella automatica  

## Moduli backend

| Modulo | Responsabilità |
|--------|----------------|
| `config.py` | Brand, path (frozen/dev), limiti, env |
| `mr_rao/app_factory.py` | Factory Flask, middleware sicurezza Host/CSRF |
| `mr_rao/routes.py` | HTTP API + template |
| `mr_rao/jobs.py` | Job store in-memory, progress, cancel, worker limit |
| `mr_rao/converter.py` | Pipeline unica + frontmatter + merge + fallback text |
| `mr_rao/eml_parser.py` | Thread email → Markdown + allegati |
| `mr_rao/ocr_service.py` | OCR immagini/PDF + tabelle |
| `mr_rao/privacy.py` | Motore: sequenza dei riconoscitori, pacchetti, sospetti, recupero OCR |
| `mr_rao/it_names.py` | Vocabolari italiani: nomi, cognomi, parole comuni maiuscole |
| `mr_rao/en_formats.py` | Validatori anglosassoni (NHS, NINO, SSN, ITIN, ABA, SIN, ABN, TFN, MRZ) con i vettori di prova accanto |
| `mr_rao/user_folders.py` | Cartelle di lavoro, rilevamento cartelle sincronizzate |
| `mr_rao/profiles.py` | Preset conversione |
| `mr_rao/watch_service.py` | Hotfolder in-process |
| `mr_rao/tray.py` | System tray opzionale |
| `mr_rao/cli.py` | CLI convert / watch / health |
| `mr_rao/portcheck.py` | Porta libera + messaggi multi-istanza |

## Il motore privacy

Ogni riconoscitore è un **`Passo`** in `SEQUENZA`, e dichiara quattro cose:
nome stabile, pacchetto, interruttore che lo accende, priorità.
`apply_privacy_filter` è un ciclo: un passo gira se il suo pacchetto è fra
quelli scelti **e** se il suo interruttore è acceso.

**I pacchetti** (`CORE`, `IT`, `EN`) separano ciò che vale ovunque da ciò
che vale in un Paese solo. Il nucleo non si spegne: l'IBAN passa il mod-97
in tutti i Paesi SEPA, la carta passa Luhn ovunque. Sono cumulabili — lo
studio italiano col contratto inglese è il caso d'uso vero — e scegliibili
da interfaccia, JSON e riga di comando.

**La priorità è del tipo di dato, non del pacchetto.** Codice fiscale (it)
e SSN (en) girano insieme, prima dei telefoni: è ciò che impedisce a un
telefono di mangiarsi una partita IVA. Se l'ordine seguisse i pacchetti,
aggiungerne un terzo lo romperebbe, e si vedrebbe come una redazione
sbagliata invece che come un errore di ordinamento.

**Prosa o modulo** (`PrivacyOptions.prosa`) decide quanto pretendere prima
di sostituire un nome: su una lettera un riscontro solo negli elenchi
basta, su un modulo è quasi sempre l'etichetta di un campo. Misurato su 127
documenti amministrativi e 1500 email vere: pretendere due riscontri toglie
2739 sostituzioni sbagliate sui moduli e ne costa 609 sulle lettere.

Il segnale che lo decide sta **nel PDF, non nel testo**: le caselle di un
modulo sono righe e rettangoli vettoriali, sopravvivono alla lettura del
file e muoiono nella conversione. Per questo `_e_prosa()` vive in
`converter.py` e non nel motore. Sulle scansioni resta `None`, perché
contare vettori su un'immagine darebbe zero e zero verrebbe letto come
«prosa»: la risposta giusta per il motivo sbagliato.

**I nomi sono a livelli di prova.** Titolo, firma, indirizzo di posta
accanto → sostituzione. Riscontro debole → **sospetto**, non sostituzione:
il documento resta leggibile e chi controlla sa dove guardare.

## Flusso conversione

1. Upload validato (estensione + size richiesta)  
2. Bytes → temp monouso (`convert_bytes`)  
3. Engine: `auto` | `rapidocr` | `markitdown`  
4. Tipo di documento dedotto (`_e_prosa`) se non imposto  
5. Privacy opzionale → report + eventuale `markdown_raw`  
6. Frontmatter YAML opzionale  
7. Cleanup temp  

## Sicurezza locale

- Bind default `127.0.0.1`  
- Allow-list header `Host` (anti DNS rebinding), **anche su `0.0.0.0`**: gli
  indirizzi di questa macchina, non `*`  
- `Sec-Fetch-Site` esterno rifiutato sulle mutazioni, con `Origin` come ripiego
  per chi non lo manda (anti CSRF)  
- `frame-ancestors 'none'`, `nosniff`, `no-referrer` su ogni risposta  
- Tetto di tempo sull'OCR (`MR_RAO_OCR_TIMEOUT`), controllato fra una pagina e
  l'altra come l'annullamento  
- `debug` solo con `MR_RAO_DEBUG=1`  
- Nessuna autenticazione (single-user locale)  

Dettaglio e ragioni in [SECURITY.md](../SECURITY.md).

## Gap noti (vedi BACKLOG)

- **Scansioni**: i riconoscitori cercano forme valide, l'OCR ne produce di quasi valide.
  Mitigato in due modi — recupero vincolato dal checksum per CF e IBAN, e segnalazione
  dei sospetti per il resto — ma resta il limite di efficacia principale (P0-ter).
- **Nomi italiani**: sui documenti amministrativi il riconoscitore produce ancora migliaia di
  sostituzioni sbagliate, misurate su 127 documenti in bianco (#5). Il parametro prosa/modulo
  ne toglie la maggior parte, ma il metodo a elenchi ha un tetto di precisione che i vincoli
  incrementali non alzano.
- **Interfaccia in italiano e inglese** (#1, fase 3): scelta dal browser, cambiabile con un clic, e il
  documento prodotto segue la stessa lingua. Resta italiana la riga di comando.
- **Nessuna autenticazione**: tool locale per una persona, non un servizio.

## Documentazione correlata

- [BACKLOG.md](BACKLOG.md) — priorità P0–P4  
- [PORTABLE.md](PORTABLE.md) — build offline  
- [PRIVACY.md](PRIVACY.md) — redazioni  
- [BEAUTIFULSOUP.md](BEAUTIFULSOUP.md) — HTML email  
