# config.py — 전체 설정값

import os

# .env 파일 자동 로드
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv 미설치 시 환경변수 직접 설정 또는 아래 키값 직접 입력

# ══════════════════════════════════════════════════════════════════════════════════
# 기본 STT — Google Cloud Speech-to-Text
# ══════════════════════════════════════════════════════════════════════════════════
# 발급: https://console.cloud.google.com → Speech-to-Text API 활성화 → API 키 생성
# .env 파일에 GOOGLE_API_KEY=AIza... 입력
GOOGLE_API_KEY   = os.environ.get("GOOGLE_API_KEY", "")
GOOGLE_STT_MODEL = "latest_short"   # "latest_short" (딕테이션) | "latest_long" (1분 이상)

# 초기 STT 모드 — GOOGLE_API_KEY 설정 여부에 따라 자동 결정
STT_MODE = "cloud_google" if GOOGLE_API_KEY else "local_whisper"

# ══════════════════════════════════════════════════════════════════════════════════
# Fallback STT — 로컬 Whisper (faster-whisper)
# Google STT API 키 미설정 또는 호출 실패 시 자동으로 전환됩니다.
# ══════════════════════════════════════════════════════════════════════════════════
# 모델 크기 선택 (mid-range GPU 기준):
#   "small"    ~0.8초  VRAM ~1GB
#   "medium"   ~1.5초  VRAM ~1.5GB  ← 기본값 (정확도 우수)
#   "large-v3" ~4초    VRAM ~3GB    (전문 용어·사투리에 유리)
WHISPER_MODEL       = "medium"

WHISPER_LANG        = "ko"         # 언어 고정 (자동 감지보다 빠름)
WHISPER_DEVICE      = "cuda"       # "cuda" | "cpu" — CUDA 없으면 자동 cpu 전환
WHISPER_COMPUTE     = "float16"    # GPU: "float16" | CPU: "int8"
WHISPER_BEAM        = 1            # 1=greedy(최속) / 2=균형 / 5=최정확
WHISPER_TEMPERATURE = [0, 0.2]     # greedy 실패 구간 자동 재시도
WHISPER_INITIAL_PROMPT = ""        # 기본값 ""(비활성) — 단어 나열 형식만 안전

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
