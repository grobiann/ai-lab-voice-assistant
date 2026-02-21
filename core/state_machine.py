# core/state_machine.py — 앱 상태 관리

import threading
from enum import Enum, auto


class State(Enum):
    IDLE       = auto()   # 대기 중
    RECORDING  = auto()   # 마이크 입력 수집 중
    PROCESSING = auto()   # Whisper 추론 중


class StateMachine:
    """
    스레드 안전한 상태 기계.

    상태 변경 시 등록된 콜백을 메인 스레드가 아닌 변경 스레드에서 호출합니다.
    UI 업데이트는 콜백 내에서 tkinter after()로 스케줄링하세요.
    """

    def __init__(self):
        self._state = State.IDLE
        self._lock  = threading.Lock()
        self._on_change_callbacks: list = []

    # ── 상태 읽기 ───────────────────────────────────────────────────────────────

    @property
    def state(self) -> State:
        with self._lock:
            return self._state

    def is_idle(self)       -> bool: return self.state == State.IDLE
    def is_recording(self)  -> bool: return self.state == State.RECORDING
    def is_processing(self) -> bool: return self.state == State.PROCESSING

    # ── 상태 전환 ───────────────────────────────────────────────────────────────

    def to_recording(self):
        self._transition(State.IDLE, State.RECORDING)

    def to_processing(self):
        self._transition(State.RECORDING, State.PROCESSING)

    def to_idle(self):
        with self._lock:
            prev = self._state
            self._state = State.IDLE
        self._fire(prev, State.IDLE)

    def toggle(self):
        """IDLE → RECORDING 또는 RECORDING → PROCESSING으로 전환."""
        with self._lock:
            cur = self._state
            if cur == State.IDLE:
                self._state = State.RECORDING
                nxt = State.RECORDING
            elif cur == State.RECORDING:
                self._state = State.PROCESSING
                nxt = State.PROCESSING
            else:
                return  # PROCESSING 중에는 토글 무시
        self._fire(cur, nxt)

    def _transition(self, expected: State, next_state: State):
        with self._lock:
            if self._state != expected:
                return
            self._state = next_state
        self._fire(expected, next_state)

    # ── 콜백 ────────────────────────────────────────────────────────────────────

    def on_change(self, callback):
        """callback(prev: State, new: State) 형태로 등록."""
        self._on_change_callbacks.append(callback)

    def _fire(self, prev: State, new: State):
        for cb in self._on_change_callbacks:
            try:
                cb(prev, new)
            except Exception as e:
                print(f"[StateMachine] callback error: {e}")
