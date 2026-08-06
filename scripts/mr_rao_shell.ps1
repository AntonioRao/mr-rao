# Collegamenti e menu contestuale di Mr. Rao.
#
# Un file solo per installazione e disinstallazione: l'elenco delle
# estensioni deve stare in un posto solo. Quando viveva in due file
# distinti le due liste sono andate fuori sincrono e la disinstallazione
# lasciava voci di menu che puntavano a un eseguibile non piu' esistente.
#
# ASCII puro di proposito: un .ps1 con caratteri accentati e senza BOM non
# viene interpretato correttamente da Windows PowerShell 5.1.

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$InstallDir,
    [switch]$Remove
)

$ErrorActionPreference = 'Continue'

$Estensioni = @(
    '.pdf', '.eml', '.docx', '.doc', '.png', '.jpg', '.jpeg',
    '.xlsx', '.pptx', '.txt'
)

$Exe = Join-Path $InstallDir 'app\MrRao.exe'

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
    # L'icona sta accanto all'installazione, ma il pacchetto la porta anche
    # dentro le risorse dell'applicazione: se la prima copia manca si usa
    # la seconda, e se mancano entrambe si usa l'icona dell'eseguibile.
    # Un collegamento senza icona resta un collegamento valido: non deve
    # essere questo a far fallire l'installazione.
    $candidati = @(
        (Join-Path $InstallDir 'mr-rao.ico'),
        (Join-Path $InstallDir 'app\_internal\static\img\mr-rao.ico'),
        (Join-Path $InstallDir 'app\static\img\mr-rao.ico')
    )
    foreach ($c in $candidati) {
        if (Test-Path $c) { return $c }
    }
    Write-Host '  icona: nessun .ico trovato, uso quella dell eseguibile'
    return $Exe
}

function Install-Shell {
    if (-not (Test-Path $Exe)) {
        Write-Host "ERRORE: manca $Exe"
        exit 1
    }
    $ico = Resolve-Icon
    Write-Host "  icona:  $ico"

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

    $comando = '"{0}" "%1"' -f $Exe
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
