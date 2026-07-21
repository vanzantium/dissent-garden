param(
    [string]$ProjectRoot = (Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)),
    [int]$Rate = 2
)

$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.Speech

$narrationPath = Join-Path $ProjectRoot "video\narration.json"
$audioDir = Join-Path $ProjectRoot "video\work\audio"
New-Item -ItemType Directory -Force -Path $audioDir | Out-Null
$sections = Get-Content -Raw -Encoding utf8 -LiteralPath $narrationPath | ConvertFrom-Json

foreach ($section in $sections) {
    $outputPath = Join-Path $audioDir ("{0}.wav" -f $section.id)
    $speaker = New-Object System.Speech.Synthesis.SpeechSynthesizer
    try {
        $speaker.SelectVoice("Microsoft Zira Desktop")
        $speaker.Rate = $Rate
        $speaker.Volume = 100
        $speaker.SetOutputToWaveFile($outputPath)
        $speaker.Speak([string]$section.narration)
    }
    finally {
        $speaker.Dispose()
    }
}

Write-Output "Narration written to $audioDir"
