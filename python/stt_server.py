#!/usr/bin/env python3
"""
stt_server.py — Real-time Korean speech-to-text server using Vosk + sounddevice.

Reads audio from the microphone and writes JSON lines to stdout.

Each line is one of:
  {"type": "ready"}                      -- server is ready
  {"type": "partial", "text": "..."}    -- in-progress transcription
  {"type": "final",   "text": "..."}    -- confirmed utterance
  {"type": "error",   "message": "..."}  -- error

Usage:
  python3 stt_server.py <model_path>

The process exits when stdin closes (i.e. the parent Node.js process exits).
"""

import sys
import json
import os
import queue
import threading
# ── Helpers ────────────────────────────────────────────────────────────────────

def emit(obj):
    """Write a JSON object as a single line to stdout and flush immediately."""
    print(json.dumps(obj, ensure_ascii=False), flush=True)

def die(msg):
    emit({"type": "error", "message": msg})
    sys.exit(1)

# ── Dependency check ───────────────────────────────────────────────────────────

try:
    import vosk
except ImportError:
    die("vosk not installed. Run: pip3 install vosk")

try:
    import sounddevice as sd
except ImportError:
    die("sounddevice not installed. Run: pip3 install sounddevice")

# ── Configuration ──────────────────────────────────────────────────────────────

SAMPLE_RATE  = 16000
CHANNELS     = 1
BLOCK_SIZE   = 4000   # ~250 ms per chunk — good latency/accuracy trade-off
DTYPE        = 'int16'

# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        die("Usage: stt_server.py <model_path>")

    model_path = sys.argv[1]

    if not os.path.isdir(model_path):
        die(
            f"Model directory not found: {model_path}\n"
            "Run: npm run download-model"
        )

    # Suppress Vosk's verbose C++ logs
    vosk.SetLogLevel(-1)

    try:
        model = vosk.Model(model_path)
    except Exception as e:
        die(f"Failed to load Vosk model: {e}")

    rec = vosk.KaldiRecognizer(model, SAMPLE_RATE)
    rec.SetWords(False)

    # Audio queue — sounddevice callback pushes chunks; main loop pops them
    audio_q = queue.Queue()

    def audio_callback(indata, frames, time_info, status):
        # indata is a (frames, channels) numpy array of int16
        audio_q.put(bytes(indata))

    # Determine device index
    device_index = None
    device_env = os.environ.get("AUDIO_DEVICE", "").strip()
    if device_env:
        try:
            device_index = int(device_env)
        except ValueError:
            pass

    try:
        stream = sd.RawInputStream(
            samplerate=SAMPLE_RATE,
            blocksize=BLOCK_SIZE,
            device=device_index,
            channels=CHANNELS,
            dtype=DTYPE,
            callback=audio_callback,
        )
    except Exception as e:
        die(f"Failed to open microphone: {e}")

    # Watch for parent process closing stdin → exit cleanly
    def stdin_watcher():
        try:
            sys.stdin.read()
        except Exception:
            pass
        os._exit(0)

    threading.Thread(target=stdin_watcher, daemon=True).start()

    emit({"type": "ready"})

    last_partial = ""

    with stream:
        try:
            while True:
                try:
                    data = audio_q.get(timeout=1.0)
                except queue.Empty:
                    continue

                if rec.AcceptWaveform(data):
                    result = json.loads(rec.Result())
                    text = result.get("text", "").strip()
                    if text:
                        emit({"type": "final", "text": text})
                        last_partial = ""
                else:
                    partial = json.loads(rec.PartialResult())
                    text = partial.get("partial", "").strip()
                    if text and text != last_partial:
                        emit({"type": "partial", "text": text})
                        last_partial = text

        except KeyboardInterrupt:
            pass
        finally:
            # Flush any remaining audio
            try:
                result = json.loads(rec.FinalResult())
                text = result.get("text", "").strip()
                if text:
                    emit({"type": "final", "text": text})
            except Exception:
                pass


if __name__ == "__main__":
    main()
