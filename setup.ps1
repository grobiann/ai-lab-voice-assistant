
# setup.ps1 — One-shot setup for ai-lab-voice-assistant on Windows
# Usage:  powershell -ExecutionPolicy Bypass -File setup.ps1

# Force UTF-8 console output so Korean/emoji display correctly
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding            = [System.Text.Encoding]::UTF8

$ErrorActionPreference = 'Stop'

function Print-Info   ($msg) { Write-Host "  $msg"       -ForegroundColor Cyan   }
function Print-Ok     ($msg) { Write-Host "  [OK] $msg"  -ForegroundColor Green  }
function Print-Warn   ($msg) { Write-Host "  [!]  $msg"  -ForegroundColor Yellow }
function Print-Error  ($msg) { Write-Host "  [X]  $msg"  -ForegroundColor Red    }
function Print-Header ($msg) { Write-Host "`n$msg"       -ForegroundColor White  }

Print-Header "=== Claude Voice Activation Trigger --- Windows Setup ==="

# ----------------------------------------------------------------------------
# 1. Python check
# ----------------------------------------------------------------------------
Print-Header "[1/4] Python..."
try {
    $pyver = & python --version 2>&1
    Print-Ok "Python: $pyver"
} catch {
    Print-Error "Python not found."
    Print-Error "Install from https://www.python.org/downloads/ then re-run."
    exit 1
}

# ----------------------------------------------------------------------------
# 2. Python packages
# ----------------------------------------------------------------------------
Print-Header "[2/4] Python packages..."

# vosk depends on 'srt' which may require older setuptools to build
Print-Info "Installing compatible setuptools..."
& python -m pip install --quiet "setuptools<67" 2>$null
& python -m pip install --quiet srt 2>$null

Print-Info "Installing vosk + sounddevice..."
& python -m pip install --quiet -r requirements.txt

Print-Info "Installing Windows automation packages (pygetwindow, pyperclip, pyautogui)..."
& python -m pip install --quiet pygetwindow pyperclip pyautogui

Print-Ok "Python packages installed"

# ----------------------------------------------------------------------------
# 3. Node.js packages
# ----------------------------------------------------------------------------
Print-Header "[3/4] Node.js packages..."
try {
    & npm install --silent
    Print-Ok "Node.js packages installed"
} catch {
    Print-Error "npm install failed. Make sure Node.js is installed."
    Print-Error "Download from https://nodejs.org/"
    exit 1
}

# ----------------------------------------------------------------------------
# 4. Vosk Korean model (~82 MB)
# ----------------------------------------------------------------------------
Print-Header "[4/4] Vosk Korean model..."
if (-not (Test-Path "models\vosk-model-small-ko-0.22")) {
    Print-Info "Downloading model (~82 MB)..."
    & node scripts/download-model.js
} else {
    Print-Ok "Model already exists"
}

# ----------------------------------------------------------------------------
# .env
# ----------------------------------------------------------------------------
if (-not (Test-Path ".env")) {
    Copy-Item .env.example .env
    Print-Warn ".env created. Edit it if needed."
}

Write-Host ""
Write-Host "Setup complete!" -ForegroundColor Green
Write-Host ""
Write-Host "Run with:  npm start" -ForegroundColor Cyan
Write-Host ""
