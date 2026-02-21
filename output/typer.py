# output/typer.py — 현재 커서 위치에 텍스트 붙여넣기

import platform
import time

import pyperclip
import pyautogui

import config

PLATFORM = platform.system()  # 'Windows' | 'Linux' | 'Darwin'

# pyautogui 안전장치 비활성화 (마우스 구석 이동 시 중단 방지)
pyautogui.FAILSAFE = False
pyautogui.PAUSE    = 0.0


def type_at_cursor(text: str):
    """
    인식된 텍스트를 현재 키보드 커서 위치에 붙여넣습니다.

    방식: 클립보드에 복사 → Ctrl+V 붙여넣기
    한글을 직접 타이핑하면 IME 문제로 깨지므로 클립보드 방식을 사용합니다.
    """
    if not text:
        return

    to_paste = text + (" " if config.TYPER_TRAILING_SPACE else "")

    # 기존 클립보드 내용 백업
    try:
        prev_clipboard = pyperclip.paste()
    except Exception:
        prev_clipboard = ""

    try:
        pyperclip.copy(to_paste)
        time.sleep(0.05)  # 클립보드 반영 대기

        if PLATFORM == "Darwin":
            pyautogui.hotkey("command", "v")
        else:
            pyautogui.hotkey("ctrl", "v")

        time.sleep(0.05)
    finally:
        # 클립보드 복원 (붙여넣기가 끝난 후)
        try:
            pyperclip.copy(prev_clipboard)
        except Exception:
            pass
