# Voice Typer

로컬 Whisper 모델을 사용한 한국어 음성 딕테이션 도구입니다.
단축키 한 번으로 녹음을 시작하고, 말이 끝나면 인식된 텍스트가 현재 커서 위치에 자동으로 입력됩니다.
인터넷 연결이나 API 키 없이 완전히 로컬에서 동작합니다.

---

## 주요 기능

- **로컬 STT** — OpenAI Whisper를 로컬에서 실행 (인터넷/API 키 불필요)
- **한국어 최적화** — 언어 고정으로 빠른 인식
- **커서 위치 자동 입력** — 메모장, 브라우저, 에디터 등 어느 앱에서나 동작
- **클립보드 자동 저장** — 인식 결과를 항상 클립보드에도 저장 (Ctrl+V로 수동 붙여넣기 가능)
- **실시간 레벨 미터** — 녹음 중 마이크 입력 시각화
- **항상-위 오버레이** — 드래그 가능한 플로팅 UI
- **GPU 가속** — CUDA 사용 가능 시 자동 전환, 없으면 CPU fallback

---

## 동작 방식

```
Ctrl+Space 누름
    │
    ▼
마이크 녹음 시작 (sounddevice)
    │
Ctrl+Space 다시 누름
    │
    ▼
Whisper 추론 (로컬, ~1~3초)
    │
    ├─► 클립보드에 저장 (tkinter)
    │
    └─► 현재 커서 위치에 텍스트 입력 (pynput)
```

---

## 요구 사항

| 항목 | 최소 사양 |
|------|-----------|
| Python | 3.8 이상 |
| OS | Windows / Linux / macOS |
| GPU | 선택 사항 (CUDA — 속도 향상) |
| 마이크 | 시스템 기본 마이크 |

---

## 설치

```bash
# 1. 저장소 클론
git clone <repo-url>
cd ai-lab-voice-assistant

# 2. 의존성 설치
pip install -r requirements.txt

# 3. (선택) CUDA 사용 시 PyTorch GPU 버전 설치
#    https://pytorch.org/get-started/locally/ 참조
```

### Linux 추가 설정

pynput이 키보드 입력을 전송하려면 X11 환경이 필요합니다.
텍스트 입력이 되지 않을 경우 xdotool을 설치하면 fallback으로 사용됩니다:

```bash
sudo apt install xdotool
```

---

## 실행

```bash
python main.py
```

최초 실행 시 Whisper 모델이 자동으로 다운로드됩니다 (base 모델 약 140MB).

---

## 사용 방법

1. `python main.py` 실행 → 화면 우하단에 오버레이 창 등장
2. 텍스트를 입력할 앱(메모장, 카카오톡 등)에 커서 위치
3. **`Ctrl+Space`** → 오버레이가 `● REC`로 바뀌면 말하기 시작
4. **`Ctrl+Space`** 다시 누름 → 인식 후 커서 위치에 텍스트 자동 입력
5. 오버레이 **`×`** 버튼으로 앱 종료

> 인식 결과는 클립보드에도 저장되므로, 자동 입력이 안 된 경우 **`Ctrl+V`** 로 붙여넣기 가능합니다.

---

## 설정 (`config.py`)

| 항목 | 기본값 | 설명 |
|------|--------|------|
| `WHISPER_MODEL` | `"base"` | 모델 크기: `tiny` / `base` / `small` / `medium` / `large` |
| `WHISPER_LANG` | `"ko"` | 인식 언어 (고정 시 속도 향상) |
| `WHISPER_DEVICE` | `"cuda"` | `"cuda"` 또는 `"cpu"` (CUDA 없으면 자동 CPU fallback) |
| `HOTKEY_MODIFIERS` | `{'ctrl'}` | 단축키 조합키 |
| `HOTKEY_KEY` | `'space'` | 단축키 키 |
| `TYPER_TRAILING_SPACE` | `True` | 인식 텍스트 뒤 공백 자동 추가 |

### 모델 크기별 비교

| 모델 | 크기 | 속도 (CPU) | 속도 (GPU) | 한국어 정확도 |
|------|------|-----------|-----------|-------------|
| tiny | 75MB | 빠름 | 매우 빠름 | 보통 |
| base | 140MB | 보통 | 빠름 | 좋음 ✓ |
| small | 460MB | 느림 | 보통 | 매우 좋음 |
| medium | 1.5GB | 매우 느림 | 느림 | 최고 |

---

## 프로젝트 구조

```
ai-lab-voice-assistant/
├── main.py               # 진입점 — 전체 컴포넌트 조합 및 단축키 리스너
├── config.py             # 전체 설정값
├── requirements.txt      # Python 의존성
│
├── core/
│   └── state_machine.py  # 스레드 안전 상태 기계 (IDLE / RECORDING / PROCESSING)
│
├── audio/
│   ├── recorder.py       # sounddevice 마이크 녹음 + 실시간 RMS 레벨 콜백
│   └── stt.py            # Whisper 로컬 추론
│
├── output/
│   └── typer.py          # 커서 위치에 텍스트 입력 (pynput → xdotool → Ctrl+V 순 시도)
│
└── ui/
    └── overlay.py        # tkinter 항상-위 플로팅 오버레이
```

---

## 의존성

| 패키지 | 용도 |
|--------|------|
| `openai-whisper` | 로컬 STT 모델 |
| `sounddevice` | 마이크 오디오 수집 |
| `numpy` | 오디오 데이터 처리 |
| `pynput` | 전역 단축키 감지 + 텍스트 키 입력 |
