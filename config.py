# config.py — 전체 설정값

import os

# ── STT 모드 선택 ───────────────────────────────────────────────────────────────
#
#   "local"     : faster-whisper 로컬 실행 (GPU 권장, API 키 불필요)
#   "openai"    : OpenAI Whisper API (인터넷 필요, OPENAI_API_KEY 필요)
#   "local+llm" : faster-whisper 인식 후 Claude API로 교정 (두 API 키 모두 필요)
#
STT_MODE = "local"

# ── Whisper 로컬 설정 (STT_MODE = "local" | "local+llm") ───────────────────────
# 모델 크기: tiny | base | small | medium | large-v2 | large-v3
# GTX 1060(6GB) 권장: small  /  RTX 3070+ 권장: large-v3
WHISPER_MODEL   = "large-v3"
WHISPER_LANG    = "ko"         # 언어 고정 (자동 감지보다 빠름)
WHISPER_DEVICE  = "cuda"       # "cuda" | "cpu" — CUDA 없으면 자동 cpu fallback
WHISPER_COMPUTE = "float16"    # GPU: "float16" | CPU: "int8"
WHISPER_BEAM    = 5            # Beam search 크기 (클수록 정확하지만 느림, 기본 5)

# ── API 키 (환경변수 우선, 없으면 아래에 직접 입력) ───────────────────────────────
# .env 파일 또는 환경변수로 설정 권장
OPENAI_API_KEY    = os.environ.get("OPENAI_API_KEY",    "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

# ── LLM 교정 설정 (STT_MODE = "local+llm") ────────────────────────────────────
LLM_MODEL = "claude-haiku-4-5-20251001"   # 빠르고 저렴한 모델 권장

# ── 오디오 ─────────────────────────────────────────────────────────────────────
SAMPLE_RATE  = 16000   # Whisper 권장 샘플레이트
CHANNELS     = 1       # 모노
AUDIO_DEVICE = None    # None = 시스템 기본 마이크 / 정수 = 디바이스 인덱스

# ── 단축키 ─────────────────────────────────────────────────────────────────────
HOTKEY_MODIFIERS = {'ctrl'}
HOTKEY_KEY       = 'space'

# ── UI ─────────────────────────────────────────────────────────────────────────
OVERLAY_WIDTH     = 420    # 오버레이 창 너비 (px)
OVERLAY_RESULT_MS = 3000   # 인식 결과 표시 시간 (ms) 후 안내 문구로 복귀

# ── 텍스트 출력 ────────────────────────────────────────────────────────────────
TYPER_TRAILING_SPACE = True   # True = 텍스트 끝에 공백 1개 추가
