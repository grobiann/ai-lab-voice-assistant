# output/typer.py — 현재 커서 위치에 텍스트 입력

import platform
import subprocess
import threading
import time

import config

PLATFORM = platform.system()  # 'Windows' | 'Linux' | 'Darwin'

# ── 이중 입력 방지 ─────────────────────────────────────────────────────────────
# pynput이 한국어 타이핑 중 예외를 던지면 일부 텍스트가 입력된 채 False 반환됨.
# 폴백이 전체 텍스트를 다시 입력하면 "부분 + 전체" 이중 출력 버그가 발생한다.
# → _typing_active 플래그로 재진입을 차단하고, 플랫폼별로 안전한 순서를 사용.
_typing_active      = False
_typing_active_lock = threading.Lock()


def type_at_cursor(text: str):
    """
    인식된 텍스트를 현재 키보드 커서 위치에 입력합니다.
    클립보드 저장은 overlay.set_clipboard()에서 이미 완료된 상태로 호출됩니다.

    플랫폼별 전략:
      Windows / macOS : pynput (SendInput — Unicode 안전)  →  Ctrl+V
      Linux           : xdotool (한국어 안정적)  →  Ctrl+V
                        (pynput은 한국어 중간 예외 시 부분 입력 후 False 반환 →
                         폴백과 겹쳐 이중 출력 버그 유발 — 사용하지 않음)
    """
    global _typing_active

    if not text:
        return

    with _typing_active_lock:
        if _typing_active:
            print("[Typer] 이미 입력 중 — 중복 호출 무시")
            return
        _typing_active = True

    try:
        to_type = text + (" " if config.TYPER_TRAILING_SPACE else "")

        # 단축키 릴리스 후 포커스가 이전 창으로 돌아올 시간을 줌
        time.sleep(0.2)

        if PLATFORM == "Linux":
            # xdotool 이 설치된 경우 우선 사용 (Korean/Unicode 안정)
            if _try_xdotool(to_type):
                return
            # xdotool 없거나 실패 → Ctrl+V (부분 입력 위험 없음)
            _try_paste()

        else:
            # Windows / macOS: pynput SendInput 은 Unicode 안전
            if _try_pynput(to_type):
                return
            _try_paste()

    finally:
        with _typing_active_lock:
            _typing_active = False


# ── 방법 1: pynput ──────────────────────────────────────────────────────────────
# Windows/macOS 전용 — SendInput KEYEVENTF_UNICODE 로 임의 유니코드 입력 가능.
# Linux 에서는 Xlib 경유 시 한국어 중간에 예외 발생 가능 → type_at_cursor 에서 제외.

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
        # xdotool 미설치 — 조용히 False 반환 (Ctrl+V 폴백으로 이어짐)
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
