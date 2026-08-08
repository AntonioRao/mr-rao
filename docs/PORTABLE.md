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
