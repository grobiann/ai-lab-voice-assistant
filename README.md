# Voice Typer

로컬 Whisper 모델을 사용한 한국어 음성 딕테이션 도구입니다.
단축키 한 번으로 녹음을 시작하고, 말이 끝나면 인식된 텍스트가 현재 커서 위치에 자동으로 입력됩니다.

---

## 빠른 시작

### Linux / macOS

```bash
chmod +x run.sh && ./run.sh
```

최초 실행 시 가상환경 생성과 패키지 설치가 자동으로 진행됩니다.

앱 메뉴(GNOME/KDE)에 **Voice Typer** 항목이 자동 등록됩니다.

### Windows

```
run.vbs  더블클릭 → 설치 + 실행 자동 처리
```

최초 실행 시 설치가 진행된 후 앱이 시작됩니다. 이후부터는 바로 실행됩니다.

> **처음 실행 시** Whisper 모델이 자동 다운로드됩니다 (medium 기준 ~600MB).
> VRAM 부족 시 `config.py`에서 `TIER2_MODEL = "small"` 로 변경하세요.

---

## 주요 기능

- **6가지 STT 모드** — 로컬(tier1/tier2/tier3) / 클라우드(OpenAI/Google/Azure)
- **로컬 STT** — faster-whisper 기반, 인터넷/API 키 불필요
- **LLM 교정** — Whisper 결과를 LLM(Ollama/Groq/Claude)으로 맞춤법·외래어 다듬기
- **커서 위치 자동 입력** — 메모장, 브라우저, 에디터 등 어느 앱에서나 동작
- **클립보드 자동 저장** — 인식 결과를 항상 클립보드에도 저장 (Ctrl+V로 수동 붙여넣기 가능)
- **실시간 레벨 미터** — 녹음 중 마이크 입력 시각화
- **항상-위 오버레이** — 드래그 가능한 플로팅 UI, × 버튼으로 종료
- **GPU 가속** — CUDA 자동 감지, 없으면 CPU fallback

---

## STT 모드

`config.py`의 `STT_MODE` 한 줄만 바꾸면 됩니다.

```python
STT_MODE = "cloud_google"   # 기본값 (API 키 없으면 tier2로 자동 전환)
```

| 모드 | 속도 | 정확도 | 비용 | 필요 조건 |
|------|------|--------|------|----------|
| `tier1` | ★★★★★ | ★★★☆☆ | 무료 | GPU 권장 |
| `tier2` (fallback) | ★★★★☆ | ★★★★★ | 무료 | GPU 권장 |
| `tier3` | ★★★☆☆ | ★★★★★+교정 | LLM_BACKEND에 따라 | GPU + LLM |
| `cloud` | ★★★★☆ | ★★★★☆ | $0.006/분 | OpenAI API 키 |
| **`cloud_google`** (기본) | ★★★★★ | ★★★★★ | 60분/월 무료 → $0.016/분 | Google API 키 |
| `cloud_azure` | ★★★★★ | ★★★★★ | 5시간/월 무료 → $1/시간 | Azure Speech 키 |

---

### 1단계 `"tier1"` — 빠른 응답 우선

```python
STT_MODE    = "tier1"
TIER1_MODEL = "small"   # 기본값
```

- **faster-whisper small 모델** 사용
- GPU VRAM ~1GB, 추론 시간 ~0.5-1초
- API 키, 인터넷 불필요
- 권장 환경: 저사양 GPU / CPU 전용 머신, 실시간 응답이 최우선인 경우

---

### 2단계 `"tier2"` — 속도·정확도 균형 (기본값)

```python
STT_MODE    = "tier2"
TIER2_MODEL = "medium"   # 기본값 (large-v3 대비 ~3배 빠름)
```

- **faster-whisper medium 모델** 사용
- GPU VRAM ~1.5GB, 추론 시간 ~1-2초 (GPU)
- API 키, 인터넷 불필요
- 한국어 일상 발화 정확도 우수 — large-v3와 체감 차이 미미
- 더 높은 정확도가 필요하면 `TIER2_MODEL = "large-v3"` 으로 변경 (~4초)

> 현재 이 모드를 기준으로 개발·테스트합니다.

---

### 3단계 `"tier3"` — 최고 정밀도 (맞춤법·외래어·문장 부호 자동 교정)

faster-whisper 인식 후 **LLM이 교정**합니다. `LLM_BACKEND`로 백엔드를 선택합니다.

```python
STT_MODE    = "tier3"
LLM_BACKEND = "ollama"   # "ollama" | "groq" | "claude"
```

#### LLM 백엔드 선택

| 백엔드 | 비용 | 속도 | 한국어 | 필요 준비 |
|--------|------|------|--------|----------|
| `"ollama"` (기본) | **무료** | 빠름 (로컬 GPU) | ★★★★★ | Ollama + 모델 설치 |
| `"groq"` | **무료** (API 키) | 매우 빠름 (클라우드) | ★★★★☆ | Groq API 키 |
| `"claude"` | 유료 | 빠름 (클라우드) | ★★★★★ | Anthropic API 키 |

---

#### Ollama 설정 (무료, 권장)

```bash
# 1. Ollama 설치: https://ollama.com/download
# 2. 모델 다운로드 (한국어 특화 모델 선택)
ollama pull exaone3.5:7.8b   # LG AI Research, 권장 (VRAM ~6GB)
ollama pull exaone3.5:2.4b   # 경량 버전 (VRAM ~3GB)
```

```python
# config.py
LLM_BACKEND  = "ollama"
OLLAMA_MODEL = "exaone3.5:7.8b"   # 또는 exaone3.5:2.4b
```

#### Groq 설정 (무료 API)

```bash
# API 키 발급: https://console.groq.com (무료, 신용카드 불필요)
# .env 파일에 추가:
GROQ_API_KEY=gsk_...
```

```python
# config.py
LLM_BACKEND = "groq"
```

---

**교정 예시 (한영 혼합 포함):**

```
Whisper 원문: "오늘 유투브에서 챗지피티 api 사용법 봤는데 완전 쉽더라"
LLM 교정:    "오늘 YouTube에서 ChatGPT API 사용법 봤는데 완전 쉽더라."
```

- 추론 시간: ~3-8초 (Whisper + LLM)
- 권장 환경: 문서 작성, 이메일, 한영 혼합 발화, 전문 용어가 많은 경우

---

### 클라우드 `"cloud"` — OpenAI Whisper API

```python
STT_MODE = "cloud"
# .env 에 OPENAI_API_KEY=sk-... 설정
```

- **OpenAI Whisper API** (whisper-1, large-v2 기반)
- 로컬 GPU 불필요
- 비용: $0.006/분 (1분 ≈ 8원), 인터넷 필수

---

### 구글 클라우드 `"cloud_google"` — Google Cloud Speech-to-Text

Android · Chrome 딕테이션과 동일한 엔진입니다.

```python
STT_MODE = "cloud_google"
# .env 에 GOOGLE_API_KEY=AIza... 설정
```

- 속도: ★★★★★  정확도: ★★★★★
- 비용: 60분/월 무료 → $0.016/분
- 설치: `pip install google-cloud-speech` (run.sh/run.vbs 자동 처리)

#### API 키 발급 방법

1. [Google Cloud Console](https://console.cloud.google.com) 접속
2. 프로젝트 생성 또는 선택
3. **API 및 서비스 → 라이브러리** 에서 "Speech-to-Text API" 검색 후 **사용 설정**
4. **API 및 서비스 → 사용자 인증 정보 → 사용자 인증 정보 만들기 → API 키** 클릭
5. 생성된 키를 복사
6. (권장) **키 제한 설정**: API 제한 → Cloud Speech-to-Text API 선택
7. `.env` 파일에 추가:

```bash
GOOGLE_API_KEY=AIza...
```

---

### 애저 `"cloud_azure"` — Azure Cognitive Services Speech

Microsoft 음성인식 엔진입니다. 별도 SDK 없이 Python 내장 `urllib` 만으로 동작합니다.

```python
STT_MODE = "cloud_azure"
# .env 에 AZURE_SPEECH_KEY=... 와 AZURE_SPEECH_REGION=koreacentral 설정
```

- 속도: ★★★★★  정확도: ★★★★★
- 비용: 5시간/월 무료 → $1/시간
- 추가 SDK 불필요

#### API 키 발급 방법

1. [Azure Portal](https://portal.azure.com) 접속 (계정 없으면 무료 계정 생성)
2. **리소스 만들기 → "Speech"** 검색 → **Speech services** 선택
3. 구독, 리소스 그룹, 지역(예: Korea Central), 가격 책정(Free F0) 선택 후 만들기
4. 리소스 생성 완료 후 **키 및 엔드포인트** 메뉴 → **키 1** 복사
5. **지역** 값 확인 (예: `koreacentral`)
6. `.env` 파일에 추가:

```bash
AZURE_SPEECH_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
AZURE_SPEECH_REGION=koreacentral
```

---

## 속도 튜닝

응답 시간은 **모델 크기**와 **beam 크기**가 결정합니다.

### 모델 크기별 예상 속도 (mid-range GPU 기준)

| 모델 | 추론 시간 | 한국어 정확도 | VRAM | 설정 |
|------|----------|-------------|------|------|
| `small` | ~0.8초 | ★★★★☆ | ~1GB | `TIER2_MODEL = "small"` |
| **`medium`** (기본) | **~1.5초** | **★★★★★** | ~1.5GB | **기본값** |
| `large-v3` | ~4초 | ★★★★★+ | ~3GB | `TIER2_MODEL = "large-v3"` |

> medium과 large-v3의 한국어 일상 발화 정확도 차이는 미미합니다.
> 전문 용어·강한 사투리가 많다면 large-v3이 유리합니다.

### beam 크기

```python
WHISPER_BEAM = 1   # 최속 (greedy decode) ← 기본값
WHISPER_BEAM = 2   # 균형
WHISPER_BEAM = 5   # 최정확 (약 1.5배 느림)
```

### 목표별 권장 조합

| 목표 | STT_MODE | TIER2_MODEL | WHISPER_BEAM | 예상 시간 |
|------|----------|-------------|--------------|----------|
| **2초 이하** | tier2 | `small` | 1 | ~0.8초 |
| **2-3초 (기본)** | tier2 | `medium` | 1 | ~1.5초 |
| **최고 정밀** | tier2 | `large-v3` | 1 | ~4초 |
| **최고 정밀 + 교정** | tier3 | `medium` | 1 | ~3-4초 |

---

## 벤치마크 도구

여러 모델의 속도와 정확도를 비교하고 원하는 모드를 선택할 수 있습니다.

```bash
python benchmark.py              # 마이크 녹음 후 전체 모델 비교
python benchmark.py --wav FILE   # WAV 파일로 테스트 (녹음 생략)
python benchmark.py --models small medium large-v3   # 특정 모델만 테스트
```

비교 결과 표에서 번호를 선택하면 `config.py`가 자동으로 업데이트됩니다.

---

## 사용 방법

1. `./run.sh` (Linux/Mac) 또는 `run.vbs` (Windows) 실행 → 화면 우하단에 오버레이 창 등장
2. 텍스트를 입력할 앱(메모장, 카카오톡 등)에 커서 위치
3. **`Ctrl+Space`** → 오버레이가 `● REC`로 바뀌면 말하기 시작
4. **`Ctrl+Space`** 다시 누름 → 인식 후 커서 위치에 텍스트 자동 입력
5. 오버레이 **`×`** 버튼으로 앱 종료

> 자동 입력이 안 된 경우 **`Ctrl+V`** 로 클립보드에서 붙여넣기 가능합니다.

---

## 설치 상세

`run.sh` / `run.vbs` 최초 실행 시 아래 과정을 자동으로 처리합니다.

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

### API 키 설정

`.env` 파일에 사용할 모드의 키를 입력합니다.

```bash
# tier3 (LLM 교정)
GROQ_API_KEY=gsk_...            # groq 백엔드
ANTHROPIC_API_KEY=sk-ant-...    # claude 백엔드

# 클라우드 STT
OPENAI_API_KEY=sk-...           # cloud 모드
GOOGLE_API_KEY=AIza...          # cloud_google 모드
AZURE_SPEECH_KEY=xxx...         # cloud_azure 모드
AZURE_SPEECH_REGION=koreacentral
```

---

## 설정 (`config.py`)

**STT 모드**

| 항목 | 기본값 | 설명 |
|------|--------|------|
| `STT_MODE` | `"cloud_google"` | `"tier1"` / `"tier2"` / `"tier3"` / `"cloud"` / `"cloud_google"` / `"cloud_azure"` |

**로컬 Whisper (tier1 / tier2 / tier3)**

| 항목 | 기본값 | 설명 |
|------|--------|------|
| `TIER1_MODEL` | `"small"` | 1단계 Whisper 모델 크기 |
| `TIER2_MODEL` | `"medium"` | 2단계 Whisper 모델 크기 |
| `TIER3_MODEL` | `"medium"` | 3단계 Whisper 모델 크기 (LLM 교정이 핵심) |
| `WHISPER_LANG` | `"ko"` | 인식 언어 |
| `WHISPER_DEVICE` | `"cuda"` | `"cuda"` / `"cpu"` |
| `WHISPER_COMPUTE` | `"float16"` | GPU: `"float16"` / CPU: `"int8"` |
| `WHISPER_BEAM` | `1` | Beam search 크기 (1=greedy 최속 / 5=최정확) |
| `WHISPER_TEMPERATURE` | `[0, 0.2]` | 불확실 구간 자동 재시도 온도. `0`=greedy 전용 |

**LLM 교정 (tier3)**

| 항목 | 기본값 | 설명 |
|------|--------|------|
| `LLM_BACKEND` | `"ollama"` | `"ollama"` / `"groq"` / `"claude"` |
| `OLLAMA_HOST` | `"http://localhost:11434"` | Ollama 서버 주소 |
| `OLLAMA_MODEL` | `"exaone3.5:7.8b"` | Ollama 모델 (`ollama list`로 확인) |
| `GROQ_LLM_MODEL` | `"llama-3.1-8b-instant"` | Groq 모델명 |
| `CLAUDE_LLM_MODEL` | `"claude-haiku-4-5-20251001"` | Claude 모델명 |

**Google Cloud STT (cloud_google)**

| 항목 | 기본값 | 설명 |
|------|--------|------|
| `GOOGLE_STT_MODEL` | `"latest_short"` | `"latest_short"` (딕테이션) / `"latest_long"` (1분 이상) |

**Azure Cognitive Services (cloud_azure)**

| 항목 | 기본값 | 설명 |
|------|--------|------|
| `AZURE_SPEECH_REGION` | `"koreacentral"` | Azure 리소스 지역 |

**API 키**

| 항목 | 기본값 | 필요 모드 |
|------|--------|----------|
| `GROQ_API_KEY` | `""` | tier3 (groq 백엔드) |
| `ANTHROPIC_API_KEY` | `""` | tier3 (claude 백엔드) |
| `OPENAI_API_KEY` | `""` | cloud |
| `GOOGLE_API_KEY` | `""` | cloud_google |
| `AZURE_SPEECH_KEY` | `""` | cloud_azure |

**출력**

| 항목 | 기본값 | 설명 |
|------|--------|------|
| `TYPER_TRAILING_SPACE` | `True` | 텍스트 끝 공백 추가 |

---

## 프로젝트 구조

```
ai-lab-voice-assistant/
├── main.py               # 진입점 — 전체 컴포넌트 조합 및 단축키 리스너
├── config.py             # 전체 설정값 (STT 모드, API 키 등)
├── benchmark.py          # STT 모델 속도·정확도 비교 도구
├── requirements.txt      # Python 의존성
├── .env.example          # API 키 설정 예시
├── run.sh                # Linux/macOS 원 버튼 실행 (설치 포함)
├── run.vbs               # Windows 원 버튼 실행 (설치 포함)
│
├── core/
│   └── state_machine.py  # 스레드 안전 상태 기계 (IDLE / RECORDING / PROCESSING)
│
├── audio/
│   ├── recorder.py       # sounddevice 마이크 녹음 + 실시간 RMS 레벨 콜백
│   └── stt.py            # STT 백엔드 6종 (tier1/2/3 로컬, OpenAI/Google/Azure 클라우드)
│
├── output/
│   └── typer.py          # 커서 위치에 텍스트 입력 (xdotool → Ctrl+V / pynput)
│
└── ui/
    └── overlay.py        # tkinter 항상-위 플로팅 오버레이
```

---

## 의존성

| 패키지 | 용도 | 필요 모드 |
|--------|------|-----------|
| `faster-whisper` | 로컬 Whisper STT | tier1, tier2, tier3 |
| `openai` | OpenAI Whisper API / Ollama·Groq 호환 클라이언트 | cloud, tier3 |
| `anthropic` | Claude LLM 교정 | tier3 (claude 백엔드) |
| `google-cloud-speech` | Google Cloud STT | cloud_google |
| `sounddevice` | 마이크 오디오 수집 | 모든 모드 |
| `soundfile` | numpy → WAV 변환 | cloud, cloud_azure |
| `numpy` | 오디오 데이터 처리 | 모든 모드 |
| `pynput` | 전역 단축키 + 텍스트 입력 | 모든 모드 |
| `python-dotenv` | `.env` 파일 자동 로드 | 모든 모드 |
