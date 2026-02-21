#!/usr/bin/env bash
# Voice Typer 실행 스크립트 — Linux / macOS
#
# 사용법:
#   ./run.sh          — 앱 실행 (처음 실행 시 자동 설치)
#   ./run.sh --log    — 로그를 터미널에 출력하며 실행 (디버깅용)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$SCRIPT_DIR/.venv"
LOG_FILE="$SCRIPT_DIR/voice-typer.log"

# ── 가상환경 미설치 시 자동 설치 ──────────────────────────────────────────────
if [ ! -f "$VENV/bin/python" ]; then
    echo "처음 실행입니다. 설치를 진행합니다..."
    bash "$SCRIPT_DIR/install.sh" || exit 1
fi

# ── TTY 감지: 터미널에서 실행 시 stdout 출력, 앱 메뉴에서 실행 시 로그 파일 ──
if [ -t 1 ] || [ "${1}" = "--log" ]; then
    # 터미널 실행 — stdout/stderr 그대로 출력
    exec "$VENV/bin/python" "$SCRIPT_DIR/main.py"
else
    # 데스크탑(GUI) 실행 — 로그 파일에 기록
    exec "$VENV/bin/python" "$SCRIPT_DIR/main.py" \
        >> "$LOG_FILE" 2>&1
fi
