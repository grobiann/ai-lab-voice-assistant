# ui/tray.py — 시스템 트레이 아이콘 (pystray + Pillow)

import threading

import pystray
from PIL import Image, ImageDraw

from core.state_machine import State


# ── 아이콘 이미지 생성 ────────────────────────────────────────────────────────────

def _make_icon(state: State = State.IDLE, loading: bool = False) -> Image.Image:
    """상태에 따라 마이크 모양 트레이 아이콘 생성 (64×64 RGBA)."""
    size = 64
    img  = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d    = ImageDraw.Draw(img)

    if loading:
        color = "#888888"
    elif state == State.RECORDING:
        color = "#e05555"
    elif state == State.PROCESSING:
        color = "#f0c040"
    else:
        color = "#55dd88"   # IDLE

    # 마이크 몸통 (둥근 사각형)
    d.rounded_rectangle([18, 4, 46, 40], radius=14, fill=color)
    # 스탠드 반원 호
    d.arc([10, 24, 54, 54], start=0, end=180, fill=color, width=5)
    # 중심 기둥
    d.rectangle([29, 52, 35, 60], fill=color)
    # 받침대
    d.rectangle([20, 59, 44, 64], fill=color)

    return img


_STATE_TITLE = {
    State.IDLE:       "Voice Typer",
    State.RECORDING:  "Voice Typer — 녹음 중",
    State.PROCESSING: "Voice Typer — 인식 중",
}


# ── TrayIcon 클래스 ───────────────────────────────────────────────────────────────

class TrayIcon:
    """
    시스템 트레이 아이콘.
    - 상태에 따라 아이콘 색상 변경 (초록 IDLE / 빨강 REC / 노랑 PROC)
    - 우클릭 메뉴: 시작/중지, 종료
    """

    def __init__(self, on_toggle: callable, on_quit: callable):
        self._on_toggle = on_toggle
        self._on_quit   = on_quit
        self._icon: pystray.Icon | None = None

    def run_in_thread(self):
        """백그라운드 데몬 스레드에서 트레이 아이콘 실행."""
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self):
        menu = pystray.Menu(
            pystray.MenuItem("Voice Typer", None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("시작 / 중지  (Ctrl+Space)", lambda _: self._on_toggle()),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("종료", lambda _: self._on_quit()),
        )
        self._icon = pystray.Icon(
            "voice-typer",
            _make_icon(loading=True),
            "Voice Typer — 로딩 중...",
            menu,
        )
        self._icon.run()

    # ── 상태 업데이트 (스레드 안전) ──────────────────────────────────────────────

    def set_loading(self, is_loading: bool):
        if not self._icon:
            return
        if is_loading:
            self._icon.icon  = _make_icon(loading=True)
            self._icon.title = "Voice Typer — 로딩 중..."
        else:
            self._icon.icon  = _make_icon(State.IDLE)
            self._icon.title = "Voice Typer"

    def update_state(self, state: State):
        if not self._icon:
            return
        self._icon.icon  = _make_icon(state)
        self._icon.title = _STATE_TITLE.get(state, "Voice Typer")

    def stop(self):
        if self._icon:
            self._icon.stop()
