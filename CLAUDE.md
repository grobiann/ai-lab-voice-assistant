# CLAUDE.md

## 프로젝트 개요

Google Cloud Speech-to-Text (fallback: 로컬 Whisper)를 사용한 한국어 음성 딕테이션 도구.
단축키(`Ctrl+Space`)로 녹음을 시작/종료하고, 인식된 텍스트를 현재 커서 위치에 자동 입력한다.

## 프로젝트 구조

```
ai-lab-voice-assistant/
├── main.py               # 진입점 — 전체 컴포넌트 조합 및 단축키 리스너
├── config.py             # 전체 설정값
├── requirements.txt      # Python 의존성
├── .env.example          # API 키 설정 예시
├── run.sh                # Linux/macOS 실행 (설치 자동 포함)
├── run.vbs               # Windows 실행 — 콘솔 창 없음 (권장)
├── run.bat               # Windows 실행 — 콘솔 창 표시 (오류 확인용)
│
├── core/
│   └── state_machine.py  # 스레드 안전 상태 기계 (IDLE / RECORDING / PROCESSING)
│
├── audio/
│   ├── recorder.py       # sounddevice 마이크 녹음 + 실시간 RMS 레벨 콜백
│   └── stt.py            # Google Cloud STT + 로컬 Whisper fallback
│
├── output/
│   └── typer.py          # 커서 위치에 텍스트 입력 (xdotool → Ctrl+V / pynput)
│
└── ui/
    └── overlay.py        # tkinter 항상-위 플로팅 오버레이
```

## 아키텍처

### 상태 흐름

```
IDLE → (Ctrl+Space) → RECORDING → (Ctrl+Space) → PROCESSING → IDLE
```

- `core/state_machine.py`가 상태를 관리하며 스레드 안전 보장
- `main.py`가 pynput 키 리스너와 각 컴포넌트를 연결

### 컴포넌트 역할

| 모듈 | 책임 |
|------|------|
| `main.py` | 컴포넌트 초기화, 단축키 이벤트 → 상태 전이 |
| `core/state_machine.py` | 상태 전이 로직, 콜백 등록 |
| `audio/recorder.py` | 마이크 스트림 열기/닫기, 오디오 버퍼 수집 |
| `audio/stt.py` | Google STT API 호출 → 실패/미설정 시 Whisper로 fallback |
| `output/typer.py` | Linux: xdotool → 실패 시 Ctrl+V / Windows·Mac: pynput |
| `ui/overlay.py` | tkinter 기반 항상-위 플로팅 창, 상태별 UI 업데이트 |

### STT 우선순위

1. `GOOGLE_API_KEY` 설정 시 → Google Cloud STT (`latest_short` 모델 기본)
2. 키 미설정 또는 API 오류 시 → 로컬 faster-whisper (`medium` 모델 기본)

## 개발 환경 실행

```bash
# 가상환경 활성화
source .venv/bin/activate          # Linux/macOS
.venv\Scripts\activate             # Windows

# 직접 실행
python main.py
```

## 주요 설정 (`config.py`)

- `GOOGLE_API_KEY` — `.env`에서 로드
- `GOOGLE_STT_MODEL` — `"latest_short"` / `"latest_long"`
- `WHISPER_MODEL` — `"small"` / `"medium"` / `"large-v3"`
- `WHISPER_DEVICE` — `"cuda"` / `"cpu"` (CUDA 없으면 자동 전환)
- `OVERLAY_RESULT_MS` — 인식 결과 표시 시간 (ms)
- `TYPER_TRAILING_SPACE` — 텍스트 끝 공백 추가 여부
