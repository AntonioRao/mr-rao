# Mr. Rao -- Copyright (c) 2026 Antonio Andrea Rao.
# SPDX-License-Identifier: AGPL-3.0-or-later
# Software libero: puoi ridistribuirlo e/o modificarlo secondo i termini della
# GNU Affero General Public License pubblicata dalla Free Software Foundation,
# versione 3 o (a tua scelta) successiva. Vedi LICENSE nella radice del repository.
# Collegamenti e menu contestuale di Mr. Rao.
#
# Un file solo per installazione e disinstallazione: l'elenco delle
# estensioni deve stare in un posto solo. Quando viveva in due file
# distinti le due liste sono andate fuori sincrono e la disinstallazione
# lasciava voci di menu che puntavano a un eseguibile non piu' esistente.
#
# ASCII puro di proposito: un .ps1 con caratteri accentati e senza BOM non
# viene interpretato correttamente da Windows PowerShell 5.1.
#
# Serve due installazioni diverse, e per questo i percorsi sono parametri
# invece che dedotti:
#
#   pacchetto portable   ->  <InstallDir>\app\MrRao.exe, che porta l'icona
#                            dentro di se'
#   installazione da     ->  "Avvia Mr Rao.bat" per il collegamento,
#   sorgente (Python)        "open_with_mr_rao.bat" per il menu, e il .ico
#                            del repository per l'icona
#
# Prima l'installazione da sorgente aveva due script propri, che facevano
# la stessa cosa in modo leggermente diverso. Due strade per lo stesso
# risultato vuol dire che correggendone una l'altra resta indietro in
# silenzio -- ed e' il difetto che questo file era nato per chiudere.

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$InstallDir,
    # Cosa lancia il collegamento. Vuoto = layout del pacchetto portable.
    [string]$Avvio,
    # Cosa lancia il menu contestuale, che riceve il file come argomento.
    # Vuoto = lo stesso di -Avvio (l'eseguibile accetta gia' un percorso).
    [string]$ApriCon,
    # Icona. Vuoto = quella dentro l'eseguibile.
    [string]$Icona,
    # Stampa cosa farebbe e si ferma: niente registro, niente collegamenti.
    [switch]$Prova,
    [switch]$Remove
)

$ErrorActionPreference = 'Continue'

$Estensioni = @(
    '.pdf', '.eml', '.docx', '.doc', '.png', '.jpg', '.jpeg',
    '.xlsx', '.pptx', '.txt'
)

if ($Avvio) { $Exe = $Avvio } else { $Exe = Join-Path $InstallDir 'app\MrRao.exe' }
if ($ApriCon) { $Bersaglio = $ApriCon } else { $Bersaglio = $Exe }

function Get-DesktopPath {
    # Con OneDrive attivo il Desktop puo' essere spostato (Known Folder
    # Move): GetFolderPath restituisce il percorso vero, %USERPROFILE%
    # restituisce una cartella che esiste ma che l'utente non vede.
    $p = [Environment]::GetFolderPath('Desktop')
    if ($p -and (Test-Path $p)) { return $p }
    $fallback = Join-Path $env:USERPROFILE 'Desktop'
    Write-Host "  nota: Desktop non risolto, uso $fallback"
    return $fallback
}

function Get-LinkPaths {
    @(
        @{ Label = 'Desktop';    Path = (Join-Path (Get-DesktopPath) 'Mr. Rao.lnk') },
        @{ Label = 'Menu Start'; Path = (Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs\Mr. Rao.lnk') },
        @{ Label = 'Invia a';    Path = (Join-Path ([Environment]::GetFolderPath('SendTo')) 'Mr. Rao.lnk') }
    )
}

function Get-VerbKeys {
    # Percorsi relativi a HKCU, non "HKCU:\...": si passa dalle API del
    # registro invece che dal provider di PowerShell. La classe "tutti i
    # file" si chiama letteralmente "*", e per il provider quello e' un
    # jolly: enumera l'intero ramo delle classi a ogni operazione, tanto
    # da portare l'installazione a due minuti e mezzo. Le API non hanno
    # jolly, non hanno problemi di virgolette e ci mettono un istante.
    $chiavi = @('Software\Classes\*\shell\MrRao')
    foreach ($e in $Estensioni) {
        $chiavi += "Software\Classes\SystemFileAssociations\$e\shell\MrRao"
    }
    return $chiavi
}

function Resolve-Icon {
    # L'icona e' quella dentro l'eseguibile, non un .ico accanto.
    #
    # Puntare a un file separato sembrava piu' pulito ed e' costato tre
    # modi diversi di rompersi: il .lnk memorizza il percorso anche in
    # forma %USERPROFILE%\... in un blocco a parte, Windows continua a
    # disegnare l'icona che ha in cache quando il file cambia restando
    # allo stesso percorso, e un .ico che sparisce lascia un riquadro
    # bianco senza spiegazione.
    #
    # L'eseguibile l'icona ce l'ha dentro (PyInstaller la incorpora al
    # build) e c'e' sempre: se manca lui non c'e' nessun collegamento da
    # creare. Un'indirezione in meno, tre guasti in meno.
    #
    # L'installazione da sorgente non ha un eseguibile in cui guardare, e
    # deve passare un .ico esplicito: li' i tre guasti descritti sopra
    # restano possibili, ed e' il prezzo di non avere un binario.
    if ($Icona) { return $Icona }
    return $Exe
}

function Install-Shell {
    if (-not (Test-Path $Exe)) {
        Write-Host "ERRORE: manca $Exe"
        exit 1
    }
    $ico = Resolve-Icon
    # Il comando si calcola qui, sopra il ramo della prova, e la prova
    # stampa *questa* variabile. Ricostruirlo dentro il ramo sembrava piu'
    # leggibile ed era falso: si poteva cambiare il comando vero lasciando
    # la prova a dire la cosa giusta. Una prova che ricalcola invece di
    # mostrare descrive un programma che non esiste.
    #
    # P0.4 - la finestra non deve sparire quando qualcosa va storto.
    #
    # Da sorgente il bersaglio e' open_with_mr_rao.bat, che di suo aggiunge
    # gia' `convert --attendi` e chiude con `if errorlevel 1 pause`: li' non
    # serve altro, e infilarci un secondo pause vorrebbe dire due prompt in
    # fila sullo stesso errore.
    #
    # Nel pacchetto portable, invece, il bersaglio e' MrRao.exe e il comando
    # era `"MrRao.exe" "%1"`: nessun `--attendi` (app.py ricostruisce
    # `convert <file>` e basta) e nessun pause. Bastava un errore perche' la
    # finestra facesse un lampo e sparisse -- che e' esattamente il difetto
    # da chiudere.
    #
    # Due pezzi, e servono tutti e due:
    #   `convert --attendi`  fa fermare il programma quando c'e' qualcosa da
    #                        leggere (redazioni, sospetti, errori);
    #   `|| pause`           tiene la finestra anche quando il programma non
    #                        arriva a parlare: DLL mancante, estrazione del
    #                        bundle fallita, eseguibile spostato. In quei casi
    #                        Python non gira, quindi nessuna cortesia scritta
    #                        in Python puo' salvare la situazione: l'unico che
    #                        sopravvive al figlio e' chi lo ha lanciato.
    #
    # Sul quoting: con `cmd /d /c "..."` cmd toglie la coppia di virgolette
    # piu' esterna ed esegue il resto, quindi percorsi e `%1` con spazi
    # restano interi. Verificato con eseguibile e documento entrambi con
    # spazi nel nome, sia in uscita 0 (nessun pause) sia in uscita diversa da
    # zero (pause). `/d` salta gli AutoRun del registro, che altrimenti
    # possono stampare roba propria prima di noi.
    if ($ApriCon) {
        $comando = '"{0}" "%1"' -f $Bersaglio
    } else {
        $comando = 'cmd /d /c ""{0}" convert --attendi "%1" || pause"' -f $Bersaglio
    }

    Write-Host "  avvio:  $Exe"
    Write-Host "  apri:   $Bersaglio"
    Write-Host "  icona:  $ico"

    if ($Prova) {
        Write-Host ''
        Write-Host '  -Prova: nessun collegamento creato, nessuna chiave scritta.'
        Write-Host ("  avrei scritto {0} voci di menu con:" -f (Get-VerbKeys).Count)
        Write-Host ("    {0}" -f $comando)
        exit 0
    }

    $falliti = @()
    foreach ($link in Get-LinkPaths) {
        try {
            $parent = Split-Path $link.Path
            if (-not (Test-Path $parent)) {
                New-Item -ItemType Directory -Path $parent -Force | Out-Null
            }
            $shell = New-Object -ComObject WScript.Shell
            $s = $shell.CreateShortcut($link.Path)
            $s.TargetPath = $Exe
            $s.WorkingDirectory = (Split-Path $Exe)
            $s.Description = 'Mr. Rao - da documento a Markdown, offline'
            $s.IconLocation = "$ico,0"
            $s.Save()
        } catch {
            Write-Host ("  errore su {0}: {1}" -f $link.Label, $_.Exception.Message)
        }
        # Verificare che il file ci sia, non che il comando non abbia
        # protestato: Save() puo' tornare senza eccezioni e senza file.
        if (Test-Path $link.Path) {
            Write-Host ("  OK      {0}: {1}" -f $link.Label, $link.Path)
        } else {
            Write-Host ("  FALLITO {0}: {1}" -f $link.Label, $link.Path)
            $falliti += $link.Label
        }
    }

    $creati = 0
    $chiavi = Get-VerbKeys
    foreach ($k in $chiavi) {
        try {
            $key = [Microsoft.Win32.Registry]::CurrentUser.CreateSubKey($k)
            $key.SetValue('', 'Apri con Mr. Rao')
            $key.SetValue('Icon', $ico)
            $sub = $key.CreateSubKey('command')
            $sub.SetValue('', $comando)
            $sub.Close()
            $key.Close()
            $creati++
        } catch {
            Write-Host ("  errore sul menu per {0}: {1}" -f $k, $_.Exception.Message)
        }
    }
    if ($creati -eq $chiavi.Count) {
        Write-Host ("  OK      menu contestuale: {0} voci su {1}" -f $creati, $chiavi.Count)
    } else {
        # Contare e non guardare il numero e' come non contare: la prima
        # versione di questo script scriveva "0 voci su 11" e usciva con
        # successo.
        Write-Host ("  FALLITO menu contestuale: {0} voci su {1}" -f $creati, $chiavi.Count)
        $falliti += 'menu contestuale'
    }

    # Aggiornando una versione precedente il file .ico cambia contenuto
    # restando allo stesso percorso, ed e' esattamente il caso in cui
    # Windows continua a disegnare quello che ha in cache: il collegamento
    # c'e', funziona, e mostra un riquadro bianco. Capita a ogni
    # aggiornamento, non solo facendo prove.
    try {
        & "$env:SystemRoot\System32\ie4uinit.exe" -show 2>&1 | Out-Null
        Write-Host '  OK      cache delle icone aggiornata'
    } catch {
        Write-Host '  nota:   cache delle icone non aggiornata; se il'
        Write-Host '          collegamento appare bianco, premi F5 sul desktop'
    }

    if ($falliti.Count -gt 0) {
        Write-Host ''
        Write-Host ("ATTENZIONE: collegamenti non creati -> {0}" -f ($falliti -join ', '))
        Write-Host "Mr. Rao e' comunque installato e si avvia da:"
        Write-Host "  $Exe"
        exit 2
    }
    exit 0
}

function Remove-Shell {
    foreach ($link in Get-LinkPaths) {
        if (Test-Path $link.Path) {
            Remove-Item -Path $link.Path -Force -ErrorAction SilentlyContinue
        }
        if (Test-Path $link.Path) {
            Write-Host ("  RESTA   {0}: {1}" -f $link.Label, $link.Path)
        } else {
            Write-Host ("  tolto   {0}" -f $link.Label)
        }
    }

    $chiavi = Get-VerbKeys
    $rimasti = 0
    foreach ($k in $chiavi) {
        try {
            [Microsoft.Win32.Registry]::CurrentUser.DeleteSubKeyTree($k, $false)
        } catch {
            Write-Host ("  errore togliendo {0}: {1}" -f $k, $_.Exception.Message)
        }
        $ancora = [Microsoft.Win32.Registry]::CurrentUser.OpenSubKey($k)
        if ($ancora) { $ancora.Close(); $rimasti++ }
    }
    if ($rimasti -gt 0) {
        Write-Host ("  RESTANO {0} voci di menu su {1}" -f $rimasti, $chiavi.Count)
        exit 2
    }
    Write-Host ("  tolto   menu contestuale: {0} voci" -f $chiavi.Count)
    exit 0
}

if ($Remove) { Remove-Shell } else { Install-Shell }
