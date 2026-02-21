# audio/stt.py — STT 백엔드 (tier1 / tier2 / tier3 / cloud)

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
       '아이폰' → 'iPhone', '챗지피티' → 'ChatGPT'
3. 영어 단어는 문맥에 맞게 영문 또는 한글 외래어 표기로 통일하세요.
4. 원문의 내용·의미를 절대 변경하지 마세요.
5. 이미 올바른 문장이면 그대로 반환하세요.

원문: {raw}"""


# ── 공개 API ───────────────────────────────────────────────────────────────────

def load_model():
    """
    앱 시작 시 호출 — tier1/2/3는 로컬 Whisper 모델을 미리 로드합니다.
    """
    if config.STT_MODE in ("tier1", "tier2", "tier3"):
        _ensure_local_model()
    else:
        print(f"[STT] 모드: {config.STT_MODE} — 로컬 Whisper 불필요")


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
        if mode == "tier1":
            if status_cb: status_cb("1단계 인식 중...")
            return _transcribe_local(audio)

        elif mode == "tier2":
            if status_cb: status_cb("2단계 인식 중...")
            return _transcribe_local(audio)

        elif mode == "tier3":
            if status_cb: status_cb("3단계 인식 중...")
            raw = _transcribe_local(audio)
            print(f"[STT] Whisper 원문: '{raw}'")
            if not raw:
                return ""
            backend = config.LLM_BACKEND.lower()
            if status_cb: status_cb(f"3단계 교정 중... ({backend})")
            return _polish_with_llm(raw)

        elif mode == "cloud":
            if status_cb: status_cb("클라우드 인식 중...")
            return _transcribe_openai(audio)

        else:
            print(f"[STT] 알 수 없는 STT_MODE: '{mode}'  (tier1/tier2/tier3/cloud)")
            return ""

    except Exception as e:
        print(f"[STT] 오류 ({mode}): {e}")
        return ""


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
    target = _tier_model_name()

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
        _local_model = WhisperModel(target, device=device, compute_type=compute)
        _local_model_name = target
        print("[STT] 로컬 모델 로드 완료")


def _transcribe_local(audio: np.ndarray) -> str:
    _ensure_local_model()
    with _local_model_lock:
        model = _local_model

    # initial_prompt: 한영 혼합 발화 인식률 향상
    prompt = config.WHISPER_INITIAL_PROMPT or None

    segments, _ = model.transcribe(
        audio.astype(np.float32),
        language=config.WHISPER_LANG,
        beam_size=config.WHISPER_BEAM,
        initial_prompt=prompt,
        vad_filter=True,
        vad_parameters={"min_silence_duration_ms": 300},
    )
    return " ".join(seg.text.strip() for seg in segments).strip()


# ── cloud 백엔드 (OpenAI Whisper API) ──────────────────────────────────────────

def _transcribe_openai(audio: np.ndarray) -> str:
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
    polished = resp.choices[0].message.content.strip()
    print(f"[STT] Ollama 교정 ({config.OLLAMA_MODEL}): '{raw}' → '{polished}'")
    return polished


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
    polished = resp.choices[0].message.content.strip()
    print(f"[STT] Groq 교정 ({config.GROQ_LLM_MODEL}): '{raw}' → '{polished}'")
    return polished


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
    polished = msg.content[0].text.strip()
    print(f"[STT] Claude 교정: '{raw}' → '{polished}'")
    return polished
