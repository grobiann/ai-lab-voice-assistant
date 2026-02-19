# AI Lab — Claude 음성 활성화 트리거

마이크로 음성을 항상 듣고 있다가, **"클로드"** 라는 단어가 감지되면 Claude 창을 열고 이후 말을 자동으로 입력합니다.
수동으로 제출할 때까지 절대 자동 제출하지 않으며, 말을 계속 이어 붙입니다.

---

## 작동 방식

```
🎤  항상 듣는 중 (Vosk 오프라인 STT)
        │
        ├─ "클로드" 감지
        │       │
        │       ├─ Claude 창 열기 / 포커스
        │       │
        │       └─ 이후 음성 → Claude 입력창에 자동 타이핑
        │               │
        │               ├─ 계속 말하면 이어서 입력됨
        │               └─ 직접 Enter 또는 전송 버튼으로 제출
        │
        └─ "취소" or "그만" → 비활성화, 다시 대기
```

- **자동 제출 없음** — 사용자가 직접 Enter 또는 전송 버튼을 눌러야 합니다.
- **계속 누적** — 말을 멈춰도 대기하며, 다음에 말하면 이어서 입력합니다.
- **완전 오프라인** — [Vosk](https://alphacephei.com/vosk/) 로컬 모델 사용, API 키 불필요.

---

## 아키텍처

```
Node.js (src/)                    Python (python/stt_server.py)
──────────────                    ──────────────────────────────
index.js                          ├─ sounddevice   ← 마이크 녹음
  ├─ wakeDetector.js              ├─ vosk          ← 한국어 STT
  ├─ automator.js  ─── cmd ──→   ├─ focus_claude  ← 창 포커스
  └─ recognizer.js ←── ack ──    └─ type_text     ← 텍스트 입력
          │                (stdin/stdout JSON lines)
          └─ partial / final events
```

Node.js가 Python 서브프로세스를 시작합니다.
- Python → Node.js: 음성 인식 결과 (`partial`, `final`)
- Node.js → Python: 자동화 명령 (`focus_claude`, `type_text`)
- Python이 창 제어 + 텍스트 입력까지 처리하므로 **Windows / Linux 모두 동작**합니다.

---

## 설치

### Windows (PowerShell)

```powershell
powershell -ExecutionPolicy Bypass -File setup.ps1
```

### Linux / macOS

```bash
bash setup.sh
```

### 수동 설치 — Linux

#### 1. 시스템 패키지

```bash
sudo apt install xdotool xclip
```

#### 2. Python 패키지

```bash
pip3 install "setuptools<67"   # srt 빌드 호환성
pip3 install srt
pip3 install -r requirements.txt
```

### 수동 설치 — Windows

#### 1. Python 패키지

```powershell
pip install "setuptools<67"
pip install srt
pip install -r requirements.txt
pip install pygetwindow pyperclip pyautogui
```

### 공통 (Windows/Linux 모두)

#### Node.js 패키지

```bash
npm install
```

#### Vosk 한국어 모델 다운로드 (~82 MB)

```bash
npm run download-model
```

모델이 `models/vosk-model-small-ko-0.22/` 에 저장됩니다.

#### 환경 변수 설정

```bash
# Linux
cp .env.example .env

# Windows PowerShell
Copy-Item .env.example .env
```

---

## 실행

```bash
npm start
```

---

## 사용법

| 동작 | 음성 명령 |
|------|-----------|
| 활성화 | `"클로드"` |
| 활성화 + 즉시 내용 | `"클로드 오늘 날씨 어때?"` |
| 비활성화 (대기로 복귀) | `"취소"` 또는 `"그만"` |
| 종료 | `Ctrl+C` |

### 전형적인 흐름

```
1. npm start 실행
2. "클로드"라고 말함
3. → Claude 창이 열리거나 포커스됨
4. 계속 말하면 → Claude 입력창에 텍스트가 누적됨
5. 원하는 시점에 직접 Enter 또는 전송 버튼 클릭
```

---

## 환경 변수 (`.env`)

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `MODEL_PATH` | `./models/vosk-model-small-ko-0.22` | Vosk 모델 경로 |
| `AUDIO_DEVICE` | (시스템 기본) | 마이크 장치 인덱스 (`python3 -c "import sounddevice; print(sounddevice.query_devices())"` 로 확인) |
| `WAKE_WORDS` | `클로드,claude,클로디` | 웨이크 워드 목록 (쉼표 구분) |
| `DEACTIVATE_WORDS` | `취소,그만,cancel,stop` | 비활성화 단어 목록 |
| `CLAUDE_WINDOW_NAMES` | `Claude,claude.ai` | X11 창 제목 검색 패턴 |
| `CLAUDE_APP_PATH` | (없음) | Claude 데스크톱 앱 실행 경로 |

---

## 기술 스택

| 구성 요소 | 라이브러리 | 역할 |
|-----------|------------|------|
| **Python** | [vosk](https://alphacephei.com/vosk/) | 오프라인 한국어 STT (Kaldi 기반) |
| **Python** | [sounddevice](https://python-sounddevice.readthedocs.io/) | 마이크 녹음 (PortAudio 내장) |
| **Python (Windows)** | pygetwindow | 창 검색 / 포커스 |
| **Python (Windows)** | pyperclip + pyautogui | 클립보드 붙여넣기로 한글 입력 |
| **Python (Linux)** | xdotool + xclip (시스템) | 창 관리 + 클립보드 입력 |
| **Node.js** | [node-notifier](https://github.com/mikaelbr/node-notifier) | 데스크톱 알림 |
| **Node.js** | [adm-zip](https://github.com/cthackers/adm-zip) + [axios](https://axios-http.com/) | 모델 다운로드 |
| **Node.js** | [dotenv](https://github.com/motdotla/dotenv) + [chalk](https://github.com/chalk/chalk) | 환경 변수, 콘솔 출력 |

---

## 문제 해결

**"Model directory not found"**
→ `npm run download-model` 실행

**"Failed to open microphone"**
→ 마이크 장치 확인:
  - Linux: `python3 -c "import sounddevice; print(sounddevice.query_devices())"`
  - Windows: `python -c "import sounddevice; print(sounddevice.query_devices())"`
→ `.env`에서 `AUDIO_DEVICE=<숫자>` 로 장치 지정

**Claude 창을 못 찾음**
→ Claude를 미리 열어둔 상태에서 실행
→ 창 제목 확인:
  - Linux: `xdotool search --name "Claude"`
  - Windows PowerShell: `python -c "import pygetwindow as gw; print([w.title for w in gw.getAllWindows() if w.title])"`
→ `.env`의 `CLAUDE_WINDOW_NAMES`에 정확한 창 제목 추가

**한국어가 입력되지 않음 (Linux)**
→ `which xclip` 확인 → 없으면: `sudo apt install xclip`

**한국어가 입력되지 않음 (Windows)**
→ `pip install pyperclip pyautogui` 실행

**vosk/srt 설치 오류**
→ `pip install "setuptools<67" && pip install srt` 먼저 실행

**PowerShell 실행 정책 오류**
→ `powershell -ExecutionPolicy Bypass -File setup.ps1`
