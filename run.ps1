$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectRoot

$venvPython = Join-Path $projectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    Write-Host "Creating the Dissent Garden Python environment..."
    python -m venv (Join-Path $projectRoot ".venv")
}

& $venvPython -c "import fastapi, openai, pydantic, uvicorn" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Installing Dissent Garden dependencies..."
    & $venvPython -m pip install -r (Join-Path $projectRoot "requirements.txt")
    if ($LASTEXITCODE -ne 0) {
        throw "Dependency installation failed."
    }
}

if ([string]::IsNullOrWhiteSpace($env:OPENAI_API_KEY)) {
    Write-Host "Dissent Garden needs an OpenAI API key for live deliberation."
    Write-Host "Copy the API key to your clipboard, return here, and press Enter."
    Write-Host "The launcher validates the key, transfers it only to this process, then clears the clipboard."
    Read-Host -Prompt "Press Enter after copying the key" | Out-Null
    try {
        $plainKey = (Get-Clipboard -Raw).Trim()
        if (
            [string]::IsNullOrWhiteSpace($plainKey) -or
            -not $plainKey.StartsWith("sk-") -or
            $plainKey.Length -lt 20 -or
            $plainKey -match "\s"
        ) {
            throw "The clipboard does not contain a complete OpenAI API key. Copy the full key and run the launcher again."
        }
        $env:OPENAI_API_KEY = $plainKey
        Write-Host "API key accepted. Clipboard cleared; starting Dissent Garden..."
    }
    finally {
        Set-Clipboard -Value "Clipboard cleared by Dissent Garden."
        Remove-Variable plainKey -ErrorAction SilentlyContinue
    }
}

& $venvPython -m uvicorn app.main:app --host 127.0.0.1 --port 8765
