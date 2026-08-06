# Contribuire a Mr. Rao

Grazie per l'interesse. Prima una cosa da sapere, così non perdi tempo.

## La licenza

Mr. Rao è software libero sotto **GNU AGPL-3.0** ([LICENSE](LICENSE)).
Aprendo una pull request accetti che il tuo contributo venga distribuito sotto
la stessa licenza.

In pratica: usalo, modificalo, ridistribuiscilo. L'unico obbligo serio scatta
se lo offri ad altri via rete — in quel caso devi rendere disponibile il
sorgente della tua versione (articolo 13).

## Cosa è utile

Guarda il [backlog](docs/BACKLOG.md): è aggiornato e onesto su cosa manca.
In particolare sono benvenuti:

- **Riconoscitori per altri Paesi.** L'architettura in `mr_rao/privacy.py` è
  già a pattern + validatore: aggiungere NIF spagnoli o SIREN francesi è
  soprattutto lavoro di regole, non di impianto.
- **Falsi positivi e falsi negativi dell'anonimizzazione.** Se un dato personale
  ti è sfuggito, o un codice prodotto è stato scambiato per un IBAN, apri una
  issue con un esempio **inventato** (mai dati reali).
- **Anteprima Markdown più fedele** (liste annidate, tabelle) — P1.4.
- **Test.** Ce ne sono 161 e non bastano mai.

## Cosa serve prima di una PR

```bash
scripts\quality_gate.bat
```

Deve passare: compilazione, dipendenze, licenze allineate, test.

Due regole che il progetto si è dato dopo averle pagate care:

1. **Un test di regressione va verificato fallire sul codice di prima.**
   Un test che passa anche col bug non dimostra nulla. Se correggi qualcosa,
   togli la correzione, guarda il test diventare rosso, rimettila.

2. **Le licenze non si scrivono a mano.** Se aggiungi una dipendenza, rigenera
   l'elenco:
   ```bash
   venv\Scripts\python scripts\gen_third_party.py
   ```
   E se la dipendenza è copyleft (LGPL, MPL, GPL), aggiungi anche testo e
   notice in `licenses/`, come è stato fatto per pystray e python-stdnum.
   Il gate controlla l'allineamento, non la completezza degli adempimenti:
   quella resta responsabilità di chi aggiunge.

## Stile

- Codice e commenti in inglese; testi rivolti all'utente in italiano.
- I commenti spiegano **perché**, non cosa: il cosa si legge dal codice.
- Niente dipendenze nuove senza una ragione forte. Ogni pacchetto in più è
  peso nel portable e una licenza in più da rispettare.

## Segnalare un bug

Servono tre righe: cosa hai fatto, cosa ti aspettavi, cosa è successo.
Con formato del file e versione (la trovi nel piè di pagina o con
`python -m mr_rao.cli --version`).

**Non allegare mai documenti reali.** Se serve un campione, costruiscine uno
finto: il progetto esiste proprio per non far girare i documenti veri.
