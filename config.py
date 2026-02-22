# config.py — 전체 설정값

import os

# .env 파일 자동 로드 — install.sh / run.bat 에서 별도 처리 없이 API 키 적용됨
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv 미설치 시 환경변수 직접 설정 또는 아래 키값 직접 입력

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
#   "tier3" : 3단계 — 최고 정밀도 (맞춤법·외래어·문장 부호 자동 교정)
#             faster-whisper (large-v3) + LLM 교정 (LLM_BACKEND 선택)
#             속도: ★★★☆☆  정확도: ★★★★★+교정  비용: LLM_BACKEND에 따라 무료~유료
#             사용 시나리오: 문서 작성, 이메일, 한영 혼합 발화, 전문 용어가 많은 경우
#             VRAM: ~3GB, 추론 시간: ~3-8초 (Whisper + LLM)
#
#   "cloud" : OpenAI Whisper API — 로컬 GPU 없는 환경용
#             whisper-1 모델 기반  비용: $0.006/분  OPENAI_API_KEY 필요
#             속도: ★★★★☆  정확도: ★★★★☆
#
#   "cloud_google" : Google Cloud Speech-to-Text ← Android·Chrome 딕테이션과 동일 엔진
#                    속도: ★★★★★  정확도: ★★★★★  비용: 60분/월 무료 → $0.016/분
#                    GOOGLE_API_KEY 필요 (발급: https://console.cloud.google.com)
#                    설치: pip install google-cloud-speech
#
#   "cloud_azure"  : Azure Cognitive Services Speech ← Microsoft 음성인식 엔진
#                    속도: ★★★★★  정확도: ★★★★★  비용: 5시간/월 무료 → $1/시간
#                    AZURE_SPEECH_KEY + AZURE_SPEECH_REGION 필요
#                    발급: https://portal.azure.com → 'Speech services' 생성
#                    (별도 SDK 불필요 — requests 만으로 동작)
#
STT_MODE = "tier2"

# ── 단계별 Whisper 모델 ──────────────────────────────────────────────────────────
# 속도 vs 정확도 트레이드오프 (mid-range GPU 기준 추론 시간):
#   tiny   ~0.3초  ★★☆☆☆ 정확도
#   base   ~0.5초  ★★★☆☆ 정확도
#   small  ~0.8초  ★★★★☆ 정확도
#   medium ~1.5초  ★★★★★ 정확도  ← tier2 기본 (2-3초 목표)
#   large-v3 ~4초  ★★★★★ 정확도 (medium과 한국어 일상 발화 차이 미미)
TIER1_MODEL = "small"      # 빠름, VRAM ~1GB
TIER2_MODEL = "medium"     # 균형, VRAM ~1.5GB  (large-v3 대비 ~3배 빠름)
TIER3_MODEL = "medium"     # tier3는 LLM 교정이 핵심 — Whisper를 medium으로 속도 확보

# ── 공통 Whisper 설정 ────────────────────────────────────────────────────────────
WHISPER_LANG    = "ko"         # 언어 고정 (자동 감지보다 빠름)
WHISPER_DEVICE  = "cuda"       # "cuda" | "cpu" — CUDA 없으면 자동 cpu fallback
WHISPER_COMPUTE = "float16"    # GPU: "float16" | CPU: "int8"
WHISPER_BEAM    = 1            # 1=greedy(최속) / 2=균형 / 5=최정확
#                              # beam 1→2 로 높이면 정확도↑ 대신 속도 ~1.5배 느려짐

# ── Whisper 온도 — 불확실 구간 자동 재시도 ────────────────────────────────────────
#
# [0, 0.2]   : greedy(0)로 먼저 시도 → 신뢰도 낮은 구간은 0.2 로 재시도 (기본 권장)
#              단어 목록 없이 한영 혼합·전문용어 인식률을 높이는 범용적 방법입니다.
# 0          : greedy 전용 (최속, 재시도 없음)
# [0, 0.2, 0.4] : 재시도 단계 추가 (더 느리지만 불명확한 발화에 유리)
WHISPER_TEMPERATURE = [0, 0.2]

# ── Whisper 초기 프롬프트 (고급·선택 설정) ──────────────────────────────────────
# 기본값 ""(비활성) — WHISPER_TEMPERATURE 방식이 더 범용적입니다.
# ✅ 안전한 형식: 단어 나열  예) "API, GPT, YouTube"  → 환각 없음
# ⛔ 위험한 형식: 완전한 문장  → Whisper가 문장을 그대로 출력하는 환각 발생
WHISPER_INITIAL_PROMPT = ""

# ── LLM 교정 백엔드 (STT_MODE = "tier3") ────────────────────────────────────────
#
#   "ollama" : Ollama 로컬 LLM — 완전 무료, 인터넷 불필요 ← 기본값
#              OLLAMA_MODEL 모델을 로컬에서 실행 (Ollama 설치 + 모델 pull 필요)
#
#   "groq"   : Groq API 무료 티어 — API 키 필요하지만 무료
#              30 req/min, 14,400 req/day — 음성 교정 용도로 충분
#              GROQ_API_KEY 필요 (발급: https://console.groq.com)
#
#   "claude" : Anthropic Claude API — 유료, 최고 한국어 품질
#              ANTHROPIC_API_KEY 필요
#
LLM_BACKEND = "ollama"

# ── Ollama 설정 ──────────────────────────────────────────────────────────────────
# 모델 선택 가이드:
#   exaone3.5:7.8b  — LG AI Research, 한국어 특화, 권장 (VRAM ~6GB)
#   exaone3.5:2.4b  — 경량, 빠름 (VRAM ~3GB)
#   qwen2.5:7b      — 알리바바, 한국어 양호, 빠름 (VRAM ~5GB)
#   qwen2.5:3b      — 초경량 (VRAM ~2.5GB)
OLLAMA_HOST  = "http://localhost:11434"
OLLAMA_MODEL = "exaone3.5:7.8b"

# ── Groq 설정 (LLM_BACKEND = "groq") ────────────────────────────────────────────
GROQ_API_KEY   = os.environ.get("GROQ_API_KEY", "")
GROQ_LLM_MODEL = "llama-3.1-8b-instant"   # 빠름, 한국어 지원

# ── Claude 설정 (LLM_BACKEND = "claude") ────────────────────────────────────────
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
CLAUDE_LLM_MODEL  = "claude-haiku-4-5-20251001"

# ── 기타 API 키 ─────────────────────────────────────────────────────────────────
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")   # cloud 모드용

# ── Google Cloud Speech-to-Text (STT_MODE = "cloud_google") ──────────────────────
# 발급: https://console.cloud.google.com → API 및 서비스 → Speech-to-Text API 활성화
# API 키 방식(간단) 또는 서비스 계정 JSON(GOOGLE_APPLICATION_CREDENTIALS 환경변수) 가능
# 설치: pip install google-cloud-speech
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "")

# ── Azure Cognitive Services Speech (STT_MODE = "cloud_azure") ───────────────────
# 발급: https://portal.azure.com → Speech services 리소스 생성 → 키 및 엔드포인트
# 지역 예시: koreacentral, eastus, japaneast, southeastasia
# (별도 SDK 불필요 — Python 내장 urllib 만으로 동작)
AZURE_SPEECH_KEY    = os.environ.get("AZURE_SPEECH_KEY", "")
AZURE_SPEECH_REGION = os.environ.get("AZURE_SPEECH_REGION", "koreacentral")

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
