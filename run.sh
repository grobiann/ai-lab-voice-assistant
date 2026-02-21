#!/usr/bin/env bash
# Voice Typer 런처 (자동 설치 포함) — Linux / macOS
#
# 처음 실행: 필요한 패키지를 자동으로 설치합니다.
# 이후 실행: 바로 앱이 시작됩니다.
#
# 옵션:
#   ./run.sh          — 앱 실행
#   ./run.sh --log    — 로그를 터미널에 출력 (디버깅용)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$SCRIPT_DIR/.venv"
LOG_FILE="$SCRIPT_DIR/voice-typer.log"

# ── 최초 실행: 가상환경이 없으면 자동 설치 ────────────────────────────────────
if [ ! -f "$VENV/bin/python" ]; then
    echo ""
    echo "=================================================="
    echo "  Voice Typer  [First Run Setup]"
    echo "=================================================="
    echo ""

    # Python 3.8+ 탐색
    PYTHON_CMD=""
    for cmd in python3.12 python3.11 python3.10 python3.9 python3 python; do
        if command -v "$cmd" &>/dev/null 2>&1; then
            OK=$("$cmd" -c "import sys; print('ok' if sys.version_info >= (3,8) else 'no')" 2>/dev/null || echo "no")
            if [ "$OK" = "ok" ]; then
                PYTHON_CMD="$cmd"
                break
            fi
        fi
    done

    if [ -z "$PYTHON_CMD" ]; then
        echo "[ERROR] Python 3.8 or higher not found."
        echo "  Install: https://www.python.org/downloads/"
        exit 1
    fi
    echo "  [OK] $($PYTHON_CMD --version)"

    # 가상환경 생성
    echo "  [1/2] Creating virtual environment..."
    "$PYTHON_CMD" -m venv "$VENV" || { echo "[ERROR] Failed to create venv"; exit 1; }

    # 패키지 설치
    echo "  [2/2] Installing packages... (may take 1-3 min on first run)"
    "$VENV/bin/pip" install --upgrade pip --quiet
    "$VENV/bin/pip" install -r "$SCRIPT_DIR/requirements.txt" \
        || { echo "[ERROR] Package installation failed"; exit 1; }

    # run.sh 실행 권한 확보
    chmod +x "$SCRIPT_DIR/run.sh"

    echo ""
    echo "  Setup complete!"
    echo "=================================================="
    echo ""
fi

# .env 없으면 example 에서 자동 복사
if [ ! -f "$SCRIPT_DIR/.env" ] && [ -f "$SCRIPT_DIR/.env.example" ]; then
    cp "$SCRIPT_DIR/.env.example" "$SCRIPT_DIR/.env"
fi

# ── 앱 실행 ───────────────────────────────────────────────────────────────────
# TTY: 터미널 실행 → stdout 출력 / GUI 실행 → 로그 파일
if [ -t 1 ] || [ "${1:-}" = "--log" ]; then
    exec "$VENV/bin/python" "$SCRIPT_DIR/main.py"
else
    exec "$VENV/bin/python" "$SCRIPT_DIR/main.py" >> "$LOG_FILE" 2>&1
fi
