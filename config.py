# config.py — 전체 설정값

# ── Whisper ────────────────────────────────────────────────────────────────────
# 모델 크기: tiny | base | small | medium | large
# GTX 1060 기준 base 권장 (한국어 정확도 ↑, 추론 ~1-2초)
WHISPER_MODEL   = "base"
WHISPER_LANG    = "ko"         # 언어 고정 (자동 감지보다 빠름)
WHISPER_DEVICE  = "cuda"       # "cuda" | "cpu" — CUDA 없으면 자동으로 cpu fallback

# ── 오디오 ─────────────────────────────────────────────────────────────────────
SAMPLE_RATE     = 16000        # Whisper 권장 샘플레이트
CHANNELS        = 1            # 모노
AUDIO_DEVICE    = None         # None = 시스템 기본 마이크 / 정수 = 디바이스 인덱스

# ── 단축키 ─────────────────────────────────────────────────────────────────────
# pynput Key 이름 또는 문자열
# 조합키: {'ctrl', 'alt'} + 일반 키
HOTKEY_MODIFIERS = {'ctrl'}
HOTKEY_KEY       = 'space'

# ── UI ─────────────────────────────────────────────────────────────────────────
OVERLAY_WIDTH        = 420     # 오버레이 창 너비 (px)
OVERLAY_RESULT_MS    = 3000    # 인식 결과 표시 시간 (ms) 후 텍스트 영역 초기화

# ── 텍스트 출력 ────────────────────────────────────────────────────────────────
# 인식된 텍스트를 커서 위치에 붙여넣은 뒤 단어 사이 공백 처리
TYPER_TRAILING_SPACE = True    # True = 텍스트 끝에 공백 1개 추가
