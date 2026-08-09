# Mr. Rao Portable — installazione senza Python

## Cosa contiene il pacchetto

La cartella `MrRao-Portable` (generata su un PC di build) include:

- `app/MrRao.exe` + tutte le librerie (Flask, MarkItDown, RapidOCR, ONNX, BeautifulSoup, …)
- template e static (logo, favicon, UI)
- script di installazione / disinstallazione

**Sul PC destinazione non servono:** Python, pip, git, venv, connessione per scaricare pacchetti.

## Come generare il pacchetto (PC sviluppatore)

```bat
scripts\build_portable.bat
```

Output: `dist\MrRao-Portable\` (~330 MB) più i due archivi in `dist\`:
`MrRao-Portable-<versione>.zip` e `MrRao-Portable.zip` (~165 MB l'uno).
**Vanno allegati entrambi alla release**: GitHub serve
`/releases/latest/download/NOME` solo se il nome non cambia fra le versioni,
ed è quel percorso che alimenta i link di scaricamento diretto nei README.
Niente di tutto questo è in git.

Verifica rapida dopo la build:

```bat
dist\MrRao-Portable\app\MrRao.exe health
dist\MrRao-Portable\app\MrRao.exe convert file.txt -o out.md --no-privacy
```

Copia l'intera cartella su USB, share di rete o archivio ZIP.

## Installazione (PC utente)

1. Apri la cartella `MrRao-Portable`
2. Esegui **`Installa Mr Rao.bat`**
3. Avvia da Desktop **Mr. Rao** (icona personalizzata)

L’installer:

- copia i file in `%LOCALAPPDATA%\MrRao`
- crea collegamento Desktop + menu Start con `mr-rao.ico`
- aggiunge **Invia a → Mr. Rao**
- aggiunge voce menu contestuale **Apri con Mr. Rao**

## Uso

- Doppio clic sull’icona → server locale + browser + tray
- Trascina file sull’exe / “Apri con” → conversione CLI in Markdown
- UI: hotfolder, preset, diff privacy, confronto 2 file, allegati EML

## Disinstallazione

Esegui `Disinstalla Mr Rao.bat` (o lo script nella cartella di install).

## Note

- Dimensione pacchetto: grande (ONNX/OCR), tipicamente centinaia di MB — è il prezzo dell’offline completo
- Antivirus a volte ispezionano exe PyInstaller: firma/white-list aziendale se serve
- La build va rifatta quando aggiorni dipendenze o codice

## Verificare il pacchetto

Due controlli diversi, che rispondono a due domande diverse. Conviene sapere
quale risponde a cosa, perché è facile credere che una firma dimostri più di
quanto dimostri.

### «È arrivato intero?» — SHA-256

Ogni release allega `SHA256SUMS.txt`.

```bash
sha256sum -c SHA256SUMS.txt
```

Su Windows: `certutil -hashfile MrRao-Portable.zip SHA256` e confronta a occhio.

Serve contro uno scaricamento troncato o un mirror qualunque. **Non** serve
contro chi controlla la pagina delle release: chi può sostituire lo zip può
sostituire anche il file delle impronte.

### «Viene davvero da qui?» — Sigstore

Il pacchetto è firmato dal workflow che lo costruisce, con le attestazioni di
provenienza di GitHub, che sono [Sigstore](https://www.sigstore.dev/) sotto il
cofano.

```bash
gh attestation verify MrRao-Portable.zip --repo AntonioRao/mr-rao
```

La risposta dice **da quale repository, da quale commit e da quale esecuzione**
è uscito quel file. È più forte di una firma GPG per una ragione precisa: con
GPG chi verifica deve procurarsi la chiave pubblica *e sapere che è la tua* —
e se qualcuno sostituisce zip, impronte e chiave, la verifica torna verde lo
stesso. Qui l'identità è quella di GitHub Actions, non si fabbrica, e la firma
è registrata nel registro pubblico Rekor, che è append-only: una firma
pubblicata non si può ritirare fingendo che non sia mai esistita.

Non c'è nessuna chiave privata da custodire: il runner ne ottiene una
usa-e-getta al momento della firma e la butta subito dopo.

### Quello che nessuno dei due fa

**Non tolgono l'avviso di SmartScreen.** Quello richiede una firma
Authenticode, cioè un certificato di code signing a pagamento. Windows
continuerà a dire che l'editore è sconosciuto: è una scelta di costo,
dichiarata, non una dimenticanza.
