#!/usr/bin/env bash
# setup.sh — One-shot setup script for ai-lab-voice-assistant
# Usage: bash setup.sh

set -e

BOLD="\033[1m"
GREEN="\033[0;32m"
YELLOW="\033[0;33m"
RED="\033[0;31m"
RESET="\033[0m"

echo -e "\n${BOLD}=== Claude 음성 활성화 트리거 — 설치 ===${RESET}\n"

# ── 1. System packages ────────────────────────────────────────────────────────
echo -e "${BOLD}[1/4] 시스템 패키지 확인 중...${RESET}"

MISSING_PKGS=()
for pkg in xdotool xclip; do
  if ! command -v "$pkg" &>/dev/null; then
    MISSING_PKGS+=("$pkg")
  fi
done
# sounddevice ships bundled PortAudio binaries — no system headers needed

if [ ${#MISSING_PKGS[@]} -gt 0 ]; then
  echo -e "${YELLOW}  다음 패키지를 설치합니다: ${MISSING_PKGS[*]}${RESET}"
  sudo apt-get update -qq
  sudo apt-get install -y "${MISSING_PKGS[@]}"
else
  echo -e "${GREEN}  ✓ 시스템 패키지 OK${RESET}"
fi

# ── 2. Python packages ────────────────────────────────────────────────────────
echo -e "\n${BOLD}[2/4] Python 패키지 설치 중...${RESET}"

# vosk depends on 'srt' which requires older setuptools to build on some systems
pip3 install --quiet "setuptools<67" 2>/dev/null || true
pip3 install --quiet srt 2>/dev/null || true
pip3 install --quiet -r requirements.txt
echo -e "${GREEN}  ✓ Python 패키지 설치 완료${RESET}"

# ── 3. Node.js packages ───────────────────────────────────────────────────────
echo -e "\n${BOLD}[3/4] Node.js 패키지 설치 중...${RESET}"
npm install --silent
echo -e "${GREEN}  ✓ Node.js 패키지 설치 완료${RESET}"

# ── 4. Vosk Korean model ──────────────────────────────────────────────────────
echo -e "\n${BOLD}[4/4] Vosk 한국어 모델 확인 중...${RESET}"
if [ ! -d "models/vosk-model-small-ko-0.22" ]; then
  echo -e "${YELLOW}  모델 다운로드 중 (~82 MB)...${RESET}"
  npm run download-model
else
  echo -e "${GREEN}  ✓ 모델 이미 존재함${RESET}"
fi

# ── .env ──────────────────────────────────────────────────────────────────────
if [ ! -f ".env" ]; then
  cp .env.example .env
  echo -e "\n${YELLOW}  .env 파일 생성됨. 필요시 수정하세요.${RESET}"
fi

echo -e "\n${GREEN}${BOLD}✓ 설치 완료!${RESET}"
echo -e "\n실행 방법:"
echo -e "  ${BOLD}npm start${RESET}\n"
