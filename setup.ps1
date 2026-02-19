# setup.ps1 — One-shot setup for ai-lab-voice-assistant on Windows
# Usage (in PowerShell):  .\setup.ps1
# If execution policy blocks it:  powershell -ExecutionPolicy Bypass -File setup.ps1

$ErrorActionPreference = 'Stop'

function Info  ($msg) { Write-Host "  $msg" -ForegroundColor Cyan }
function Ok    ($msg) { Write-Host "  ✓ $msg" -ForegroundColor Green }
function Warn  ($msg) { Write-Host "  ! $msg" -ForegroundColor Yellow }
function Header($msg) { Write-Host "`n$msg" -ForegroundColor White }

Header "=== Claude 음성 활성화 트리거 — Windows 설치 ==="

# ── 1. Python check ───────────────────────────────────────────────────────────
Header "[1/4] Python 확인 중..."
try {
    $pyver = & python --version 2>&1
    Ok "Python: $pyver"
} catch {
    Write-Host "  ✗ Python이 설치되어 있지 않습니다." -ForegroundColor Red
    Write-Host "    https://www.python.org/downloads/ 에서 설치 후 다시 실행하세요." -ForegroundColor Red
    exit 1
}

# ── 2. Python packages ────────────────────────────────────────────────────────
Header "[2/4] Python 패키지 설치 중..."

# vosk depends on 'srt' which can require older setuptools
Info "setuptools 호환 버전 설치 중..."
& python -m pip install --quiet "setuptools<67" 2>$null
& python -m pip install --quiet srt 2>$null

Info "vosk, sounddevice 설치 중..."
& python -m pip install --quiet -r requirements.txt

Info "Windows 자동화 패키지 설치 중 (pygetwindow, pyperclip, pyautogui)..."
& python -m pip install --quiet pygetwindow pyperclip pyautogui

Ok "Python 패키지 설치 완료"

# ── 3. Node.js packages ───────────────────────────────────────────────────────
Header "[3/4] Node.js 패키지 설치 중..."
try {
    & npm install --silent
    Ok "Node.js 패키지 설치 완료"
} catch {
    Write-Host "  ✗ npm install 실패. Node.js가 설치되어 있는지 확인하세요." -ForegroundColor Red
    Write-Host "    https://nodejs.org/ 에서 설치 후 다시 실행하세요." -ForegroundColor Red
    exit 1
}

# ── 4. Vosk Korean model ──────────────────────────────────────────────────────
Header "[4/4] Vosk 한국어 모델 확인 중..."
if (-not (Test-Path "models\vosk-model-small-ko-0.22")) {
    Info "모델 다운로드 중 (~82 MB)..."
    & node scripts/download-model.js
} else {
    Ok "모델 이미 존재함"
}

# ── .env ──────────────────────────────────────────────────────────────────────
if (-not (Test-Path ".env")) {
    Copy-Item .env.example .env
    Warn ".env 파일 생성됨. 필요시 수정하세요."
}

Write-Host ""
Write-Host "✓ 설치 완료!" -ForegroundColor Green
Write-Host ""
Write-Host "실행 방법:" -ForegroundColor White
Write-Host "  npm start" -ForegroundColor Cyan
Write-Host ""
