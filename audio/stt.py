# audio/stt.py — STT 백엔드 (local / openai / local+llm)

import threading
import numpy as np

import config

# ── 로컬 모델 상태 ─────────────────────────────────────────────────────────────
_local_model      = None
_local_model_lock = threading.Lock()


# ── 공개 API ───────────────────────────────────────────────────────────────────

def load_model():
    """
    앱 시작 시 호출 — STT_MODE가 로컬을 포함할 때만 모델을 미리 로드합니다.
    """
    if config.STT_MODE in ("local", "local+llm"):
        _ensure_local_model()
    else:
        print(f"[STT] 모드: {config.STT_MODE} — 로컬 모델 불필요")


def transcribe(audio: np.ndarray, status_cb=None) -> str:
    """
    float32 numpy 배열(16kHz mono)을 텍스트로 변환합니다.

    status_cb: callable(str) — 처리 단계를 UI에 표시할 콜백 (선택)
    반환값: 인식된 텍스트 (공백 포함), 실패 시 빈 문자열
    """
    if audio is None or len(audio) == 0:
        return ""

    mode = config.STT_MODE

    try:
        if mode == "local":
            if status_cb: status_cb("Whisper 인식 중...")
            return _transcribe_local(audio)

        elif mode == "openai":
            if status_cb: status_cb("OpenAI API 인식 중...")
            return _transcribe_openai(audio)

        elif mode == "local+llm":
            if status_cb: status_cb("Whisper 인식 중...")
            raw = _transcribe_local(audio)
            print(f"[STT] Whisper 원문: '{raw}'")
            if not raw:
                return ""
            if status_cb: status_cb(f"LLM 교정 중...")
            return _polish_with_llm(raw)

        else:
            print(f"[STT] 알 수 없는 STT_MODE: '{mode}'")
            return ""

    except Exception as e:
        print(f"[STT] 오류 ({mode}): {e}")
        return ""


# ── 방법 1: faster-whisper 로컬 ────────────────────────────────────────────────

def _ensure_local_model():
    global _local_model
    with _local_model_lock:
        if _local_model is not None:
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

        print(f"[STT] faster-whisper '{config.WHISPER_MODEL}' 로딩 "
              f"({device}, {compute})...")
        _local_model = WhisperModel(
            config.WHISPER_MODEL,
            device=device,
            compute_type=compute,
        )
        print("[STT] 로컬 모델 로드 완료")


def _transcribe_local(audio: np.ndarray) -> str:
    _ensure_local_model()
    with _local_model_lock:
        model = _local_model

    segments, _ = model.transcribe(
        audio.astype(np.float32),
        language=config.WHISPER_LANG,
        beam_size=config.WHISPER_BEAM,
        vad_filter=True,          # 무음 구간 자동 제거
        vad_parameters={"min_silence_duration_ms": 300},
    )
    return " ".join(seg.text.strip() for seg in segments).strip()


# ── 방법 2: OpenAI Whisper API ─────────────────────────────────────────────────

def _transcribe_openai(audio: np.ndarray) -> str:
    import io
    import soundfile as sf

    api_key = config.OPENAI_API_KEY
    if not api_key:
        raise ValueError(
            "OPENAI_API_KEY가 비어 있습니다.\n"
            "config.py 또는 환경변수(OPENAI_API_KEY)에 API 키를 설정하세요."
        )

    from openai import OpenAI
    client = OpenAI(api_key=api_key)

    # numpy 배열 → WAV 바이너리 변환
    buf = io.BytesIO()
    sf.write(buf, audio.astype(np.float32), config.SAMPLE_RATE,
             format="wav", subtype="PCM_16")
    buf.seek(0)
    buf.name = "audio.wav"   # OpenAI SDK가 확장자로 포맷 판별

    result = client.audio.transcriptions.create(
        model="whisper-1",
        file=buf,
        language=config.WHISPER_LANG,
    )
    return result.text.strip()


# ── 방법 3: LLM 교정 (faster-whisper 결과를 Claude로 다듬기) ──────────────────────

def _polish_with_llm(raw: str) -> str:
    api_key = config.ANTHROPIC_API_KEY
    if not api_key:
        print("[STT] ANTHROPIC_API_KEY 없음 — LLM 교정 건너뜀, 원문 반환")
        return raw

    try:
        from anthropic import Anthropic
        client = Anthropic(api_key=api_key)

        msg = client.messages.create(
            model=config.LLM_MODEL,
            max_tokens=500,
            messages=[{
                "role": "user",
                "content": (
                    "다음은 음성인식(Whisper) 결과입니다. "
                    "한국어 맞춤법·띄어쓰기·문장 부호를 교정하고 "
                    "자연스러운 구어체 문장으로 다듬어 주세요.\n"
                    "규칙:\n"
                    "- 원문의 내용과 의미를 절대 변경하지 마세요\n"
                    "- 교정된 텍스트만 출력하세요 (설명 없이)\n"
                    "- 내용이 완전하면 그대로 두세요\n\n"
                    f"원문: {raw}"
                ),
            }],
        )
        polished = msg.content[0].text.strip()
        print(f"[STT] LLM 교정: '{raw}' → '{polished}'")
        return polished

    except Exception as e:
        print(f"[STT] LLM 교정 실패: {e} — 원문 반환")
        return raw
