#!/usr/bin/env python3
# main.py — 음성 딕테이션 앱 진입점

import threading
import sys

from core.state_machine import StateMachine, State
from audio.recorder     import Recorder
from audio              import stt
from output.typer       import type_at_cursor
from ui.overlay         import Overlay
import config

# ── 전역 컴포넌트 ───────────────────────────────────────────────────────────────
sm       = StateMachine()
recorder = None   # on_toggle 등록 후 생성
overlay  = None


# ── 토글 핸들러 (버튼 클릭 / 단축키 공통) ───────────────────────────────────────

def on_toggle():
    """IDLE↔RECORDING 전환 또는 RECORDING→PROCESSING 전환."""
    state = sm.state

    if state == State.IDLE:
        sm.to_recording()

    elif state == State.RECORDING:
        sm.to_processing()

    # PROCESSING 중에는 무시


# ── 상태 변경 콜백 ───────────────────────────────────────────────────────────────

def on_state_change(prev: State, new: State):
    """StateMachine 상태 변경 시 호출 — 백그라운드 스레드에서 실행될 수 있음."""
    overlay.set_state(new)

    if new == State.RECORDING:
        recorder.start()

    elif new == State.PROCESSING:
        # 녹음 중지 후 별도 스레드에서 Whisper 추론
        audio = recorder.stop()
        threading.Thread(
            target=_transcribe_and_type,
            args=(audio,),
            daemon=True,
        ).start()


def _transcribe_and_type(audio):
    """Whisper 추론 → 클립보드 저장 → 커서 위치에 입력 → IDLE 복귀."""
    text = stt.transcribe(audio)
    print(f"[STT] 인식 결과: '{text}'")

    if text:
        # 1. 항상 클립보드에 저장 (타이핑 성공 여부와 무관)
        overlay.set_clipboard(text)
        # 2. 커서 위치에 직접 타이핑 시도
        type_at_cursor(text)

    overlay.show_result(text)
    sm.to_idle()


# ── 전역 단축키 (pynput) ────────────────────────────────────────────────────────

def _start_hotkey_listener():
    try:
        from pynput import keyboard

        # 단일 문자는 그대로, 특수키 이름(space, enter 등)은 <> 로 감쌈
        key = config.HOTKEY_KEY
        key_part = key if len(key) == 1 else f"<{key}>"
        combo = "+".join(f"<{m}>" for m in sorted(config.HOTKEY_MODIFIERS)) + f"+{key_part}"
        print(f"[Hotkey] 등록: {combo}")

        def on_activate():
            on_toggle()

        with keyboard.GlobalHotKeys({combo: on_activate}):
            # 핫키 리스너는 블로킹 — 데몬 스레드에서 실행
            import time
            while True:
                time.sleep(1)

    except Exception as e:
        print(f"[Hotkey] 단축키 리스너 오류: {e}")
        print("[Hotkey] 단축키 없이 버튼만 사용 가능합니다.")


# ── 시작 ────────────────────────────────────────────────────────────────────────

def main():
    global recorder, overlay

    print("=" * 50)
    print("  Voice Typer — 음성 딕테이션 도구")
    print("=" * 50)
    print(f"  단축키: Ctrl+Space")
    print(f"  Whisper 모델: {config.WHISPER_MODEL}  언어: {config.WHISPER_LANG}")
    print("=" * 50)

    # Whisper 모델을 백그라운드에서 미리 로드 (첫 사용 전 준비)
    threading.Thread(target=stt.load_model, daemon=True).start()

    # Recorder 생성 (레벨 콜백 등록)
    recorder = Recorder(on_level=lambda lvl: overlay.update_level(lvl) if overlay else None)

    # StateMachine 콜백 등록
    sm.on_change(on_state_change)

    # Overlay 생성
    overlay = Overlay(on_toggle=on_toggle)

    # 단축키 리스너 — 데몬 스레드
    hotkey_thread = threading.Thread(target=_start_hotkey_listener, daemon=True)
    hotkey_thread.start()

    # tkinter 메인 루프 (메인 스레드 점유)
    overlay.run()


if __name__ == "__main__":
    main()
