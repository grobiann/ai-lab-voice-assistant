# audio/stt.py — STT 백엔드 (Google Cloud STT + 로컬 Whisper fallback)

import time
import threading
import numpy as np

import config

# ── 로컬 모델 상태 (fallback용) ────────────────────────────────────────────────
_local_model      = None
_local_model_name = None
_local_model_lock = threading.Lock()


# ── 공개 API ───────────────────────────────────────────────────────────────────

def load_model(on_ready=None):
    """
    앱 시작 시 호출 — API 키가 없으면 로컬 Whisper 모델을 미리 로드합니다.
    on_ready: 로드 완료 후 호출할 콜백 (선택)
    """
    import os
    has_key = bool(config.GOOGLE_API_KEY or os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"))
    if has_key:
        print("[STT] Google Cloud STT — API 키 확인됨 (로컬 Whisper fallback 대기)")
    else:
        print("[STT] GOOGLE_API_KEY 없음 — 로컬 Whisper 미리 로드")
        _ensure_local_model()
    if on_ready:
        on_ready()


def transcribe(audio: np.ndarray, status_cb=None, mode_cb=None) -> str:
    """
    float32 numpy 배열(16kHz mono)을 텍스트로 변환합니다.

    status_cb: callable(str) — 처리 단계를 UI에 표시할 콜백 (선택)
    mode_cb:   callable(str) — 실제 사용된 STT 모드 이름을 UI에 전달할 콜백 (선택)
    반환값: 인식된 텍스트 (공백 포함), 실패 시 빈 문자열
    """
    if audio is None or len(audio) == 0:
        return ""

    dur = len(audio) / config.SAMPLE_RATE
    rms = float(np.sqrt(np.mean(audio ** 2))) if len(audio) > 0 else 0.0

    print(f"\n{'═'*54}")
    print(f"[Pipeline] cloud_google  |  오디오 {dur:.1f}s  RMS {rms:.4f}")

    t_start = time.perf_counter()
    text    = ""

    try:
        if status_cb: status_cb("Google STT 인식 중...")
        if mode_cb:   mode_cb("Google STT")
        try:
            text = _transcribe_google(audio)
        except Exception as google_err:
            print(f"[STT] Google STT 실패: {google_err}")
            print("[STT] fallback → 로컬 Whisper")
            if status_cb: status_cb("로컬 STT로 전환 중...")
            if mode_cb:   mode_cb(f"로컬 Whisper ({config.WHISPER_MODEL}) ↩")
            _ensure_local_model()
            text = _transcribe_local(audio)

    except Exception as e:
        print(f"[STT] 오류: {e}")
        return ""

    elapsed = time.perf_counter() - t_start
    print(f"[Pipeline] 총 {elapsed:.2f}s  →  '{text}'")
    print(f"{'═'*54}")
    return text


# ── faster-whisper 로컬 백엔드 (fallback) ─────────────────────────────────────

def _ensure_local_model():
    global _local_model, _local_model_name
    target    = config.WHISPER_MODEL
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

    if do_warmup:
        _warmup(_local_model)


def _warmup(model) -> None:
    try:
        dummy = np.zeros(3200, dtype=np.float32)
        list(model.transcribe(dummy, language="ko", beam_size=1)[0])
        print("[STT] GPU 워밍업 완료")
    except Exception as e:
        print(f"[STT] GPU 워밍업 실패 (무시): {e}")


def _transcribe_local(audio: np.ndarray) -> str:
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


# ── Google Cloud Speech-to-Text ────────────────────────────────────────────────

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
