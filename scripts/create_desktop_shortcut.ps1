# Create Desktop shortcut "Mr. Rao.lnk" with custom ICO
param(
    [string]$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
)

$ErrorActionPreference = "Stop"
$Desktop = [Environment]::GetFolderPath("Desktop")
$Ico = Join-Path $ProjectRoot "static\img\mr-rao.ico"
$Target = Join-Path $ProjectRoot "Avvia Mr Rao.bat"
$ShortcutPath = Join-Path $Desktop "Mr. Rao.lnk"

if (-not (Test-Path $Target)) {
    Write-Error "Launcher not found: $Target"
    exit 1
}
if (-not (Test-Path $Ico)) {
    Write-Host "ICO missing, generating icons..."
    $py = Join-Path $ProjectRoot "venv\Scripts\python.exe"
    if (-not (Test-Path $py)) { $py = "python" }
    & $py (Join-Path $ProjectRoot "scripts\generate_icons.py")
}

$Wsh = New-Object -ComObject WScript.Shell
$Sc = $Wsh.CreateShortcut($ShortcutPath)
$Sc.TargetPath = $Target
$Sc.WorkingDirectory = $ProjectRoot
$Sc.WindowStyle = 1
$Sc.Description = "Mr. Rao - Documenti in Markdown (offline)"
if (Test-Path $Ico) {
    $Sc.IconLocation = "$Ico,0"
}
$Sc.Save()

# Remove old plain .bat launcher on Desktop if present
$OldBat = Join-Path $Desktop "Mr Rao.bat"
if (Test-Path $OldBat) {
    Remove-Item $OldBat -Force -ErrorAction SilentlyContinue
}

Write-Host "Shortcut created: $ShortcutPath"
if (Test-Path $Ico) { Write-Host "Icon: $Ico" }
exit 0
