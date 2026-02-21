# ui/overlay.py — 항상 맨 위 플로팅 오버레이 (tkinter)

import tkinter as tk
from tkinter import font as tkfont

from core.state_machine import State
import config

# ── 색상 팔레트 ─────────────────────────────────────────────────────────────────
C_BG        = "#1e1e1e"   # 배경
C_FG        = "#f0f0f0"   # 기본 텍스트
C_IDLE      = "#888888"   # 대기 상태 표시
C_REC       = "#e05555"   # 녹음 중 (빨간색)
C_PROC      = "#f0c040"   # 처리 중 (노란색)
C_RESULT    = "#7ec8e3"   # 인식 결과 텍스트 (하늘색)
C_LEVEL_BG  = "#333333"   # 레벨 미터 배경
C_LEVEL_FG  = "#55dd88"   # 레벨 미터 바 (초록)
C_BTN_REC   = "#c0392b"   # 녹음 버튼
C_BTN_STOP  = "#888888"   # 중지 버튼
C_BTN_FG    = "#ffffff"   # 버튼 텍스트
C_BORDER    = "#444444"   # 테두리


class Overlay:
    """
    tkinter 기반 항상-위 플로팅 오버레이 창.

    다른 스레드에서 update_level() / set_state() / show_result()를
    안전하게 호출할 수 있습니다 (root.after 스케줄링 사용).
    """

    def __init__(self, on_toggle: callable):
        """
        on_toggle: 버튼 클릭 또는 단축키 입력 시 호출되는 콜백
        """
        self._on_toggle = on_toggle
        self._root      = None
        self._level     = 0
        self._blink_on  = False

    # ── 공개 API (스레드 안전) ───────────────────────────────────────────────────

    def update_level(self, level: int):
        """오디오 레벨(0~100) 업데이트 — 아무 스레드에서 호출 가능."""
        self._level = level
        if self._root:
            self._root.after(0, self._draw_level)

    def set_state(self, state: State):
        """상태 변경 시 UI 갱신 — 아무 스레드에서 호출 가능."""
        if self._root:
            self._root.after(0, lambda: self._apply_state(state))

    def show_result(self, text: str):
        """인식 결과 텍스트 표시 후 일정 시간 뒤 초기화 — 아무 스레드에서 호출 가능."""
        if self._root:
            self._root.after(0, lambda: self._display_result(text))

    # ── 메인 루프 ────────────────────────────────────────────────────────────────

    def run(self):
        """tkinter 메인 루프 — 메인 스레드에서 호출해야 합니다."""
        root = tk.Tk()
        self._root = root

        root.title("Voice Typer")
        root.configure(bg=C_BG)
        root.resizable(False, False)
        root.attributes("-topmost", True)       # 항상 맨 위
        root.attributes("-alpha", 0.93)         # 약간 투명
        root.overrideredirect(True)             # 타이틀바 제거

        self._build_ui(root)
        self._position_bottom_right(root)
        self._make_draggable(root)

        # 레벨 미터 초기 렌더
        root.after(100, lambda: self._apply_state(State.IDLE))

        root.mainloop()

    # ── UI 빌드 ──────────────────────────────────────────────────────────────────

    def _build_ui(self, root: tk.Tk):
        W = config.OVERLAY_WIDTH

        # 외곽 프레임 (테두리)
        outer = tk.Frame(root, bg=C_BORDER, padx=1, pady=1)
        outer.pack(fill=tk.BOTH, expand=True)

        inner = tk.Frame(outer, bg=C_BG, padx=12, pady=8)
        inner.pack(fill=tk.BOTH, expand=True)

        # ─ 상단 행: 상태 표시 + 레벨 미터 + 버튼 ─
        top = tk.Frame(inner, bg=C_BG)
        top.pack(fill=tk.X)

        # 상태 레이블 (● IDLE / ● REC / ◌ 인식 중)
        self._lbl_status = tk.Label(
            top, text="● 대기", fg=C_IDLE, bg=C_BG,
            font=("Segoe UI", 10, "bold"), width=9, anchor="w",
        )
        self._lbl_status.pack(side=tk.LEFT)

        # 레벨 미터 (Canvas)
        self._canvas_level = tk.Canvas(
            top, width=W - 160, height=14,
            bg=C_LEVEL_BG, highlightthickness=0,
        )
        self._canvas_level.pack(side=tk.LEFT, padx=(4, 8))

        # 시작/중지 버튼
        self._btn = tk.Button(
            top, text="시작",
            bg=C_BTN_REC, fg=C_BTN_FG,
            activebackground="#a93226", activeforeground=C_BTN_FG,
            font=("Segoe UI", 9, "bold"),
            relief=tk.FLAT, padx=10, pady=2, cursor="hand2",
            command=self._on_toggle,
        )
        self._btn.pack(side=tk.RIGHT)

        # ─ 하단 행: 텍스트 결과 ─
        self._lbl_text = tk.Label(
            inner, text="Ctrl+Space 또는 버튼을 눌러 시작",
            fg=C_IDLE, bg=C_BG,
            font=("Segoe UI", 9),
            wraplength=W - 30, justify=tk.LEFT, anchor="w",
        )
        self._lbl_text.pack(fill=tk.X, pady=(6, 0))

    # ── 상태별 UI 업데이트 ────────────────────────────────────────────────────────

    def _apply_state(self, state: State):
        if state == State.IDLE:
            self._lbl_status.config(text="● 대기", fg=C_IDLE)
            self._btn.config(text="시작", bg=C_BTN_REC)
            self._draw_level(force_zero=True)

        elif state == State.RECORDING:
            self._lbl_status.config(text="● REC", fg=C_REC)
            self._btn.config(text="중지", bg=C_BTN_STOP)
            self._lbl_text.config(text="말씀하세요...", fg=C_IDLE)
            self._blink_start()

        elif state == State.PROCESSING:
            self._lbl_status.config(text="◌ 인식 중", fg=C_PROC)
            self._btn.config(text="대기", bg=C_BTN_STOP, state=tk.DISABLED)
            self._lbl_text.config(text="인식 중...", fg=C_PROC)
            self._draw_level(force_zero=True)

    def _display_result(self, text: str):
        self._btn.config(state=tk.NORMAL)
        if text:
            self._lbl_text.config(
                text=f'"{text}"', fg=C_RESULT,
            )
        else:
            self._lbl_text.config(text="(인식된 텍스트 없음)", fg=C_IDLE)
        # 일정 시간 후 안내 문구로 복귀
        self._root.after(config.OVERLAY_RESULT_MS, self._reset_text)

    def _reset_text(self):
        self._lbl_text.config(
            text="Ctrl+Space 또는 버튼을 눌러 시작", fg=C_IDLE,
        )

    # ── 레벨 미터 ────────────────────────────────────────────────────────────────

    def _draw_level(self, force_zero=False):
        c     = self._canvas_level
        level = 0 if force_zero else self._level
        w     = c.winfo_width()
        h     = c.winfo_height()
        if w <= 1:
            return
        fill_w = int(w * level / 100)
        c.delete("bar")
        if fill_w > 0:
            # 색상: 낮으면 초록, 높으면 노란→빨간
            if level < 60:
                color = C_LEVEL_FG
            elif level < 85:
                color = "#f0c040"
            else:
                color = "#e05555"
            c.create_rectangle(0, 0, fill_w, h, fill=color, outline="", tags="bar")

    # ── 녹음 중 깜빡임 ────────────────────────────────────────────────────────────

    def _blink_start(self):
        self._blink_on = True
        self._blink_tick()

    def _blink_tick(self):
        if not self._blink_on:
            return
        cur = self._lbl_status.cget("fg")
        next_fg = C_BG if cur == C_REC else C_REC
        self._lbl_status.config(fg=next_fg)
        self._root.after(600, self._blink_tick)

    def _blink_stop(self):
        self._blink_on = False

    # ── 창 드래그 ────────────────────────────────────────────────────────────────

    def _make_draggable(self, root: tk.Tk):
        self._drag_x = 0
        self._drag_y = 0

        def on_press(e):
            self._drag_x = e.x
            self._drag_y = e.y

        def on_drag(e):
            dx = e.x - self._drag_x
            dy = e.y - self._drag_y
            x  = root.winfo_x() + dx
            y  = root.winfo_y() + dy
            root.geometry(f"+{x}+{y}")

        root.bind("<ButtonPress-1>",   on_press)
        root.bind("<B1-Motion>",       on_drag)

    # ── 위치 설정 ─────────────────────────────────────────────────────────────────

    def _position_bottom_right(self, root: tk.Tk):
        root.update_idletasks()
        sw = root.winfo_screenwidth()
        sh = root.winfo_screenheight()
        ww = root.winfo_width()
        wh = root.winfo_height()
        x  = sw - ww - 20
        y  = sh - wh - 60
        root.geometry(f"+{x}+{y}")
