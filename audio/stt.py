# audio/stt.py — STT 백엔드 (tier1 / tier2 / tier3 / cloud / cloud_google / cloud_azure)

import time
import threading
import numpy as np

import config

# ── 로컬 모델 상태 ─────────────────────────────────────────────────────────────
_local_model      = None
_local_model_name = None   # 현재 로드된 모델 이름 추적
_local_model_lock = threading.Lock()

# ── LLM 교정 공통 프롬프트 ──────────────────────────────────────────────────────
# 한영 혼합 발화를 포함해 맞춤법·외래어 표기를 교정하는 지시문
_POLISH_PROMPT = """\
다음은 한국어 음성인식(Whisper) 결과입니다.
아래 규칙에 따라 교정하고, 교정된 텍스트만 출력하세요 (설명·주석 없이).

교정 규칙:
1. 한국어 맞춤법·띄어쓰기·문장 부호를 교정하세요.
2. 영어 단어·외래어가 잘못 인식된 경우 올바른 표기로 수정하세요.
   예) '유투브' → 'YouTube', '지피티' → 'GPT', '에이피아이' → 'API',
       '아이폰' → 'iPhone', '챗지피티' → 'ChatGPT', '파이썬' → 'Python'
3. 영어 단어는 문맥에 맞게 영문 또는 한글 외래어 표기로 통일하세요.
4. 원문의 내용·의미를 절대 변경하지 마세요.
5. 이미 올바른 문장이면 그대로 반환하세요.

원문: {raw}"""


# ── 공개 API ───────────────────────────────────────────────────────────────────

def load_model(on_ready=None):
    """
    앱 시작 시 호출 — tier1/2/3는 로컬 Whisper 모델을 미리 로드합니다.
    cloud_google 모드이지만 API 키가 없으면 tier2 로컬 모델을 미리 로드합니다.
    on_ready: 로드 완료 후 호출할 콜백 (선택, 어떤 스레드에서도 안전)
    """
    import os
    if config.STT_MODE in ("tier1", "tier2", "tier3"):
        _ensure_local_model()
    elif config.STT_MODE == "cloud_google":
        has_key = bool(config.GOOGLE_API_KEY or os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"))
        if has_key:
            print("[STT] 모드: cloud_google — Google API 키 확인됨 (tier2 fallback 대기)")
        else:
            print("[STT] GOOGLE_API_KEY 없음 — tier2 (로컬 Whisper) 로 자동 전환")
            _ensure_local_model()
    else:
        print(f"[STT] 모드: {config.STT_MODE} — 로컬 Whisper 불필요")
    if on_ready:
        on_ready()


def transcribe(audio: np.ndarray, status_cb=None, mode_cb=None) -> str:
    """
    float32 numpy 배열(16kHz mono)을 텍스트로 변환합니다.

    status_cb: callable(str) — 처리 단계를 UI에 표시할 콜백 (선택)
    mode_cb:   callable(str) — 실제 사용된 STT 모드 이름을 UI에 전달할 콜백 (선택)
               cloud_google fallback 발생 시 로컬 Whisper로 변경됐음을 통지하는 데 사용
    반환값: 인식된 텍스트 (공백 포함), 실패 시 빈 문자열
    """
    if audio is None or len(audio) == 0:
        return ""

    mode  = config.STT_MODE
    model = _tier_model_name() if mode in ("tier1", "tier2", "tier3") else mode
    dur   = len(audio) / config.SAMPLE_RATE
    rms   = float(np.sqrt(np.mean(audio ** 2))) if len(audio) > 0 else 0.0

    print(f"\n{'═'*54}")
    print(f"[Pipeline] {mode} / {model}  |  오디오 {dur:.1f}s  RMS {rms:.4f}")

    t_start = time.perf_counter()
    text    = ""

    try:
        if mode == "tier1":
            if status_cb: status_cb("1단계 인식 중...")
            text = _transcribe_local(audio)

        elif mode == "tier2":
            if status_cb: status_cb("2단계 인식 중...")
            text = _transcribe_local(audio)

        elif mode == "tier3":
            if status_cb: status_cb("3단계 인식 중...")
            raw = _transcribe_local(audio)
            if not raw:
                return ""
            backend = config.LLM_BACKEND.lower()
            if status_cb: status_cb(f"교정 중... ({backend})")
            t_llm = time.perf_counter()
            text  = _polish_with_llm(raw)
            print(f"  LLM ({backend}): {time.perf_counter()-t_llm:.2f}s")
            print(f"    '{raw}'")
            print(f"    → '{text}'")

        elif mode == "cloud":
            if status_cb: status_cb("클라우드 인식 중...")
            text = _transcribe_openai(audio)

        elif mode == "cloud_google":
            if status_cb: status_cb("Google STT 인식 중...")
            if mode_cb:   mode_cb("Google STT")
            try:
                text = _transcribe_google(audio)
            except Exception as google_err:
                print(f"[STT] Google STT 실패: {google_err}")
                print("[STT] fallback → tier2 (로컬 Whisper)")
                if status_cb: status_cb("로컬 STT로 전환 중...")
                if mode_cb:   mode_cb(f"로컬 Whisper ({config.TIER2_MODEL}) ↩")
                _ensure_local_model()
                text = _transcribe_local(audio)

        elif mode == "cloud_azure":
            if status_cb: status_cb("Azure STT 인식 중...")
            text = _transcribe_azure(audio)

        else:
            print(f"[STT] 알 수 없는 STT_MODE: '{mode}'")
            print( "      사용 가능: tier1 / tier2 / tier3 / cloud / cloud_google / cloud_azure")
            return ""

    except Exception as e:
        print(f"[STT] 오류 ({mode}): {e}")
        return ""

    elapsed = time.perf_counter() - t_start
    print(f"[Pipeline] 총 {elapsed:.2f}s  →  '{text}'")
    print(f"{'═'*54}")
    return text


# ── 단계별 모델 선택 헬퍼 ──────────────────────────────────────────────────────

def _tier_model_name() -> str:
    return {
        "tier1": config.TIER1_MODEL,
        "tier2": config.TIER2_MODEL,
        "tier3": config.TIER3_MODEL,
    }.get(config.STT_MODE, config.TIER2_MODEL)


# ── faster-whisper 로컬 백엔드 ──────────────────────────────────────────────────

def _ensure_local_model():
    global _local_model, _local_model_name
    target   = _tier_model_name()
    do_warmup = False

    with _local_model_lock:
        if _local_model is not None and _local_model_name == target:
            return

        try:
            from faster_whisper import WhisperModel
        except ImportError:
            raise ImportError(
                "faster-whisper가 설치되지 않았습니다.\n"
                "실행: pip install faster-whisper"
            )

        device = config.WHISPER_DEVICE
        try:
            import torch
            if device == "cuda" and not torch.cuda.is_available():
                print("[STT] CUDA 사용 불가 — CPU로 전환")
                device = "cpu"
        except ImportError:
            device = "cpu"

        compute = config.WHISPER_COMPUTE if device == "cuda" else "int8"

        print(f"[STT] faster-whisper '{target}' 로딩 ({device}, {compute})...")
        _local_model      = WhisperModel(target, device=device, compute_type=compute)
        _local_model_name = target
        print("[STT] 로컬 모델 로드 완료")
        do_warmup = (device == "cuda")

    # 워밍업은 lock 밖에서 실행 — lock 점유 중 차단 문제 해결
    if do_warmup:
        _warmup(_local_model)


def _warmup(model) -> None:
    """앱 시작 시 CUDA 커널을 미리 컴파일 — 첫 실제 추론의 지연(2-3초) 제거."""
    try:
        dummy = np.zeros(3200, dtype=np.float32)   # 0.2초 묵음
        list(model.transcribe(dummy, language="ko", beam_size=1)[0])
        print("[STT] GPU 워밍업 완료 (첫 추론 지연 제거됨)")
    except Exception as e:
        print(f"[STT] GPU 워밍업 실패 (무시): {e}")


def _transcribe_local(audio: np.ndarray) -> str:
    """faster-whisper 추론 — 세그먼트별 상세 로그 포함."""
    _ensure_local_model()
    with _local_model_lock:
        model = _local_model

    t0 = time.perf_counter()

    temperature = getattr(config, "WHISPER_TEMPERATURE", [0, 0.2])
    prompt      = config.WHISPER_INITIAL_PROMPT or None

    segs, _ = model.transcribe(
        audio.astype(np.float32),
        language=config.WHISPER_LANG,
        beam_size=config.WHISPER_BEAM,
        initial_prompt=prompt,
        condition_on_previous_text=False,
        vad_filter=True,
        vad_parameters={"min_silence_duration_ms": 300},
        temperature=temperature,
    )

    parts = []
    for i, seg in enumerate(segs):
        t = seg.text.strip()
        if not t:
            continue
        print(
            f"  │ [{i+1}] {seg.start:.1f}s→{seg.end:.1f}s  "
            f"logprob={seg.avg_logprob:.2f}  no_speech={seg.no_speech_prob:.2f}"
        )
        print(f"  │     → '{t}'")
        parts.append(t)

    elapsed = time.perf_counter() - t0
    result  = " ".join(parts).strip()
    print(f"  └ Whisper {elapsed:.2f}s  → '{result}'")
    return result


# ── cloud 백엔드 (OpenAI Whisper API) ──────────────────────────────────────────

def _transcribe_openai(audio: np.ndarray) -> str:
    """
    OpenAI Whisper API (cloud 모드).
    로컬 GPU 없는 환경에서 사용. whisper-1 모델 기반.

    설정: OPENAI_API_KEY (.env 또는 환경변수)
    비용: $0.006/분
    설치: pip install openai soundfile
    """
    import io
    import soundfile as sf

    api_key = config.OPENAI_API_KEY
    if not api_key:
        raise ValueError(
            "OPENAI_API_KEY가 비어 있습니다.\n"
            ".env 또는 환경변수에 OPENAI_API_KEY를 설정하세요."
        )

    from openai import OpenAI
    client = OpenAI(api_key=api_key)

    buf = io.BytesIO()
    sf.write(buf, audio.astype(np.float32), config.SAMPLE_RATE,
             format="wav", subtype="PCM_16")
    buf.seek(0)
    buf.name = "audio.wav"

    result = client.audio.transcriptions.create(
        model="whisper-1",
        file=buf,
        language=config.WHISPER_LANG,
    )
    return result.text.strip()


# ── Google Cloud Speech-to-Text 백엔드 ─────────────────────────────────────────

def _transcribe_google(audio: np.ndarray) -> str:
    """
    Google Cloud Speech-to-Text API.

    인증 방법 (둘 중 하나):
      1. GOOGLE_API_KEY 환경변수 / .env 설정 (간단)
      2. GOOGLE_APPLICATION_CREDENTIALS 환경변수에 서비스 계정 JSON 경로 설정

    설치: pip install google-cloud-speech
    """
    try:
        from google.cloud import speech as gcp_speech
    except ImportError:
        raise ImportError(
            "google-cloud-speech 가 설치되지 않았습니다.\n"
            "실행: pip install google-cloud-speech"
        )

    api_key = config.GOOGLE_API_KEY
    if api_key:
        # API 키 방식 — 서비스 계정 없이 간단히 사용 가능
        client = gcp_speech.SpeechClient(
            client_options={"api_key": api_key}
        )
    else:
        import os
        if not os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
            raise ValueError(
                "GOOGLE_API_KEY 또는 GOOGLE_APPLICATION_CREDENTIALS 가 필요합니다.\n"
                "  .env 에 GOOGLE_API_KEY=... 를 입력하거나\n"
                "  GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json 설정"
            )
        client = gcp_speech.SpeechClient()

    # numpy float32 → PCM 16-bit bytes
    audio_bytes = (
        audio.clip(-1.0, 1.0) * 32767
    ).astype(np.int16).tobytes()

    gcp_audio  = gcp_speech.RecognitionAudio(content=audio_bytes)
    gcp_config = gcp_speech.RecognitionConfig(
        encoding=gcp_speech.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=config.SAMPLE_RATE,
        language_code="ko-KR",
        model=getattr(config, "GOOGLE_STT_MODEL", "latest_short"),
        enable_automatic_punctuation=True,
    )

    response = client.recognize(config=gcp_config, audio=gcp_audio)
    return " ".join(
        result.alternatives[0].transcript
        for result in response.results
        if result.alternatives
    ).strip()


# ── Azure Cognitive Services Speech 백엔드 ──────────────────────────────────────

def _transcribe_azure(audio: np.ndarray) -> str:
    """
    Azure Cognitive Services Speech REST API.
    별도 SDK 불필요 — Python 내장 urllib 만으로 동작합니다.

    설정:
      AZURE_SPEECH_KEY    : Azure Speech 리소스 키
      AZURE_SPEECH_REGION : 리소스 지역 (예: koreacentral, eastus)
    발급: https://portal.azure.com → Speech services 리소스 생성
    """
    import io
    import json
    import urllib.request
    import urllib.error
    import soundfile as sf

    key    = config.AZURE_SPEECH_KEY
    region = config.AZURE_SPEECH_REGION

    if not key:
        raise ValueError(
            "AZURE_SPEECH_KEY 가 설정되지 않았습니다.\n"
            ".env 에 AZURE_SPEECH_KEY=<키> 를 입력하세요.\n"
            "발급: https://portal.azure.com → Speech services 리소스 생성"
        )
    if not region:
        raise ValueError(
            "AZURE_SPEECH_REGION 이 설정되지 않았습니다.\n"
            ".env 에 AZURE_SPEECH_REGION=koreacentral 등을 입력하세요."
        )

    # numpy float32 → WAV bytes
    buf = io.BytesIO()
    sf.write(buf, audio.astype(np.float32), config.SAMPLE_RATE,
             format="wav", subtype="PCM_16")
    wav_bytes = buf.getvalue()

    url = (
        f"https://{region}.stt.speech.microsoft.com"
        f"/speech/recognition/conversation/cognitiveservices/v1"
        f"?language=ko-KR&format=simple&profanity=raw"
    )

    req = urllib.request.Request(
        url,
        data=wav_bytes,
        headers={
            "Ocp-Apim-Subscription-Key": key,
            "Content-Type": "audio/wav; codecs=audio/pcm; samplerate=16000",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        raise RuntimeError(f"Azure HTTP {e.code}: {body}")

    if data.get("RecognitionStatus") == "Success":
        return data.get("DisplayText", "").strip()

    # 발화 없음 또는 오류
    status = data.get("RecognitionStatus", "Unknown")
    if status not in ("NoMatch", "InitialSilenceTimeout"):
        print(f"[STT] Azure 상태: {status}")
    return ""


# ── LLM 교정 라우터 ────────────────────────────────────────────────────────────

def _polish_with_llm(raw: str) -> str:
    backend = config.LLM_BACKEND.lower()
    try:
        if backend == "ollama":
            return _polish_ollama(raw)
        elif backend == "groq":
            return _polish_groq(raw)
        elif backend == "claude":
            return _polish_claude(raw)
        else:
            print(f"[STT] 알 수 없는 LLM_BACKEND: '{backend}' — 원문 반환")
            return raw
    except Exception as e:
        print(f"[STT] LLM 교정 실패 ({backend}): {e} — 원문 반환")
        return raw


# ── LLM 백엔드 1: Ollama (로컬, 완전 무료) ─────────────────────────────────────

def _polish_ollama(raw: str) -> str:
    """Ollama 로컬 LLM으로 텍스트 교정 — OpenAI 호환 API 사용."""
    from openai import OpenAI

    client = OpenAI(
        base_url=config.OLLAMA_HOST.rstrip("/") + "/v1",
        api_key="ollama",   # Ollama는 API 키 불필요
    )
    resp = client.chat.completions.create(
        model=config.OLLAMA_MODEL,
        messages=[{"role": "user", "content": _POLISH_PROMPT.format(raw=raw)}],
        max_tokens=500,
        temperature=0.1,   # 낮은 temperature = 일관된 교정
    )
    return resp.choices[0].message.content.strip()


# ── LLM 백엔드 2: Groq (클라우드, 무료 티어) ──────────────────────────────────

def _polish_groq(raw: str) -> str:
    """Groq API 무료 티어로 텍스트 교정 — OpenAI 호환 API 사용."""
    api_key = config.GROQ_API_KEY
    if not api_key:
        raise ValueError(
            "GROQ_API_KEY가 설정되지 않았습니다.\n"
            "발급: https://console.groq.com  →  .env에 GROQ_API_KEY=... 입력"
        )

    from openai import OpenAI
    client = OpenAI(
        base_url="https://api.groq.com/openai/v1",
        api_key=api_key,
    )
    resp = client.chat.completions.create(
        model=config.GROQ_LLM_MODEL,
        messages=[{"role": "user", "content": _POLISH_PROMPT.format(raw=raw)}],
        max_tokens=500,
        temperature=0.1,
    )
    return resp.choices[0].message.content.strip()


# ── LLM 백엔드 3: Claude (유료, 최고 품질) ────────────────────────────────────

def _polish_claude(raw: str) -> str:
    """Anthropic Claude API로 텍스트 교정."""
    api_key = config.ANTHROPIC_API_KEY
    if not api_key:
        raise ValueError(
            "ANTHROPIC_API_KEY가 설정되지 않았습니다.\n"
            ".env에 ANTHROPIC_API_KEY=sk-ant-... 입력"
        )

    from anthropic import Anthropic
    client = Anthropic(api_key=api_key)
    msg = client.messages.create(
        model=config.CLAUDE_LLM_MODEL,
        max_tokens=500,
        messages=[{"role": "user", "content": _POLISH_PROMPT.format(raw=raw)}],
    )
    return msg.content[0].text.strip()
