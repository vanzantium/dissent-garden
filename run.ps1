$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectRoot

if ([string]::IsNullOrWhiteSpace($env:OPENAI_API_KEY)) {
    Write-Host "Dissent Garden needs an OpenAI API key for live deliberation."
    Write-Host "Paste the key at the hidden prompt and press Enter. It is kept only for this process."
    $secureKey = Read-Host -Prompt "OpenAI API key" -AsSecureString
    $keyPointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureKey)
    try {
        $plainKey = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($keyPointer)
        if ([string]::IsNullOrWhiteSpace($plainKey)) {
            throw "No API key was entered."
        }
        $env:OPENAI_API_KEY = $plainKey.Trim()
    }
    finally {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($keyPointer)
        Remove-Variable secureKey, plainKey -ErrorAction SilentlyContinue
    }
}

python -m uvicorn app.main:app --host 127.0.0.1 --port 8765
