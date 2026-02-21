# audio/recorder.py — 마이크 녹음 (sounddevice)

import threading
import numpy as np
import sounddevice as sd

import config


class Recorder:
    """
    마이크 오디오를 float32 numpy 배열로 수집.

    - start() 호출 시 녹음 시작
    - stop()  호출 시 녹음 중지 후 전체 오디오 반환
    - on_level 콜백으로 실시간 RMS 레벨(0~100)을 전달
    """

    def __init__(self, on_level=None):
        """
        on_level: callable(level: int) — 실시간 오디오 레벨 콜백 (0~100)
        """
        self._on_level  = on_level
        self._chunks    = []
        self._stream    = None
        self._lock      = threading.Lock()

    # ── Public API ──────────────────────────────────────────────────────────────

    def start(self):
        """녹음 시작. 이미 녹음 중이면 무시."""
        with self._lock:
            if self._stream is not None:
                return
            self._chunks = []
            self._stream = sd.InputStream(
                samplerate=config.SAMPLE_RATE,
                channels=config.CHANNELS,
                dtype='float32',
                device=config.AUDIO_DEVICE,
                blocksize=int(config.SAMPLE_RATE * 0.05),  # 50ms 청크
                callback=self._callback,
            )
            self._stream.start()

    def stop(self) -> np.ndarray:
        """
        녹음 중지.
        반환값: (N,) float32 numpy 배열 (16kHz mono)
                녹음이 없었으면 빈 배열 반환.
        """
        with self._lock:
            stream = self._stream
            self._stream = None

        if stream is None:
            return np.array([], dtype=np.float32)

        stream.stop()
        stream.close()

        with self._lock:
            chunks = self._chunks[:]
            self._chunks = []

        if not chunks:
            return np.array([], dtype=np.float32)

        return np.concatenate(chunks, axis=0)

    # ── 내부 ────────────────────────────────────────────────────────────────────

    def _callback(self, indata: np.ndarray, frames: int, time_info, status):
        """sounddevice 오디오 콜백 — 별도 스레드에서 호출됨."""
        mono = indata[:, 0].copy()

        with self._lock:
            if self._stream is not None:
                self._chunks.append(mono)

        if self._on_level:
            rms   = float(np.sqrt(np.mean(mono ** 2)))
            level = min(100, int(rms * 500))  # 0~1 float → 0~100 스케일
            self._on_level(level)
