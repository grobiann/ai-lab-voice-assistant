#!/usr/bin/env bash
# Voice Typer 설치 스크립트 — Linux / macOS

set -e

# ── 색상 정의 ───────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; BOLD='\033[1m'; NC='\033[0m'

step()  { echo -e "\n${BLUE}▶${NC} ${BOLD}$1${NC}"; }
ok()    { echo -e "  ${GREEN}✓${NC} $1"; }
warn()  { echo -e "  ${YELLOW}!${NC} $1"; }
err()   { echo -e "  ${RED}✗${NC} $1" >&2; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo ""
echo -e "${BOLD}=================================================="
echo -e "  Voice Typer 설치"
echo -e "==================================================${NC}"

# ── 1. Python 확인 ──────────────────────────────────────────────────────────────
step "Python 버전 확인"
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
    err "Python 3.8 이상이 설치되어 있지 않습니다."
    echo "  → 설치: https://www.python.org/downloads/"
    exit 1
fi
ok "$($PYTHON_CMD --version)"

# ── 2. 가상환경 ─────────────────────────────────────────────────────────────────
step "가상환경 설정"
VENV="$SCRIPT_DIR/.venv"
if [ ! -d "$VENV" ]; then
    "$PYTHON_CMD" -m venv "$VENV"
    ok "가상환경 생성됨: .venv/"
else
    ok "기존 가상환경 재사용"
fi

# ── 3. 패키지 설치 ──────────────────────────────────────────────────────────────
step "패키지 설치 (처음 실행 시 수 분이 걸릴 수 있습니다)"
"$VENV/bin/pip" install --upgrade pip --quiet
"$VENV/bin/pip" install -r "$SCRIPT_DIR/requirements.txt"
ok "패키지 설치 완료"

# ── 4. .env 파일 ────────────────────────────────────────────────────────────────
step "환경 파일 설정"
if [ ! -f "$SCRIPT_DIR/.env" ]; then
    cp "$SCRIPT_DIR/.env.example" "$SCRIPT_DIR/.env"
    ok ".env 파일 생성됨"
    warn "tier3 / cloud 모드 사용 시 .env 파일에 API 키를 입력하세요"
else
    ok ".env 파일 유지 (기존 설정 보존)"
fi

# ── 5. run.sh 실행 권한 ─────────────────────────────────────────────────────────
chmod +x "$SCRIPT_DIR/run.sh"

# ── 6. Ollama 설치 확인 (tier3 ollama 모드용) ───────────────────────────────────
step "Ollama 확인 (tier3 LLM 교정용)"
if command -v ollama &>/dev/null; then
    ok "Ollama 설치됨: $(ollama --version 2>/dev/null || echo '버전 확인 불가')"
    # 권장 모델 존재 여부 확인
    if ollama list 2>/dev/null | grep -q "exaone3.5"; then
        ok "EXAONE 3.5 모델 준비됨"
    else
        warn "EXAONE 3.5 모델 미설치 — tier3(ollama) 사용 시 필요:"
        echo "     ollama pull exaone3.5:7.8b   (권장, 한국어 특화, ~5GB)"
        echo "     ollama pull exaone3.5:2.4b   (경량, ~2GB)"
    fi
else
    warn "Ollama 미설치 — tier3 (LLM_BACKEND=\"ollama\") 사용 시 필요"
    echo "     설치: https://ollama.com/download"
    echo "     설치 후 모델 다운로드:"
    echo "       ollama pull exaone3.5:7.8b   (권장, 한국어 특화, ~5GB)"
    echo "       ollama pull exaone3.5:2.4b   (경량, ~2GB)"
    echo "     tier3 없이 tier2 기본 사용 가능 (API 키 불필요)"
fi
APPS_DIR="$HOME/.local/share/applications"
if [ -d "$APPS_DIR" ]; then
    step "데스크탑 바로가기 설치"
    cat > "$APPS_DIR/voice-typer.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Voice Typer
GenericName=음성 딕테이션
Comment=Ctrl+Space 로 음성을 텍스트로 변환합니다
Exec=$SCRIPT_DIR/run.sh
Terminal=false
Categories=Utility;Accessibility;
Keywords=voice;speech;stt;whisper;dictation;음성;받아쓰기;
StartupNotify=true
EOF
    ok "앱 메뉴에 'Voice Typer' 등록됨"
fi

# ── 완료 메시지 ─────────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}=================================================="
echo -e "  설치 완료!"
echo ""
echo -e "  실행 방법:"
echo -e "    터미널    :  ./run.sh"
echo -e "    앱 메뉴   :  'Voice Typer' 검색 (Linux)"
echo ""
echo -e "  STT 단계 변경 → config.py 의 STT_MODE:"
echo -e "    tier1 (빠름)  tier2 (균형, 기본)  tier3 (최고정밀+LLM 교정)"
echo ""
echo -e "  tier3 LLM 백엔드 → config.py 의 LLM_BACKEND:"
echo -e "    ollama (무료, 로컬)  groq (무료 API)  claude (유료)"
echo -e "=================================================="
echo -e "${NC}"
