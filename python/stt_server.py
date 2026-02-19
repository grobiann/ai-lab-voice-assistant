#!/usr/bin/env python3
"""
stt_server.py — Real-time Korean STT server + cross-platform desktop automation.

STDOUT (events to Node.js) — newline-delimited JSON:
  {"type": "ready"}
  {"type": "partial", "text": "..."}
  {"type": "final",   "text": "..."}
  {"type": "ack",     "cmd": "...", "id": <n>, "success": true/false}
  {"type": "warn",    "message": "..."}
  {"type": "error",   "message": "..."}

STDIN (commands from Node.js) — newline-delimited JSON:
  {"cmd": "focus_claude", "id": <n>, "windowNames": [...], "appPath": "..."|null}
  {"cmd": "type_text",    "id": <n>, "text": "...", "isFirst": true/false}

Usage:
  python3 stt_server.py <model_path>
"""

import sys
import json
import os
import queue
import threading
import subprocess
import tempfile
import time
import platform

PLATFORM = platform.system()   # 'Windows' | 'Linux' | 'Darwin'

# ── Helpers ────────────────────────────────────────────────────────────────────

def emit(obj):
    print(json.dumps(obj, ensure_ascii=False), flush=True)

def warn(msg):
    emit({"type": "warn", "message": msg})

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

# ── Audio config ───────────────────────────────────────────────────────────────

SAMPLE_RATE = 16000
CHANNELS    = 1
BLOCK_SIZE  = 4000
DTYPE       = 'int16'

# ── Platform-specific automation ───────────────────────────────────────────────

def _run(cmd, **kw):
    """Run a shell command, return (returncode, stdout)."""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, **kw)
        return r.returncode, r.stdout.strip()
    except FileNotFoundError:
        return -1, ''

# ─── Window management ───

def _find_window_linux(names):
    for name in names:
        rc, out = _run(['xdotool', 'search', '--name', name])
        if rc == 0 and out:
            return out.split('\n')[-1]
    rc, out = _run(['xdotool', 'search', '--class', 'Claude'])
    if rc == 0 and out:
        return out.split('\n')[-1]
    return None

def _focus_window_linux(win_id):
    _run(['xdotool', 'windowraise', win_id])
    _run(['xdotool', 'windowfocus', '--sync', win_id])
    time.sleep(0.25)

def _open_claude_linux(app_path):
    if app_path and os.path.exists(app_path):
        subprocess.Popen([app_path])
    else:
        subprocess.Popen(['xdg-open', 'https://claude.ai'])
    time.sleep(3.0)

def _find_window_windows(names):
    try:
        import pygetwindow as gw
        for name in names:
            wins = gw.getWindowsWithTitle(name)
            if wins:
                return wins[0]
    except ImportError:
        warn("pygetwindow not installed. Run: pip install pygetwindow")
    return None

def _focus_window_windows(win):
    try:
        win.restore()
        win.activate()
        time.sleep(0.3)
    except Exception as e:
        warn(f"Window activate failed: {e}")

def _open_claude_windows(app_path):
    if app_path and os.path.exists(app_path):
        subprocess.Popen([app_path])
    else:
        os.system('start https://claude.ai')
    time.sleep(3.0)

def focus_claude(window_names, app_path):
    """Find and focus the Claude window. Opens Claude if not found. Returns success bool."""
    if PLATFORM == 'Windows':
        win = _find_window_windows(window_names)
        if win:
            _focus_window_windows(win)
            return True
        _open_claude_windows(app_path)
        win = _find_window_windows(window_names)
        if win:
            _focus_window_windows(win)
            return True
        return False
    else:
        win_id = _find_window_linux(window_names)
        if win_id:
            _focus_window_linux(win_id)
            return True
        _open_claude_linux(app_path)
        win_id = _find_window_linux(window_names)
        if win_id:
            _focus_window_linux(win_id)
            return True
        return False

# ─── Text input ───

def _type_text_linux(text):
    """Copy text to clipboard and paste via xdotool (handles Korean)."""
    with tempfile.NamedTemporaryFile(mode='wb', suffix='.txt', delete=False) as f:
        f.write(text.encode('utf-8'))
        fname = f.name
    try:
        rc, _ = _run(['xclip', '-selection', 'clipboard', '-in', fname])
        if rc != 0:
            # Try xsel as fallback
            _run(['xsel', '--clipboard', '--input', fname])
        os.unlink(fname)
        _run(['xdotool', 'key', '--clearmodifiers', 'End'])
        time.sleep(0.05)
        _run(['xdotool', 'key', '--clearmodifiers', 'ctrl+v'])
        return True
    except Exception as e:
        warn(f"Linux type failed: {e}")
        try:
            os.unlink(fname)
        except Exception:
            pass
        return False

def _type_text_windows(text):
    """Copy text to clipboard and paste via pyperclip + pyautogui."""
    try:
        import pyperclip
        import pyautogui
        pyperclip.copy(text)
        time.sleep(0.1)
        pyautogui.hotkey('ctrl', 'End')
        time.sleep(0.05)
        pyautogui.hotkey('ctrl', 'v')
        return True
    except ImportError as e:
        warn(f"Missing package: {e}. Run: pip install pyperclip pyautogui")
        return False
    except Exception as e:
        warn(f"Windows type failed: {e}")
        return False

def type_text(text, is_first):
    """Append text to the Claude input field."""
    to_type = text if is_first else (' ' + text)
    if PLATFORM == 'Windows':
        return _type_text_windows(to_type)
    else:
        return _type_text_linux(to_type)

# ── Stdin command reader (Node.js → Python) ────────────────────────────────────

def handle_command(msg):
    cmd    = msg.get('cmd')
    req_id = msg.get('id')

    if cmd == 'focus_claude':
        names    = msg.get('windowNames', ['Claude', 'claude.ai'])
        app_path = msg.get('appPath') or None
        success  = focus_claude(names, app_path)
        emit({'type': 'ack', 'cmd': 'focus_claude', 'id': req_id, 'success': success})

    elif cmd == 'type_text':
        text     = msg.get('text', '')
        is_first = msg.get('isFirst', False)
        success  = type_text(text, is_first)
        emit({'type': 'ack', 'cmd': 'type_text', 'id': req_id, 'success': success})

def stdin_reader():
    """Reads newline-delimited JSON commands from stdin in a background thread."""
    try:
        for line in iter(sys.stdin.readline, ''):
            line = line.strip()
            if line:
                try:
                    msg = json.loads(line)
                    threading.Thread(target=handle_command, args=(msg,), daemon=True).start()
                except json.JSONDecodeError:
                    pass
    except Exception:
        pass
    # stdin closed = parent Node.js process exited
    os._exit(0)

# ── Main STT loop ──────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        die("Usage: stt_server.py <model_path>")

    model_path = sys.argv[1]
    if not os.path.isdir(model_path):
        die(f"Model directory not found: {model_path}. Run: npm run download-model")

    vosk.SetLogLevel(-1)

    try:
        model = vosk.Model(model_path)
    except Exception as e:
        die(f"Failed to load Vosk model: {e}")

    rec = vosk.KaldiRecognizer(model, SAMPLE_RATE)
    rec.SetWords(False)

    audio_q = queue.Queue()

    def audio_callback(indata, frames, time_info, status):
        audio_q.put(bytes(indata))

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

    # Start stdin command reader
    threading.Thread(target=stdin_reader, daemon=True).start()

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
            try:
                result = json.loads(rec.FinalResult())
                text = result.get("text", "").strip()
                if text:
                    emit({"type": "final", "text": text})
            except Exception:
                pass


if __name__ == "__main__":
    main()
