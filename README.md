# Voice Typer

로컬 Whisper 모델을 사용한 한국어 음성 딕테이션 도구입니다.
단축키 한 번으로 녹음을 시작하고, 말이 끝나면 인식된 텍스트가 현재 커서 위치에 자동으로 입력됩니다.

---

## 주요 기능

- **3가지 STT 모드 선택** — 로컬 / OpenAI API / 로컬+LLM 교정
- **로컬 STT** — faster-whisper 기반, 인터넷/API 키 불필요
- **LLM 교정** — Whisper 결과를 Claude API로 맞춤법·문장 다듬기
- **커서 위치 자동 입력** — 메모장, 브라우저, 에디터 등 어느 앱에서나 동작
- **클립보드 자동 저장** — 인식 결과를 항상 클립보드에도 저장 (Ctrl+V로 수동 붙여넣기 가능)
- **실시간 레벨 미터** — 녹음 중 마이크 입력 시각화
- **항상-위 오버레이** — 드래그 가능한 플로팅 UI, × 버튼으로 종료
- **GPU 가속** — CUDA 자동 감지, 없으면 CPU fallback

---

## STT 모드

`config.py`의 `STT_MODE` 값 하나로 전환합니다.

### `"local"` — faster-whisper 로컬 실행 (기본값)

```python
STT_MODE = "local"
WHISPER_MODEL = "large-v3"   # 모델 크기 선택
```

- API 키, 인터넷 연결 불필요
- GPU(CUDA) 권장 — CPU도 동작하나 느림
- faster-whisper는 원본 Whisper 대비 2~4배 빠름

| 모델 | VRAM | 속도 (GPU) | 한국어 정확도 |
|------|------|-----------|-------------|
| tiny | ~1GB | 매우 빠름 | ★★☆☆☆ |
| base | ~1GB | 빠름 | ★★★☆☆ |
| small | ~2GB | 보통 | ★★★★☆ |
| large-v3 | ~3GB\* | 보통 | ★★★★★ |

\* faster-whisper는 int8/float16 양자화로 원본 대비 VRAM 절반

---

### `"openai"` — OpenAI Whisper API

```python
STT_MODE = "openai"
OPENAI_API_KEY = "sk-..."   # 또는 환경변수 OPENAI_API_KEY
```

- 인터넷 및 OpenAI API 키 필요
- 로컬 GPU 불필요
- 비용: $0.006/분 (1분 ≈ 8원)

---

### `"local+llm"` — faster-whisper + Claude 교정

```python
STT_MODE      = "local+llm"
WHISPER_MODEL = "large-v3"
ANTHROPIC_API_KEY = "sk-ant-..."   # 또는 환경변수 ANTHROPIC_API_KEY
```

- Whisper 인식 → Claude Haiku가 맞춤법·띄어쓰기·문장 부호 교정
- 전문 용어, 구어체 표현, 빠른 발화에서 효과적

```
Whisper 원문: "오늘미팅에서 중요한내용을 논의했어"
Claude 교정: "오늘 미팅에서 중요한 내용을 논의했어."
```

---

## 설치

```bash
# 1. 저장소 클론
git clone <repo-url>
cd ai-lab-voice-assistant

# 2. 의존성 설치
pip install -r requirements.txt

# 3. API 키 설정 (openai / local+llm 모드 사용 시)
cp .env.example .env
# .env 파일에 API 키 입력
```

> **GPU(CUDA) 환경**: `faster-whisper`가 자동으로 CUDA를 감지합니다.
> PyTorch CUDA 버전이 필요하면 [pytorch.org](https://pytorch.org/get-started/locally/) 참조.

### Linux 추가 설정

pynput 텍스트 입력이 안 될 경우 xdotool 설치:

```bash
sudo apt install xdotool
```

---

## 실행

```bash
python main.py
```

`"local"` 모드 최초 실행 시 Whisper 모델이 자동 다운로드됩니다.

---

## 사용 방법

1. `python main.py` 실행 → 화면 우하단에 오버레이 창 등장
2. 텍스트를 입력할 앱(메모장, 카카오톡 등)에 커서 위치
3. **`Ctrl+Space`** → 오버레이가 `● REC`로 바뀌면 말하기 시작
4. **`Ctrl+Space`** 다시 누름 → 인식 후 커서 위치에 텍스트 자동 입력
5. 오버레이 **`×`** 버튼으로 앱 종료

> 자동 입력이 안 된 경우 **`Ctrl+V`** 로 클립보드에서 붙여넣기 가능합니다.

---

## 설정 (`config.py`)

| 항목 | 기본값 | 설명 |
|------|--------|------|
| `STT_MODE` | `"local"` | `"local"` / `"openai"` / `"local+llm"` |
| `WHISPER_MODEL` | `"large-v3"` | 로컬 모드 모델 크기 |
| `WHISPER_LANG` | `"ko"` | 인식 언어 |
| `WHISPER_DEVICE` | `"cuda"` | `"cuda"` / `"cpu"` |
| `WHISPER_COMPUTE` | `"float16"` | GPU: `"float16"` / CPU: `"int8"` |
| `WHISPER_BEAM` | `5` | Beam search 크기 (클수록 정확, 느림) |
| `OPENAI_API_KEY` | `""` | OpenAI API 키 |
| `ANTHROPIC_API_KEY` | `""` | Anthropic API 키 |
| `LLM_MODEL` | `"claude-haiku-4-5-20251001"` | LLM 교정 모델 |
| `TYPER_TRAILING_SPACE` | `True` | 텍스트 끝 공백 추가 |

---

## 프로젝트 구조

```
ai-lab-voice-assistant/
├── main.py               # 진입점 — 전체 컴포넌트 조합 및 단축키 리스너
├── config.py             # 전체 설정값 (STT 모드, API 키 등)
├── requirements.txt      # Python 의존성
├── .env.example          # API 키 설정 예시
│
├── core/
│   └── state_machine.py  # 스레드 안전 상태 기계 (IDLE / RECORDING / PROCESSING)
│
├── audio/
│   ├── recorder.py       # sounddevice 마이크 녹음 + 실시간 RMS 레벨 콜백
│   └── stt.py            # STT 백엔드 3종 (local / openai / local+llm)
│
├── output/
│   └── typer.py          # 커서 위치에 텍스트 입력 (pynput → xdotool → Ctrl+V)
│
└── ui/
    └── overlay.py        # tkinter 항상-위 플로팅 오버레이
```

---

## 의존성

| 패키지 | 용도 | 필요 모드 |
|--------|------|-----------|
| `faster-whisper` | 로컬 Whisper STT | local, local+llm |
| `openai` | OpenAI Whisper API | openai |
| `anthropic` | Claude LLM 교정 | local+llm |
| `sounddevice` | 마이크 오디오 수집 | 모든 모드 |
| `soundfile` | numpy → WAV 변환 | openai |
| `numpy` | 오디오 데이터 처리 | 모든 모드 |
| `pynput` | 전역 단축키 + 텍스트 입력 | 모든 모드 |
