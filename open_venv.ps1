$venvPath = Join-Path $PSScriptRoot "venv"

if (!(Test-Path $venvPath)) {
    Read-Host "Sorry, you do not seem to have a venv!"
    exit 1
}

Write-Host "Type 'deactivate' to return."

& "$venvPath\Scripts\Activate.ps1"
