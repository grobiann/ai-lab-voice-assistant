# Voice Typer

Google Cloud Speech-to-Text를 사용한 한국어 음성 딕테이션 도구입니다.
단축키 한 번으로 녹음을 시작하고, 말이 끝나면 인식된 텍스트가 현재 커서 위치에 자동으로 입력됩니다.

---

## 빠른 시작

### Windows

```
run.vbs  더블클릭 → 설치 + 실행 자동 처리
```

### Linux / macOS

```bash
chmod +x run.sh && ./run.sh
```

최초 실행 시 가상환경 생성과 패키지 설치가 자동으로 진행됩니다.

---

## API 키 설정

`.env` 파일에 Google API 키를 입력합니다.

```bash
GOOGLE_API_KEY=AIza...
```

**발급 방법:**

1. [Google Cloud Console](https://console.cloud.google.com) 접속
2. 프로젝트 생성 또는 선택
3. **API 및 서비스 → 라이브러리** 에서 "Speech-to-Text API" 검색 후 **사용 설정**
4. **API 및 서비스 → 사용자 인증 정보 → API 키 만들기**
5. 생성된 키를 `.env` 파일에 붙여넣기

> API 키 미설정 시 Fallback STT(로컬 Whisper)로 자동 전환됩니다. 모델은 `config.py`의 `WHISPER_MODEL`로 설정합니다.

---

## 사용 방법

1. `run.vbs` (Windows) 또는 `./run.sh` (Linux/Mac) 실행 → 화면 우하단에 오버레이 창 등장
2. 텍스트를 입력할 앱(메모장, 브라우저 등)에 커서 위치
3. **`Ctrl+Space`** → 오버레이가 `● REC`로 바뀌면 말하기 시작
4. **`Ctrl+Space`** 다시 누름 → 인식 후 커서 위치에 텍스트 자동 입력
5. 오버레이 **`×`** 버튼으로 앱 종료

> 자동 입력이 안 된 경우 **`Ctrl+V`** 로 클립보드에서 붙여넣기 가능합니다.

---

## 설정 (`config.py`)

**기본 STT — Google Cloud Speech-to-Text**

| 항목 | 기본값 | 설명 |
|------|--------|------|
| `GOOGLE_API_KEY` | `""` | `.env` 에 설정. 미설정 시 Whisper fallback 자동 전환 |
| `GOOGLE_STT_MODEL` | `"latest_short"` | `"latest_short"` (딕테이션) / `"latest_long"` (1분 이상) |

**Fallback STT — 로컬 Whisper (faster-whisper)**

| 항목 | 기본값 | 설명 |
|------|--------|------|
| `WHISPER_MODEL` | `"medium"` | 모델 크기: `"small"` / `"medium"` / `"large-v3"` |
| `WHISPER_DEVICE` | `"cuda"` | `"cuda"` / `"cpu"` — CUDA 없으면 자동 cpu 전환 |

**출력 / UI**

| 항목 | 기본값 | 설명 |
|------|--------|------|
| `OVERLAY_RESULT_MS` | `3000` | 인식 결과 표시 시간 (ms) |
| `TYPER_TRAILING_SPACE` | `True` | 텍스트 끝에 공백 1개 추가 |

---

## 설치 상세

`run.sh` / `run.vbs` 최초 실행 시 아래 과정을 자동으로 처리합니다.

```
1. Python 3.8+ 확인
2. .venv/ 가상환경 생성
3. requirements.txt 패키지 설치
4. .env.example → .env 복사 (최초 1회)
```

### Linux 텍스트 입력 문제

자동 입력이 작동하지 않는 경우 xdotool 설치:

```bash
sudo apt install xdotool
```

---

## 프로젝트 구조

```
ai-lab-voice-assistant/
├── main.py               # 진입점 — 전체 컴포넌트 조합 및 단축키 리스너
├── config.py             # 전체 설정값
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
│   └── stt.py            # Google Cloud STT + 로컬 Whisper fallback
│
├── output/
│   └── typer.py          # 커서 위치에 텍스트 입력 (xdotool → Ctrl+V / pynput)
│
└── ui/
    └── overlay.py        # tkinter 항상-위 플로팅 오버레이
```

---

## 의존성

| 패키지 | 용도 |
|--------|------|
| `google-cloud-speech` | Google Cloud STT (기본) |
| `faster-whisper` | 로컬 Whisper STT (fallback) |
| `sounddevice` | 마이크 오디오 수집 |
| `numpy` | 오디오 데이터 처리 |
| `pynput` | 전역 단축키 + 텍스트 입력 |
| `python-dotenv` | `.env` 파일 자동 로드 |
