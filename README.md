# Voice Typer

로컬 Whisper 모델을 사용한 한국어 음성 딕테이션 도구입니다.
단축키 한 번으로 녹음을 시작하고, 말이 끝나면 인식된 텍스트가 현재 커서 위치에 자동으로 입력됩니다.

---

## 빠른 시작

### Linux / macOS

```bash
# 1. 설치 (최초 1회)
chmod +x install.sh && ./install.sh

# 2. 실행
./run.sh
```

앱 메뉴(GNOME/KDE)에 **Voice Typer** 항목이 자동 등록됩니다.

### Windows

```
1. install.bat  더블클릭 → 설치
2. run.bat      더블클릭 → 실행
```

> **처음 실행 시** Whisper 모델이 자동 다운로드됩니다 (large-v3 기준 ~1.5GB).
> VRAM 부족 시 `config.py`에서 `TIER2_MODEL = "small"` 로 변경하세요.

---

## 주요 기능

- **3단계 정확도 선택** — tier1(빠름) / tier2(균형) / tier3(최고정밀+교정)
- **로컬 STT** — faster-whisper 기반, 인터넷/API 키 불필요
- **LLM 교정** — Whisper 결과를 Claude API로 맞춤법·문장 다듬기
- **커서 위치 자동 입력** — 메모장, 브라우저, 에디터 등 어느 앱에서나 동작
- **클립보드 자동 저장** — 인식 결과를 항상 클립보드에도 저장 (Ctrl+V로 수동 붙여넣기 가능)
- **실시간 레벨 미터** — 녹음 중 마이크 입력 시각화
- **항상-위 오버레이** — 드래그 가능한 플로팅 UI, × 버튼으로 종료
- **GPU 가속** — CUDA 자동 감지, 없으면 CPU fallback

---

## STT 정확도 단계

`config.py`의 `STT_MODE` 한 줄만 바꾸면 됩니다.

```python
STT_MODE = "tier2"   # 기본값
```

| 단계 | 속도 | 정확도 | 비용 | 필요 조건 |
|------|------|--------|------|----------|
| `tier1` | ★★★★★ | ★★★☆☆ | 무료 | GPU 권장 |
| **`tier2`** (기본) | ★★★★☆ | ★★★★★ | 무료 | GPU 권장 |
| `tier3` | ★★★☆☆ | ★★★★★+교정 | Claude API | GPU + API 키 |
| `cloud` | ★★★★☆ | ★★★★☆ | $0.006/분 | OpenAI API 키 |

---

### 1단계 `"tier1"` — 빠른 응답 우선

```python
STT_MODE  = "tier1"
TIER1_MODEL = "small"   # 기본값, 필요 시 변경 가능
```

- **faster-whisper small 모델** 사용
- GPU VRAM ~2GB, 추론 시간 ~0.5-1초
- API 키, 인터넷 불필요
- 권장 환경: 저사양 GPU / CPU 전용 머신, 실시간 응답이 최우선인 경우

---

### 2단계 `"tier2"` — 속도·정확도 균형 (기본값, 개발·테스트 기준)

```python
STT_MODE    = "tier2"
TIER2_MODEL = "large-v3"   # 기본값
```

- **faster-whisper large-v3 모델** 사용
- GPU VRAM ~3GB (float16 양자화로 원본 Whisper 대비 절반)
- API 키, 인터넷 불필요
- 추론 시간 ~1-3초 (GPU) / ~15-30초 (CPU)
- 한국어 정확도 최고 수준 — 대부분의 일상 사용에 충분

> 현재 이 모드를 기준으로 개발·테스트합니다.

---

### 3단계 `"tier3"` — 최고 정밀도 (맞춤법·문장 부호 자동 교정)

```python
STT_MODE          = "tier3"
TIER3_MODEL       = "large-v3"   # 기본값
ANTHROPIC_API_KEY = "sk-ant-..."   # 환경변수 ANTHROPIC_API_KEY 권장
```

- **faster-whisper large-v3** 인식 후 **Claude Haiku**가 후처리
- 맞춤법, 띄어쓰기, 문장 부호, 구어체→문어체 변환
- 추론 시간 ~3-6초 (Whisper + API 왕복)
- 권장 환경: 문서 작성, 이메일, 전문 용어·빠른 발화가 많은 경우

```
Whisper 원문: "오늘미팅에서 중요한내용을 논의했어 다음주까지 보고서 작성해야돼"
Claude 교정: "오늘 미팅에서 중요한 내용을 논의했어. 다음 주까지 보고서 작성해야 돼."
```

---

### 클라우드 `"cloud"` — 로컬 GPU 없는 환경용 (고급 옵션)

```python
STT_MODE       = "cloud"
OPENAI_API_KEY = "sk-..."   # 환경변수 OPENAI_API_KEY 권장
```

- **OpenAI Whisper API** (whisper-1, large-v2 기반)
- 로컬 GPU 불필요
- 비용: $0.006/분 (1분 ≈ 8원), 인터넷 필수

---

## 설치 상세

위 "빠른 시작"의 `install.sh` / `install.bat` 가 아래 과정을 자동으로 처리합니다.

```
1. Python 3.8+ 확인
2. .venv/ 가상환경 생성
3. requirements.txt 패키지 설치
4. .env.example → .env 복사 (최초 1회)
5. [Linux] 앱 메뉴 바로가기 자동 등록
```

### GPU(CUDA) 설정

`faster-whisper`가 CUDA를 자동 감지합니다.
PyTorch가 CUDA를 인식하지 못할 경우 → [pytorch.org](https://pytorch.org/get-started/locally/) 에서 CUDA 버전에 맞는 PyTorch 설치.

### Linux 텍스트 입력 문제

자동 입력이 작동하지 않는 경우 xdotool 설치:

```bash
sudo apt install xdotool
```

### API 키 설정 (tier3 / cloud 모드)

`.env` 파일에 키 입력:

```bash
ANTHROPIC_API_KEY=sk-ant-...   # tier3 용
OPENAI_API_KEY=sk-...          # cloud 용
```

---

## 사용 방법

1. `./run.sh` (Linux/Mac) 또는 `run.bat` (Windows) 실행 → 화면 우하단에 오버레이 창 등장
2. 텍스트를 입력할 앱(메모장, 카카오톡 등)에 커서 위치
3. **`Ctrl+Space`** → 오버레이가 `● REC`로 바뀌면 말하기 시작
4. **`Ctrl+Space`** 다시 누름 → 인식 후 커서 위치에 텍스트 자동 입력
5. 오버레이 **`×`** 버튼으로 앱 종료

> 자동 입력이 안 된 경우 **`Ctrl+V`** 로 클립보드에서 붙여넣기 가능합니다.

---

## 설정 (`config.py`)

| 항목 | 기본값 | 설명 |
|------|--------|------|
| `STT_MODE` | `"tier2"` | `"tier1"` / `"tier2"` / `"tier3"` / `"cloud"` |
| `TIER1_MODEL` | `"small"` | 1단계 Whisper 모델 크기 |
| `TIER2_MODEL` | `"large-v3"` | 2단계 Whisper 모델 크기 |
| `TIER3_MODEL` | `"large-v3"` | 3단계 Whisper 모델 크기 |
| `WHISPER_LANG` | `"ko"` | 인식 언어 |
| `WHISPER_DEVICE` | `"cuda"` | `"cuda"` / `"cpu"` |
| `WHISPER_COMPUTE` | `"float16"` | GPU: `"float16"` / CPU: `"int8"` |
| `WHISPER_BEAM` | `5` | Beam search 크기 (클수록 정확, 느림) |
| `OPENAI_API_KEY` | `""` | OpenAI API 키 (cloud 모드) |
| `ANTHROPIC_API_KEY` | `""` | Anthropic API 키 (tier3 모드) |
| `LLM_MODEL` | `"claude-haiku-4-5-20251001"` | tier3 교정 모델 |
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
