#!/usr/bin/env python3
# main.py — 음성 딕테이션 앱 진입점

import os
import threading
import time
import platform

from core.state_machine import StateMachine, State
from audio.recorder     import Recorder
from audio              import stt
from output.typer       import type_at_cursor
from ui.overlay         import Overlay
from ui.tray            import TrayIcon
import config

# ── 전역 컴포넌트 ───────────────────────────────────────────────────────────────
sm            = StateMachine()
recorder      = None
overlay       = None
tray          = None
_model_loaded = False   # 모델 로드 완료 전 토글 입력 차단용 플래그
_quitting     = False   # 중복 종료 방지 플래그


# ── 앱 종료 ──────────────────────────────────────────────────────────────────────

def do_quit():
    """앱 종료 — 트레이 '종료' / 오버레이 × 버튼 공통 핸들러."""
    global _quitting
    if _quitting:
        return
    _quitting = True
    print("[App] 종료")
    if tray:
        tray.stop()
    if overlay and overlay._root:
        overlay._root.after(0, _destroy_overlay)


def _destroy_overlay():
    try:
        overlay._root.quit()
        overlay._root.destroy()
    except Exception:
        pass


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
    if tray:
        tray.set_loading(False)


# ── 상태 변경 콜백 ───────────────────────────────────────────────────────────────

def on_state_change(prev: State, new: State):
    overlay.set_state(new)
    if tray:
        tray.update_state(new)

    if new == State.RECORDING:
        overlay.show()   # 녹음 시작 시 오버레이 표시
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
    text = stt.transcribe(audio, status_cb=overlay.set_processing_text, mode_cb=overlay.set_mode_label)

    if text:
        # 1. 클립보드에 저장 — 완료될 때까지 대기 (동기)
        overlay.set_clipboard_sync(text)
        # 2. 커서 위치에 직접 타이핑 시도
        t_type = time.perf_counter()
        type_at_cursor(text)
        print(f"[Typer] 입력 완료: {time.perf_counter()-t_type:.2f}s")

    overlay.show_result(text)
    sm.to_idle()
    # 오버레이는 OVERLAY_RESULT_MS 뒤 _reset_text() → 자동 숨김


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


# ── 자동 시작 등록 ────────────────────────────────────────────────────────────────

def _setup_autostart():
    """OS 시작 시 Voice Typer 자동 실행 등록 (이미 등록된 경우 건너뜀)."""
    app_name = "VoiceTyper"
    base_dir = os.path.dirname(os.path.abspath(__file__))

    try:
        if platform.system() == "Windows":
            import winreg
            run_vbs  = os.path.join(base_dir, "run.vbs")
            cmd      = f'wscript.exe "{run_vbs}"'
            key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER, key_path, 0,
                winreg.KEY_READ | winreg.KEY_WRITE,
            ) as key:
                try:
                    existing, _ = winreg.QueryValueEx(key, app_name)
                    if existing == cmd:
                        return   # 이미 등록됨
                except FileNotFoundError:
                    pass
                winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, cmd)
            print("[AutoStart] Windows 시작 프로그램 등록 완료")

        elif platform.system() == "Linux":
            autostart_dir = os.path.expanduser("~/.config/autostart")
            os.makedirs(autostart_dir, exist_ok=True)
            desktop_path  = os.path.join(autostart_dir, "voice-typer.desktop")
            if os.path.exists(desktop_path):
                return
            run_sh  = os.path.join(base_dir, "run.sh")
            content = (
                "[Desktop Entry]\n"
                "Type=Application\n"
                f"Name={app_name}\n"
                f'Exec=bash "{run_sh}"\n'
                "Hidden=false\n"
                "NoDisplay=false\n"
                "X-GNOME-Autostart-enabled=true\n"
            )
            with open(desktop_path, "w") as f:
                f.write(content)
            print("[AutoStart] Linux 자동 시작 등록 완료")

        elif platform.system() == "Darwin":
            plist_dir  = os.path.expanduser("~/Library/LaunchAgents")
            os.makedirs(plist_dir, exist_ok=True)
            plist_path = os.path.join(plist_dir, "com.voicetyper.app.plist")
            if os.path.exists(plist_path):
                return
            run_sh  = os.path.join(base_dir, "run.sh")
            content = (
                '<?xml version="1.0" encoding="UTF-8"?>\n'
                '<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"'
                ' "http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n'
                '<plist version="1.0"><dict>\n'
                '  <key>Label</key>            <string>com.voicetyper.app</string>\n'
                '  <key>ProgramArguments</key> <array>\n'
                '    <string>bash</string>\n'
                f'    <string>{run_sh}</string>\n'
                '  </array>\n'
                '  <key>RunAtLoad</key>        <true/>\n'
                '  <key>KeepAlive</key>        <false/>\n'
                '</dict></plist>\n'
            )
            with open(plist_path, "w") as f:
                f.write(content)
            print("[AutoStart] macOS LaunchAgent 등록 완료")

    except Exception as e:
        print(f"[AutoStart] 등록 실패 (무시): {e}")


# ── 시작 ────────────────────────────────────────────────────────────────────────

def main():
    global recorder, overlay, tray

    print("=" * 50)
    print("  Voice Typer — 음성 딕테이션 도구")
    print("=" * 50)
    print(f"  단축키: Ctrl+Space  |  종료: 트레이 아이콘 → 종료")
    print(f"  기본 STT  : Google Cloud STT  (model: {config.GOOGLE_STT_MODEL})")
    print(f"  Fallback  : 로컬 Whisper      (model: {config.WHISPER_MODEL})")
    print("=" * 50)

    recorder = Recorder(on_level=lambda lvl: overlay.update_level(lvl) if overlay else None)
    sm.on_change(on_state_change)

    tray    = TrayIcon(on_toggle=on_toggle, on_quit=do_quit)
    overlay = Overlay(on_toggle=on_toggle, on_quit=do_quit)

    tray.run_in_thread()

    # overlay 생성 후 로딩 시작 — 콜백이 overlay에 안전하게 전달됨
    threading.Thread(
        target=lambda: stt.load_model(on_ready=_on_model_ready),
        daemon=True,
    ).start()

    threading.Thread(target=_start_hotkey_listener, daemon=True).start()

    _setup_autostart()

    overlay.run()


if __name__ == "__main__":
    main()
