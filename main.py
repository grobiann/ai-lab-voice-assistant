#!/usr/bin/env python3
# main.py — 음성 딕테이션 앱 진입점

import threading
import time

from core.state_machine import StateMachine, State
from audio.recorder     import Recorder
from audio              import stt
from output.typer       import type_at_cursor
from ui.overlay         import Overlay
import config

# ── 전역 컴포넌트 ───────────────────────────────────────────────────────────────
sm            = StateMachine()
recorder      = None
overlay       = None
_model_loaded = False   # 모델 로드 완료 전 토글 입력 차단용 플래그


# ── 토글 핸들러 (버튼 클릭 / 단축키 공통) ───────────────────────────────────────

def on_toggle():
    """IDLE↔RECORDING 전환 또는 RECORDING→PROCESSING 전환."""
    if not _model_loaded:
        return   # 모델 로딩 중 — 무시
    state = sm.state
    if state == State.IDLE:
        sm.to_recording()
    elif state == State.RECORDING:
        sm.to_processing()
    # PROCESSING 중에는 무시


# ── 모델 로드 완료 콜백 ──────────────────────────────────────────────────────────

def _on_model_ready():
    global _model_loaded
    _model_loaded = True
    if overlay:
        overlay.set_loading(False)


# ── 상태 변경 콜백 ───────────────────────────────────────────────────────────────

def on_state_change(prev: State, new: State):
    overlay.set_state(new)

    if new == State.RECORDING:
        recorder.start()

    elif new == State.PROCESSING:
        audio = recorder.stop()
        threading.Thread(
            target=_transcribe_and_type,
            args=(audio,),
            daemon=True,
        ).start()


def _transcribe_and_type(audio):
    """STT 추론 → 클립보드 저장(동기) → 커서 위치 입력 → IDLE 복귀."""
    text = stt.transcribe(audio, status_cb=overlay.set_processing_text)

    if text:
        # 1. 클립보드에 저장 — 완료될 때까지 대기 (동기)
        overlay.set_clipboard_sync(text)
        # 2. 커서 위치에 직접 타이핑 시도
        t_type = time.perf_counter()
        type_at_cursor(text)
        print(f"[Typer] 입력 완료: {time.perf_counter()-t_type:.2f}s")

    overlay.show_result(text)
    sm.to_idle()


# ── 전역 단축키 (pynput keyboard.Listener) ──────────────────────────────────────

def _start_hotkey_listener():
    """
    GlobalHotKeys 대신 keyboard.Listener를 직접 사용.
    GlobalHotKeys의 문자열 파싱이 특수키(space 등)에서 불안정하기 때문.
    """
    try:
        from pynput import keyboard

        ctrl_held = False

        def on_press(key):
            nonlocal ctrl_held
            # Ctrl 눌림 감지
            if key in (keyboard.Key.ctrl_l, keyboard.Key.ctrl_r):
                ctrl_held = True
                return
            # Ctrl + Space 조합 감지
            if ctrl_held and key == keyboard.Key.space:
                on_toggle()

        def on_release(key):
            nonlocal ctrl_held
            if key in (keyboard.Key.ctrl_l, keyboard.Key.ctrl_r):
                ctrl_held = False

        print("[Hotkey] Ctrl+Space 리스너 시작")
        with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
            listener.join()

    except Exception as e:
        print(f"[Hotkey] 단축키 리스너 오류: {e}")
        print("[Hotkey] 단축키 없이 버튼만 사용 가능합니다.")


# ── 시작 ────────────────────────────────────────────────────────────────────────

def main():
    global recorder, overlay

    print("=" * 50)
    print("  Voice Typer — 음성 딕테이션 도구")
    print("=" * 50)
    _TIER_LABELS = {
        "tier1": f"1단계 — 빠른 응답 (faster-whisper {config.TIER1_MODEL})",
        "tier2": f"2단계 — 균형 (faster-whisper {config.TIER2_MODEL})",
        "tier3": f"3단계 — 최고 정밀도 ({config.TIER3_MODEL} + {config.LLM_BACKEND} 교정)",
        "cloud": "클라우드 (OpenAI Whisper API)",
    }
    _TIER_MODELS = {
        "tier1": config.TIER1_MODEL,
        "tier2": config.TIER2_MODEL,
        "tier3": config.TIER3_MODEL,
    }
    tier_label = _TIER_LABELS.get(config.STT_MODE, config.STT_MODE)
    print(f"  단축키: Ctrl+Space  |  종료: 오버레이 × 버튼")
    print(f"  STT: {tier_label}")
    if config.STT_MODE in _TIER_MODELS:
        print(f"  모델: {_TIER_MODELS[config.STT_MODE]}  언어: {config.WHISPER_LANG}")
    print("=" * 50)

    recorder = Recorder(on_level=lambda lvl: overlay.update_level(lvl) if overlay else None)
    sm.on_change(on_state_change)

    overlay = Overlay(on_toggle=on_toggle)

    # overlay 생성 후 로딩 시작 — 콜백이 overlay에 안전하게 전달됨
    threading.Thread(
        target=lambda: stt.load_model(on_ready=_on_model_ready),
        daemon=True,
    ).start()

    threading.Thread(target=_start_hotkey_listener, daemon=True).start()

    overlay.run()


if __name__ == "__main__":
    main()
