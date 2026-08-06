param(
    [Parameter(Mandatory = $true)][string]$ExePath,
    [string]$IconPath = ""
)

$ErrorActionPreference = "Stop"
if (-not (Test-Path $ExePath)) {
    Write-Error "Exe not found: $ExePath"
    exit 1
}
if (-not $IconPath -or -not (Test-Path $IconPath)) {
    $IconPath = $ExePath
}

# SendTo
$sendTo = [Environment]::GetFolderPath("SendTo")
$w = New-Object -ComObject WScript.Shell
$sc = $w.CreateShortcut((Join-Path $sendTo "Mr. Rao.lnk"))
$sc.TargetPath = $ExePath
$sc.WorkingDirectory = Split-Path $ExePath
$sc.IconLocation = "$IconPath,0"
$sc.Save()

# Right-click "Apri con Mr. Rao" for all files + common types
function Set-ShellVerb($keyPath) {
    New-Item -Path $keyPath -Force | Out-Null
    New-ItemProperty -Path $keyPath -Name "(Default)" -Value "Apri con Mr. Rao" -Force | Out-Null
    New-ItemProperty -Path $keyPath -Name "Icon" -Value $IconPath -Force | Out-Null
    $cmd = Join-Path $keyPath "command"
    New-Item -Path $cmd -Force | Out-Null
    # %1 = selected file; MrRao.exe routes non-flag args to convert CLI
    New-ItemProperty -Path $cmd -Name "(Default)" -Value "`"$ExePath`" `"%1`"" -Force | Out-Null
}

Set-ShellVerb "HKCU:\Software\Classes\*\shell\MrRao"
foreach ($ext in @(".pdf", ".eml", ".docx", ".doc", ".png", ".jpg", ".jpeg", ".xlsx", ".pptx", ".txt")) {
    Set-ShellVerb "HKCU:\Software\Classes\SystemFileAssociations\$ext\shell\MrRao"
}

Write-Host "Shell integration OK (SendTo + context menu)"
exit 0
