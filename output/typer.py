# output/typer.py — 현재 커서 위치에 텍스트 입력

import platform
import subprocess
import time

import config

PLATFORM = platform.system()  # 'Windows' | 'Linux' | 'Darwin'


def type_at_cursor(text: str):
    """
    인식된 텍스트를 현재 키보드 커서 위치에 입력합니다.

    시도 순서:
      1. pynput keyboard.type()   — 한글 Unicode 직접 키 이벤트 (가장 안정적)
      2. xdotool type             — Linux X11 대안
      3. 클립보드 + Ctrl+V         — 최후 수단
    """
    if not text:
        return

    to_type = text + (" " if config.TYPER_TRAILING_SPACE else "")

    # 단축키 릴리스 후 포커스가 이전 창으로 돌아올 시간을 줌
    time.sleep(0.15)

    if _try_pynput(to_type):
        return
    if PLATFORM == "Linux" and _try_xdotool(to_type):
        return
    _try_clipboard(to_type)


# ── 방법 1: pynput ──────────────────────────────────────────────────────────────

def _try_pynput(text: str) -> bool:
    try:
        from pynput.keyboard import Controller
        kb = Controller()
        kb.type(text)
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
            return True
        print(f"[Typer] xdotool 실패: {result.stderr.decode().strip()}")
        return False
    except FileNotFoundError:
        return False  # xdotool 미설치
    except Exception as e:
        print(f"[Typer] xdotool 오류: {e}")
        return False


# ── 방법 3: 클립보드 + Ctrl+V ───────────────────────────────────────────────────

def _try_clipboard(text: str) -> bool:
    """클립보드에 복사 후 Ctrl+V 붙여넣기."""
    try:
        _set_clipboard(text)
        time.sleep(0.08)

        from pynput.keyboard import Controller, Key
        kb = Controller()
        with kb.pressed(Key.ctrl):
            kb.press('v')
            kb.release('v')
        time.sleep(0.05)
        return True
    except Exception as e:
        print(f"[Typer] 클립보드 방식 실패: {e}")
        return False


def _set_clipboard(text: str):
    """플랫폼별 클립보드 설정."""
    # Linux: xclip → xsel → pyperclip 순으로 시도
    if PLATFORM == "Linux":
        for cmd in (["xclip", "-selection", "clipboard"],
                    ["xsel", "--clipboard", "--input"]):
            try:
                subprocess.run(cmd, input=text.encode("utf-8"),
                               capture_output=True, timeout=3, check=True)
                return
            except (FileNotFoundError, subprocess.CalledProcessError):
                continue

    # 공통 fallback: pyperclip
    import pyperclip
    pyperclip.copy(text)
