# config.py — 전체 설정값

import os

# ── STT 정확도 단계 선택 ─────────────────────────────────────────────────────────
#
#   "tier1" : 1단계 — 빠른 응답 우선
#             faster-whisper (small 모델) 로컬 실행
#             속도: ★★★★★  정확도: ★★★☆☆  비용: 무료
#             사용 시나리오: 저사양 GPU / CPU 환경, 실시간에 가까운 응답이 필요할 때
#             VRAM: ~2GB, 추론 시간: ~0.5-1초 (GPU)
#
#   "tier2" : 2단계 — 속도와 정확도의 균형  ← 기본값, 이 모드로 개발·테스트
#             faster-whisper (large-v3 모델) 로컬 실행
#             속도: ★★★★☆  정확도: ★★★★★  비용: 무료
#             사용 시나리오: 일반적인 사용, API 키 없이 최고 수준의 로컬 정확도
#             VRAM: ~3GB (float16 양자화), 추론 시간: ~1-3초 (GPU)
#
#   "tier3" : 3단계 — 최고 정밀도 (맞춤법·띄어쓰기·문장 부호 자동 교정)
#             faster-whisper (large-v3) + Claude Haiku API 교정
#             속도: ★★★☆☆  정확도: ★★★★★+교정  비용: Claude API 과금
#             사용 시나리오: 문서 작성, 이메일, 전문 용어가 많은 경우
#             VRAM: ~3GB, 추론 시간: ~3-6초 (Whisper + API 왕복)
#             ANTHROPIC_API_KEY 필요
#
#   "cloud" : 클라우드 대체 — 로컬 GPU 없는 환경용 (고급 옵션)
#             OpenAI Whisper API (whisper-1 / large-v2 기반)
#             속도: ★★★★☆  정확도: ★★★★☆  비용: $0.006/분
#             OPENAI_API_KEY 필요
#
STT_MODE = "tier2"

# ── 단계별 Whisper 모델 ──────────────────────────────────────────────────────────
TIER1_MODEL = "small"      # 빠름, VRAM ~2GB
TIER2_MODEL = "large-v3"   # 균형, VRAM ~3GB (float16 양자화)
TIER3_MODEL = "large-v3"   # tier3도 large-v3 사용 (LLM 교정이 핵심)

# ── 공통 Whisper 설정 ────────────────────────────────────────────────────────────
WHISPER_LANG    = "ko"         # 언어 고정 (자동 감지보다 빠름)
WHISPER_DEVICE  = "cuda"       # "cuda" | "cpu" — CUDA 없으면 자동 cpu fallback
WHISPER_COMPUTE = "float16"    # GPU: "float16" | CPU: "int8"
WHISPER_BEAM    = 5            # Beam search 크기 (클수록 정확하지만 느림, 기본 5)

# ── API 키 (환경변수 우선, 없으면 아래에 직접 입력) ───────────────────────────────
# .env 파일 또는 환경변수로 설정 권장
OPENAI_API_KEY    = os.environ.get("OPENAI_API_KEY",    "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

# ── LLM 교정 설정 (STT_MODE = "tier3") ────────────────────────────────────────
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
