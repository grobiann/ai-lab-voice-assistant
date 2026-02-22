# ui/overlay.py — 항상 맨 위 플로팅 오버레이 (tkinter)

import threading
import tkinter as tk

from core.state_machine import State
import config

# ── 색상 팔레트 ─────────────────────────────────────────────────────────────────
C_BG        = "#1e1e1e"
C_IDLE      = "#888888"
C_REC       = "#e05555"
C_PROC      = "#f0c040"
C_RESULT    = "#7ec8e3"
C_LEVEL_BG  = "#333333"
C_LEVEL_FG  = "#55dd88"
C_BTN_REC   = "#c0392b"
C_BTN_STOP  = "#888888"
C_BTN_FG    = "#ffffff"
C_BORDER    = "#444444"
C_CLOSE     = "#555555"
C_MODE      = "#666666"   # STT 모드 레이블 색상


def _mode_display_name(mode=None):
    """STT 모드 문자열 → 오버레이에 표시할 짧은 이름."""
    m = mode if mode is not None else config.STT_MODE
    if m == "cloud_google":
        return "Google STT"
    return f"로컬 Whisper ({config.WHISPER_MODEL})"


class Overlay:
    """
    tkinter 기반 항상-위 플로팅 오버레이 창.
    다른 스레드에서 모든 공개 메서드를 안전하게 호출할 수 있습니다.
    """

    def __init__(self, on_toggle: callable):
        self._on_toggle    = on_toggle
        self._root         = None
        self._level        = 0
        self._blink_on     = False
        self._model_ready  = False   # 모델 로드 완료 여부 (스레드 안전 플래그)
        self._mode_text    = _mode_display_name()   # 초기 STT 모드 표시

    # ── 공개 API (스레드 안전) ───────────────────────────────────────────────────

    def set_loading(self, is_loading: bool):
        """
        모델 로딩 상태 전환 — 백그라운드 스레드에서 호출 가능.
        is_loading=False: '준비 완료' 표시 후 2초 뒤 정상 대기 상태로 전환.
        """
        if not is_loading:
            self._model_ready = True   # _root가 없어도 플래그 먼저 설정
        if self._root:
            if is_loading:
                self._root.after(0, self._show_loading)
            else:
                self._root.after(0, self._show_ready)

    def update_level(self, level: int):
        self._level = level
        if self._root:
            self._root.after(0, self._draw_level)

    def set_state(self, state: State):
        if self._root:
            self._root.after(0, lambda: self._apply_state(state))

    def show_result(self, text: str):
        if self._root:
            self._root.after(0, lambda: self._display_result(text))

    def set_processing_text(self, text: str):
        """처리 단계 텍스트 업데이트 — 아무 스레드에서 호출 가능 (PROCESSING 상태 중)."""
        if self._root:
            self._root.after(0, lambda: self._lbl_text.config(text=text, fg=C_PROC))

    def set_mode_label(self, text: str):
        """현재 STT 모드 레이블 업데이트 — 어느 스레드에서 호출해도 안전."""
        self._mode_text = text
        if self._root:
            self._root.after(0, lambda: self._lbl_mode.config(text=text))

    def set_clipboard_sync(self, text: str, timeout: float = 1.0):
        """
        tkinter 클립보드에 저장하고 완료될 때까지 대기 (동기 호출).
        백그라운드 스레드에서 호출해도 안전 — threading.Event로 완료 대기.
        """
        if not self._root:
            return
        done = threading.Event()

        def do_set():
            try:
                self._root.clipboard_clear()
                self._root.clipboard_append(text)
                print(f"[Clipboard] 저장 완료: '{text[:40]}{'...' if len(text) > 40 else ''}'")
            except Exception as e:
                print(f"[Clipboard] 저장 실패: {e}")
            finally:
                done.set()

        self._root.after(0, do_set)
        done.wait(timeout=timeout)

    # ── 메인 루프 ────────────────────────────────────────────────────────────────

    def run(self):
        """tkinter 메인 루프 — 메인 스레드에서 호출해야 합니다."""
        root = tk.Tk()
        self._root = root

        root.title("Voice Typer")
        root.configure(bg=C_BG)
        root.resizable(False, False)
        root.attributes("-topmost", True)
        root.attributes("-alpha", 0.93)
        root.overrideredirect(True)

        self._build_ui(root)
        self._position_bottom_right(root)
        self._make_draggable(root)

        # 모델이 이미 로드됐으면(cloud 모드 등) 바로 IDLE, 아니면 로딩 표시
        if self._model_ready:
            root.after(100, lambda: self._apply_state(State.IDLE))
        else:
            root.after(100, self._show_loading)
        root.mainloop()

    # ── UI 빌드 ──────────────────────────────────────────────────────────────────

    def _build_ui(self, root: tk.Tk):
        W = config.OVERLAY_WIDTH

        outer = tk.Frame(root, bg=C_BORDER, padx=1, pady=1)
        outer.pack(fill=tk.BOTH, expand=True)

        inner = tk.Frame(outer, bg=C_BG, padx=12, pady=8)
        inner.pack(fill=tk.BOTH, expand=True)

        # ─ 상단 행: 상태 + 레벨 미터 + 시작/중지 버튼 + × 종료 버튼 ─
        top = tk.Frame(inner, bg=C_BG)
        top.pack(fill=tk.X)

        self._lbl_status = tk.Label(
            top, text="● 대기", fg=C_IDLE, bg=C_BG,
            font=("Segoe UI", 10, "bold"), width=9, anchor="w",
        )
        self._lbl_status.pack(side=tk.LEFT)

        self._canvas_level = tk.Canvas(
            top, width=W - 190, height=14,
            bg=C_LEVEL_BG, highlightthickness=0,
        )
        self._canvas_level.pack(side=tk.LEFT, padx=(4, 8))

        # × 종료 버튼 (맨 오른쪽)
        btn_close = tk.Button(
            top, text="×",
            bg=C_CLOSE, fg="#aaaaaa",
            activebackground="#c0392b", activeforeground="#ffffff",
            font=("Segoe UI", 11, "bold"),
            relief=tk.FLAT, padx=6, pady=0, cursor="hand2",
            command=self._quit,
        )
        btn_close.pack(side=tk.RIGHT, padx=(4, 0))

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

        # ─ 모드 행: 현재 STT 엔진 표시 ─
        self._lbl_mode = tk.Label(
            inner, text=self._mode_text,
            fg=C_MODE, bg=C_BG,
            font=("Segoe UI", 8),
            anchor="w",
        )
        self._lbl_mode.pack(fill=tk.X, pady=(3, 0))

        # ─ 하단 행: 텍스트 결과 ─
        self._lbl_text = tk.Label(
            inner, text="Ctrl+Space 또는 버튼을 눌러 시작",
            fg=C_IDLE, bg=C_BG,
            font=("Segoe UI", 9),
            wraplength=W - 30, justify=tk.LEFT, anchor="w",
        )
        self._lbl_text.pack(fill=tk.X, pady=(3, 0))

    # ── 상태별 UI 업데이트 ────────────────────────────────────────────────────────

    def _show_loading(self):
        """앱 시작 시 모델 로딩 중 표시 — 버튼 비활성화."""
        self._blink_on = False
        self._lbl_status.config(text="◌ 로딩 중", fg=C_PROC)
        self._btn.config(text="대기", bg=C_BTN_STOP, state=tk.DISABLED)
        self._lbl_text.config(text="모델 로딩 중... 잠시만 기다려 주세요", fg=C_PROC)
        self._draw_level(force_zero=True)

    def _show_ready(self):
        """모델 로드 완료 시 '준비 완료' 표시 후 IDLE로 전환."""
        self._lbl_status.config(text="● 준비 완료", fg=C_LEVEL_FG)
        self._btn.config(text="시작", bg=C_BTN_REC, state=tk.NORMAL)
        self._lbl_text.config(text="준비됐습니다! Ctrl+Space 또는 버튼을 눌러 시작", fg=C_LEVEL_FG)
        self._root.after(2000, lambda: self._apply_state(State.IDLE))

    def _apply_state(self, state: State):
        if state == State.IDLE:
            self._blink_on = False
            self._lbl_status.config(text="● 대기", fg=C_IDLE)
            self._btn.config(text="시작", bg=C_BTN_REC, state=tk.NORMAL)
            self._draw_level(force_zero=True)

        elif state == State.RECORDING:
            self._lbl_status.config(text="● REC", fg=C_REC)
            self._btn.config(text="중지", bg=C_BTN_STOP, state=tk.NORMAL)
            self._lbl_text.config(text="말씀하세요...", fg=C_IDLE)
            self._blink_start()

        elif state == State.PROCESSING:
            self._blink_on = False
            self._lbl_status.config(text="◌ 인식 중", fg=C_PROC)
            self._btn.config(text="대기", bg=C_BTN_STOP, state=tk.DISABLED)
            self._lbl_text.config(text="인식 중...", fg=C_PROC)
            self._draw_level(force_zero=True)

    def _display_result(self, text: str):
        self._btn.config(state=tk.NORMAL)
        if text:
            self._lbl_text.config(text=f'"{text}"', fg=C_RESULT)
        else:
            self._lbl_text.config(text="(인식된 텍스트 없음)", fg=C_IDLE)
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
            color = C_LEVEL_FG if level < 60 else ("#f0c040" if level < 85 else "#e05555")
            c.create_rectangle(0, 0, fill_w, h, fill=color, outline="", tags="bar")

    # ── 녹음 중 깜빡임 ────────────────────────────────────────────────────────────

    def _blink_start(self):
        self._blink_on = True
        self._blink_tick()

    def _blink_tick(self):
        if not self._blink_on:
            self._lbl_status.config(fg=C_REC)  # 꺼질 때 색 복원
            return
        cur     = self._lbl_status.cget("fg")
        next_fg = C_BG if cur == C_REC else C_REC
        self._lbl_status.config(fg=next_fg)
        self._root.after(600, self._blink_tick)

    # ── 종료 ─────────────────────────────────────────────────────────────────────

    def _quit(self):
        print("[Overlay] 앱 종료")
        self._root.quit()
        self._root.destroy()

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
            root.geometry(f"+{root.winfo_x() + dx}+{root.winfo_y() + dy}")

        root.bind("<ButtonPress-1>", on_press)
        root.bind("<B1-Motion>",     on_drag)

    # ── 위치 설정 ─────────────────────────────────────────────────────────────────

    def _position_bottom_right(self, root: tk.Tk):
        root.update_idletasks()
        sw = root.winfo_screenwidth()
        sh = root.winfo_screenheight()
        x  = sw - root.winfo_width() - 20
        y  = sh - root.winfo_height() - 60
        root.geometry(f"+{x}+{y}")
