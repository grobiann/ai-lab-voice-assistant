# output/typer.py — 현재 커서 위치에 텍스트 입력

import platform
import subprocess
import time

import config

PLATFORM = platform.system()  # 'Windows' | 'Linux' | 'Darwin'


def type_at_cursor(text: str):
    """
    인식된 텍스트를 현재 키보드 커서 위치에 입력합니다.
    클립보드 저장은 overlay.set_clipboard()에서 이미 완료된 상태로 호출됩니다.

    시도 순서:
      1. pynput keyboard.type()  — 한글 Unicode 직접 키 이벤트
      2. xdotool type            — Linux X11 대안
      3. Ctrl+V                  — 클립보드에서 붙여넣기 (이미 저장되어 있음)
    """
    if not text:
        return

    to_type = text + (" " if config.TYPER_TRAILING_SPACE else "")

    # 단축키 릴리스 후 포커스가 이전 창으로 돌아올 시간을 줌
    time.sleep(0.2)

    if _try_pynput(to_type):
        return
    if PLATFORM == "Linux" and _try_xdotool(to_type):
        return
    _try_paste()  # 클립보드는 이미 저장됨 — Ctrl+V 만 전송


# ── 방법 1: pynput ──────────────────────────────────────────────────────────────

def _try_pynput(text: str) -> bool:
    try:
        from pynput.keyboard import Controller
        kb = Controller()
        kb.type(text)
        print("[Typer] pynput 입력 성공")
        return True
    except Exception as e:
        print(f"[Typer] pynput 실패: {e}")
        return False


# ── 방법 2: xdotool (Linux 전용) ────────────────────────────────────────────────

def _try_xdotool(text: str) -> bool:
    try:
        result = subprocess.run(
            ["xdotool", "type", "--clearmodifiers", "--delay", "0", "--", text],
            capture_output=True, timeout=5,
        )
        if result.returncode == 0:
            print("[Typer] xdotool 입력 성공")
            return True
        print(f"[Typer] xdotool 실패: {result.stderr.decode().strip()}")
        return False
    except FileNotFoundError:
        return False
    except Exception as e:
        print(f"[Typer] xdotool 오류: {e}")
        return False


# ── 방법 3: Ctrl+V (클립보드는 overlay에서 이미 저장됨) ─────────────────────────

def _try_paste() -> bool:
    try:
        from pynput.keyboard import Controller, Key
        kb = Controller()
        with kb.pressed(Key.ctrl):
            kb.press('v')
            kb.release('v')
        time.sleep(0.05)
        print("[Typer] Ctrl+V 붙여넣기 시도")
        return True
    except Exception as e:
        print(f"[Typer] Ctrl+V 실패: {e}")
        return False
