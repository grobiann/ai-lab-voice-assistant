# audio/stt.py — Whisper 로컬 STT

import threading
import numpy as np

import config

# Whisper는 임포트 시 모델을 로드하지 않음 — load_model() 호출 시 로드됨
_model      = None
_model_lock = threading.Lock()


def load_model():
    """
    Whisper 모델을 미리 로드합니다 (앱 시작 시 호출 권장).
    이미 로드된 경우 재로드하지 않습니다.
    """
    global _model
    with _model_lock:
        if _model is not None:
            return

        import whisper
        import torch

        device = config.WHISPER_DEVICE
        if device == "cuda" and not torch.cuda.is_available():
            device = "cpu"

        print(f"[STT] Whisper '{config.WHISPER_MODEL}' 모델 로딩 ({device})...")
        _model = whisper.load_model(config.WHISPER_MODEL, device=device)
        print("[STT] 모델 로드 완료")


def transcribe(audio: np.ndarray) -> str:
    """
    float32 numpy 배열(16kHz mono)을 한국어 텍스트로 변환.

    반환값: 인식된 텍스트 문자열 (공백 제거됨)
            오류 또는 빈 오디오이면 빈 문자열 반환.
    """
    global _model

    if audio is None or len(audio) == 0:
        return ""

    with _model_lock:
        if _model is None:
            load_model()
        model = _model

    try:
        import whisper
        # Whisper는 float32 배열을 직접 받을 수 있음
        audio_fp32 = audio.astype(np.float32)
        result = model.transcribe(
            audio_fp32,
            language=config.WHISPER_LANG,
            fp16=(model.device.type == "cuda"),
        )
        return result.get("text", "").strip()
    except Exception as e:
        print(f"[STT] 추론 오류: {e}")
        return ""
