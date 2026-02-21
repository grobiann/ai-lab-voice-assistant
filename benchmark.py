#!/usr/bin/env python3
"""
benchmark.py — Voice Typer 정확도·속도 비교 테스트

사용법:
  python benchmark.py              # 마이크 녹음 후 전체 모드 비교
  python benchmark.py --wav FILE   # WAV 파일로 테스트 (녹음 생략)
  python benchmark.py --models small medium large-v3   # 특정 모델만 테스트

동작:
  1. 마이크로 테스트 음성을 한 번 녹음합니다.
  2. 동일한 오디오를 여러 Whisper 모델로 병렬 추론합니다.
  3. 추론 시간과 결과를 표로 출력합니다.
  4. 원하는 모드를 선택하면 config.py 에 저장됩니다.
"""

import sys
import os
import time
import argparse
import re
import threading
import numpy as np

# ── 프로젝트 루트를 Python 경로에 추가 ───────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

import config as cfg

# ── 테스트 설정 목록 ──────────────────────────────────────────────────────────────
# (표시 라벨,  tier_key,  model_name)
DEFAULT_TESTS = [
    ("tier1 / tiny",     "tier1", "tiny"),
    ("tier1 / small",    "tier1", "small"),
    ("tier2 / medium",   "tier2", "medium"),
    ("tier2 / large-v3", "tier2", "large-v3"),
]

SAMPLE_RATE = 16_000   # Whisper 요구 샘플레이트


# ─────────────────────────────────────────────────────────────────────────────
# 오디오 녹음
# ─────────────────────────────────────────────────────────────────────────────

def record_from_mic() -> np.ndarray:
    """마이크로 오디오 녹음 — Enter 로 중지."""
    try:
        import sounddevice as sd
    except ImportError:
        print("[오류] sounddevice 가 설치되지 않았습니다: pip install sounddevice")
        sys.exit(1)

    chunks   = []
    stop_evt = threading.Event()

    def _cb(indata, frames, t, status):
        chunks.append(indata.copy())

    print()
    print("  ● 마이크 녹음 중 — 테스트 문장을 말한 후 [Enter] 를 누르세요.")
    print("    예) '안녕하세요, ChatGPT API 와 Python 으로 개발한 앱입니다.'")
    print()

    with sd.InputStream(samplerate=SAMPLE_RATE, channels=1,
                        dtype="float32", callback=_cb):
        input()   # Enter 대기

    if not chunks:
        print("[오류] 녹음된 오디오가 없습니다.")
        sys.exit(1)

    audio = np.concatenate(chunks).squeeze()
    dur   = len(audio) / SAMPLE_RATE
    rms   = float(np.sqrt(np.mean(audio ** 2)))
    print(f"  녹음 완료: {dur:.1f}초  RMS {rms:.4f}")
    return audio


def load_wav(path: str) -> np.ndarray:
    """WAV 파일 로드 (16kHz mono float32 로 변환)."""
    try:
        import soundfile as sf
    except ImportError:
        print("[오류] soundfile 이 설치되지 않았습니다: pip install soundfile")
        sys.exit(1)

    data, sr = sf.read(path, dtype="float32", always_2d=False)
    if data.ndim > 1:
        data = data.mean(axis=1)

    if sr != SAMPLE_RATE:
        try:
            import resampy
            data = resampy.resample(data, sr, SAMPLE_RATE)
        except ImportError:
            print(f"[경고] 샘플레이트 {sr}Hz → {SAMPLE_RATE}Hz 변환을 위해 "
                  f"resampy 가 필요합니다: pip install resampy")
            sys.exit(1)

    print(f"  WAV 로드: {path}  ({len(data)/SAMPLE_RATE:.1f}초)")
    return data.astype(np.float32)


# ─────────────────────────────────────────────────────────────────────────────
# 단일 모델 추론
# ─────────────────────────────────────────────────────────────────────────────

def _detect_device() -> tuple[str, str]:
    """CUDA 가용 여부 확인 후 (device, compute_type) 반환."""
    device  = "cpu"
    compute = "int8"
    try:
        import torch
        if torch.cuda.is_available():
            device  = "cuda"
            compute = "float16"
    except ImportError:
        pass
    return device, compute


def run_single(model_name: str, audio: np.ndarray,
               beam: int = 1, temperature=None) -> dict:
    """
    지정한 Whisper 모델 하나를 로드 → 추론 → 결과 반환.

    반환 dict:
      model      : 모델 이름
      load_time  : 모델 로드 시간 (초) — 이미 캐시된 경우 짧음
      infer_time : 추론 시간 (초)
      text       : 인식 결과
      error      : 오류 메시지 (없으면 None)
    """
    if temperature is None:
        temperature = [0, 0.2]

    from faster_whisper import WhisperModel

    device, compute = _detect_device()

    # ── 모델 로드 ──────────────────────────────────────────────────────────────
    t0 = time.perf_counter()
    try:
        model = WhisperModel(model_name, device=device, compute_type=compute)
    except Exception as e:
        return {"model": model_name, "load_time": 0,
                "infer_time": 0, "text": "", "error": str(e)}
    load_time = time.perf_counter() - t0

    # ── 추론 ───────────────────────────────────────────────────────────────────
    t1 = time.perf_counter()
    try:
        segs, _ = model.transcribe(
            audio.astype(np.float32),
            language=cfg.WHISPER_LANG,
            beam_size=beam,
            condition_on_previous_text=False,
            vad_filter=True,
            vad_parameters={"min_silence_duration_ms": 300},
            temperature=temperature,
        )
        text = " ".join(s.text.strip() for s in segs).strip()
    except Exception as e:
        return {"model": model_name, "load_time": load_time,
                "infer_time": 0, "text": "", "error": str(e)}
    infer_time = time.perf_counter() - t1

    # 메모리 해제
    del model
    try:
        import torch
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except ImportError:
        pass

    return {
        "model":      model_name,
        "load_time":  load_time,
        "infer_time": infer_time,
        "text":       text,
        "error":      None,
    }


# ─────────────────────────────────────────────────────────────────────────────
# 결과 테이블 출력
# ─────────────────────────────────────────────────────────────────────────────

def _truncate(s: str, width: int) -> str:
    if len(s) <= width:
        return s
    return s[:width - 1] + "…"


def print_table(results: list[dict], tests: list[tuple], cur_mode: str, cur_model: str):
    """결과를 ASCII 표로 출력."""
    COL_LABEL  = 20
    COL_LOAD   = 8
    COL_INFER  = 8
    COL_TEXT   = 42

    sep = (f"  ┼{'─'*COL_LABEL}┼{'─'*COL_LOAD}┼{'─'*COL_INFER}┼{'─'*COL_TEXT}┤")
    hdr = (f"  │{'모드/모델':^{COL_LABEL}}│{'로드(s)':^{COL_LOAD}}"
           f"│{'추론(s)':^{COL_INFER}}│{'결과':^{COL_TEXT}}│")

    print()
    print("  " + "─" * (COL_LABEL + COL_LOAD + COL_INFER + COL_TEXT + 4))
    print(hdr)
    print(sep)

    for (label, tier, model), r in zip(tests, results):
        cur_mark = " ◀" if (tier == cur_mode and model == cur_model) else "  "
        lbl_str  = _truncate(label + cur_mark, COL_LABEL)

        if r["error"]:
            txt_str = f"[오류] {r['error']}"[:COL_TEXT]
            load_s  = "-"
            infer_s = "-"
        else:
            txt_str = _truncate(r["text"] or "(인식 없음)", COL_TEXT)
            load_s  = f"{r['load_time']:.1f}"
            infer_s = f"{r['infer_time']:.2f}"

        print(f"  │{lbl_str:<{COL_LABEL}}│{load_s:>{COL_LOAD-1}} │{infer_s:>{COL_INFER-1}} │{txt_str:<{COL_TEXT}}│")

    print("  " + "─" * (COL_LABEL + COL_LOAD + COL_INFER + COL_TEXT + 4))


# ─────────────────────────────────────────────────────────────────────────────
# config.py 업데이트
# ─────────────────────────────────────────────────────────────────────────────

def save_config(tier: str, model: str):
    """선택한 tier / model 을 config.py 에 기록."""
    config_path = os.path.join(SCRIPT_DIR, "config.py")
    with open(config_path, encoding="utf-8") as f:
        src = f.read()

    # STT_MODE 업데이트
    src = re.sub(
        r'^(STT_MODE\s*=\s*)["\'].*?["\']',
        lambda m: m.group(1) + f'"{tier}"',
        src, flags=re.MULTILINE,
    )

    # 해당 tier 모델 라인 업데이트
    tier_key = tier.upper()   # TIER1 / TIER2
    src = re.sub(
        rf'^(TIER{tier_key[-1]}_MODEL\s*=\s*)["\'].*?["\']',
        lambda m: m.group(1) + f'"{model}"',
        src, flags=re.MULTILINE,
    )

    with open(config_path, "w", encoding="utf-8") as f:
        f.write(src)

    print(f"\n  config.py 업데이트 완료 → STT_MODE={tier!r}  모델={model!r}")


# ─────────────────────────────────────────────────────────────────────────────
# CLI 진입점
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Voice Typer STT 정확도·속도 벤치마크",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--wav", metavar="FILE",
        help="테스트에 사용할 WAV 파일 (지정 시 마이크 녹음 생략)",
    )
    parser.add_argument(
        "--models", nargs="+",
        metavar="MODEL",
        help="테스트할 모델 이름 (기본: tiny small medium large-v3)",
    )
    parser.add_argument(
        "--beam", type=int, default=1,
        help="Beam size (기본 1=greedy)",
    )
    args = parser.parse_args()

    print("=" * 56)
    print("  Voice Typer — 정확도·속도 벤치마크")
    print(f"  현재 설정: {cfg.STT_MODE} / {getattr(cfg, cfg.STT_MODE.upper()+'_MODEL', '?')}")
    print("=" * 56)

    # ── 테스트 목록 구성 ────────────────────────────────────────────────────────
    if args.models:
        tests = []
        for m in args.models:
            tier = "tier1" if m in ("tiny", "base", "small") else "tier2"
            tests.append((f"{tier} / {m}", tier, m))
    else:
        tests = DEFAULT_TESTS

    print(f"\n  테스트 모델 ({len(tests)}개):", ", ".join(m for _, _, m in tests))

    # ── 오디오 준비 ─────────────────────────────────────────────────────────────
    if args.wav:
        audio = load_wav(args.wav)
    else:
        audio = record_from_mic()

    dur = len(audio) / SAMPLE_RATE

    # ── 각 모델 순차 추론 ───────────────────────────────────────────────────────
    print()
    results = []
    for i, (label, tier, model) in enumerate(tests, 1):
        print(f"  [{i}/{len(tests)}] {label} 테스트 중...", end=" ", flush=True)
        r = run_single(model, audio, beam=args.beam)
        if r["error"]:
            print(f"오류: {r['error']}")
        else:
            print(f"완료 (로드 {r['load_time']:.1f}s  추론 {r['infer_time']:.2f}s)")
        results.append(r)

    # ── 결과 표 출력 ────────────────────────────────────────────────────────────
    cur_mode  = cfg.STT_MODE
    cur_model = getattr(cfg, f"{cur_mode.upper()}_MODEL", "?") if cur_mode != "cloud" else "cloud"

    print_table(results, tests, cur_mode, cur_model)

    # ── 모드 선택 및 저장 ───────────────────────────────────────────────────────
    print()
    print("  원하는 모드를 선택하면 config.py 에 저장됩니다:")
    valid = []
    for i, ((label, tier, model), r) in enumerate(zip(tests, results), 1):
        cur_mark = "  (현재 설정)" if (tier == cur_mode and model == cur_model) else ""
        err_mark = "  [오류]" if r["error"] else ""
        print(f"    {i}. {label}{cur_mark}{err_mark}")
    print(f"    0. 변경 없음")
    print()

    while True:
        try:
            raw = input("  선택 [0]: ").strip()
            if raw == "" or raw == "0":
                print("  변경 없음.")
                break
            idx = int(raw) - 1
            if 0 <= idx < len(tests):
                label, tier, model = tests[idx]
                if results[idx]["error"]:
                    print(f"  해당 모델은 오류가 발생했습니다. 다시 선택하세요.")
                    continue
                save_config(tier, model)
                break
            else:
                print(f"  1~{len(tests)} 또는 0 을 입력하세요.")
        except (ValueError, KeyboardInterrupt):
            print("\n  변경 없음.")
            break

    print()


if __name__ == "__main__":
    main()
