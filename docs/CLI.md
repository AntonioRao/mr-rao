# Riga di comando

Tutto quello che si fa dall'interfaccia si fa anche da qui — e il contrario
vale come regola del progetto: **nessuna funzione può esistere solo da riga di
comando**, perché chi usa Mr. Rao apre una pagina, non un terminale.

Questo file esiste perché non era così: per venti release le opzioni non
erano scritte da nessuna parte. Ora `scripts/check_docs.py` **interroga il
parser vero** e fallisce se ne compare una che qui non c'è.

```bash
python -m mr_rao.cli --help
```

Nel portable l'eseguibile fa le stesse cose: `MrRao.exe convert ...`.

---

## `convert` — converti uno o più file

```bash
python -m mr_rao.cli convert fattura.pdf -o convertiti/
```

`files` accetta più percorsi e anche cartelle intere.

### Dove finisce il risultato

| opzione | cosa fa |
|---------|---------|
| `-o`, `--output` | File o cartella di destinazione. Senza, il `.md` nasce accanto all'originale |
| `--merge` | Unisce tutto in un solo Markdown invece di un file per documento |
| `--title` | Titolo del documento unificato (vale solo con `--merge`) |
| `--attendi` | Tiene aperta la finestra se c'è qualcosa da controllare. Lo usa la voce del tasto destro: in uno script è inutile |

### Come viene convertito

| opzione | cosa fa |
|---------|---------|
| `--engine {auto,rapidocr,markitdown}` | `auto` decide dal file. `rapidocr` forza l'OCR, `markitdown` lo esclude |
| `--force-ocr` | Passa dall'OCR anche su un PDF che ha già un testo estraibile |
| `--no-tables` | Non estrarre le tabelle |
| `--no-frontmatter` | Niente intestazione YAML in testa al Markdown |
| `--clean` | Output pulito, pensato per finire dentro un prompt |
| `--language` | **Ignorata.** Il modello OCR è unico e copre gli alfabeti latini; l'opzione resta solo per non rompere gli script che la passano |

### Cosa viene anonimizzato

Di serie la redazione è **accesa**. Le opzioni qui sotto la spostano, non la
accendono.

| opzione | cosa fa |
|---------|---------|
| `--no-privacy` | Spegne tutto. Il documento esce come è entrato |
| `--scrub-amounts` | Toglie anche gli importi in euro. Spento di serie: in una fattura le cifre di solito servono |
| `--scrub-dates` | Toglie le date **accanto a un contesto di nascita** (`nato il`, `data di nascita`, `born`, `DOB`). Spento di serie |
| `--name-guess` | Accende l'euristica «due parole maiuscole che non sono parole italiane». Spenta di serie, e conviene lasciarla spenta: misurata, porta il richiamo da 89% a 91% e i falsi positivi da 3 257 a 27 637 |
| `--no-name-guess` | Non fa niente. Accettata perché è finita in script e appunti di chi la usava per difendersi da quella stessa euristica, che oggi è già spenta |
| `--no-pack-it` | Spegne i riconoscitori italiani: codice fiscale, P.IVA, BBAN, vie, nomi |
| `--no-pack-en` | Spegne quelli anglosassoni: SSN, NINO, NHS number, passaporti |
| `--sempre TERMINE` | Nascondi sempre questo termine. **Ripetibile.** I nomi che ricorrono in ogni tua pratica e che nessuna regola generale può indovinare |
| `--mai TERMINE` | Non farlo toccare da **nessun** riconoscitore. **Ripetibile.** Vince su `--sempre` |

Il nucleo — IBAN, carte di pagamento, email, telefoni, chiavi — non si spegne
per pacchetto: vale in ogni Paese.

```bash
python -m mr_rao.cli convert atto.pdf \
  --sempre "Rossi & Partners" --sempre "Progetto Sirio" \
  --mai "Studio Rao S.r.l."
```

> **Attenzione a dove finiscono i termini.** La riga di comando resta nella
> cronologia della shell. Un elenco di clienti scritto lì è esattamente il
> genere di dato che questo programma esiste per non far girare: dall'interfaccia
> le due liste restano sul disco di chi converte, e non passano da nessuna
> cronologia.

---

## `watch` — osserva una cartella e converti da solo

```bash
python -m mr_rao.cli watch "Da convertire" "Convertiti" --move-done
```

| opzione | cosa fa |
|---------|---------|
| `--interval` | Secondi fra un controllo e l'altro (2.0 di serie) |
| `--move-done` | Sposta l'originale quando ha finito, invece di lasciarlo dov'è |

Accetta anche `--engine`, `--language`, `--force-ocr`, `--no-tables`,
`--no-frontmatter`, `--clean`, `--no-privacy`, `--scrub-amounts`,
`--scrub-dates`, `--no-name-guess`, con lo stesso significato di `convert`.

Le due liste `--sempre` e `--mai` **non** ci sono: una cartella osservata gira
per ore senza nessuno davanti, e i termini si scrivono dall'interfaccia.

---

## `health` — le dipendenze ci sono?

```bash
python -m mr_rao.cli health
```

Dice quali librerie opzionali sono installate e quali no. Non converte niente.

---

## Globali

| opzione | cosa fa |
|---------|---------|
| `--version` | Nome e versione |
| `--help` | Vale su ogni comando: `... convert --help` |
