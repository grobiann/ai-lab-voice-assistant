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
#   "cloud" : 클라우드 대체 — 로컬 GPU 없는 환경용 (고급 옵션)
#             OpenAI Whisper API (whisper-1 / large-v2 기반)
#             속도: ★★★★☆  정확도: ★★★★☆  비용: $0.006/분
#             OPENAI_API_KEY 필요
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

# ── Whisper 한영 혼합 초기 프롬프트 (어휘 힌트 토큰) ─────────────────────────────
#
# Whisper에 "이런 단어가 나올 수 있다"는 어휘 힌트를 주어 한영 혼합 인식률을 높입니다.
# 속도 변화 없이 정확도를 개선하는 가장 안전한 방법입니다.
#
# ✅ 안전한 형식 — 단어·고유명사 나열 (현재 설정):
#      Whisper가 어휘 참고용으로만 사용 → 환각(hallucination) 없음
#
# ⛔ 위험한 형식 — 완전한 문장 (예: "한국어 음성이며 영어 단어가 포함됩니다"):
#      Whisper가 해당 문장을 그대로 출력하는 환각 현상 발생 가능
#
# 자신의 발화에 맞게 자주 쓰는 용어를 자유롭게 추가·제거하세요.
WHISPER_INITIAL_PROMPT = (
    "YouTube, API, GPT, ChatGPT, GPU, CPU, RAM, SSD, iPhone, MacBook, "
    "Python, GitHub, Docker, npm, Node.js, React, Linux, Ubuntu, "
    "LLM, AI, UI, UX, URL, HTTP, JSON, SDK, IDE, PC, Mac, "
    "Whisper, Ollama, Groq, Claude, OpenAI"
)

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
