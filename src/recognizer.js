/**
 * recognizer.js
 * Spawns the Python STT server (python/stt_server.py) as a child process.
 * The Python process handles microphone access and Vosk recognition;
 * this module reads JSON lines from its stdout and emits 'partial'/'final' events.
 */

const path = require('path');
const { spawn } = require('child_process');
const readline = require('readline');
const { EventEmitter } = require('events');
const config = require('./config');
const logger = require('./logger');

const PYTHON_SCRIPT = path.join(__dirname, '../python/stt_server.py');
// On Windows, the executable is 'python'; on Linux/macOS it is 'python3'
const PYTHON_BIN = process.platform === 'win32' ? 'python' : 'python3';

class Recognizer extends EventEmitter {
  constructor() {
    super();
    this._proc = null;
  }

  /**
   * Start the Python STT subprocess.
   * Returns a Promise that resolves once the subprocess signals it is ready.
   */
  start() {
    return new Promise((resolve, reject) => {
      const env = { ...process.env };
      if (config.AUDIO_DEVICE) {
        env.AUDIO_DEVICE = config.AUDIO_DEVICE;
      }

      this._proc = spawn(PYTHON_BIN, [PYTHON_SCRIPT, config.MODEL_PATH], {
        env,
        stdio: ['pipe', 'pipe', 'inherit'],  // stdin=pipe, stdout=pipe, stderr=terminal
      });

      this._proc.on('error', (err) => {
        reject(new Error(`Failed to start STT server: ${err.message}`));
      });

      this._proc.on('exit', (code) => {
        if (code !== 0 && code !== null) {
          logger.warn(`STT server exited with code ${code}`);
        }
      });

      // Read newline-delimited JSON from Python stdout
      const rl = readline.createInterface({ input: this._proc.stdout });

      rl.on('line', (line) => {
        let msg;
        try {
          msg = JSON.parse(line);
        } catch {
          return; // Ignore non-JSON lines
        }

        switch (msg.type) {
          case 'ready':
            logger.success('STT server ready — listening for speech');
            resolve();
            break;

          case 'partial':
            if (msg.text) this.emit('partial', msg.text);
            break;

          case 'final':
            if (msg.text) this.emit('final', msg.text);
            break;

          // Automation ack — emitted as 'ack:<cmd>:<id>' so automator can await it
          case 'ack':
            this.emit(`ack:${msg.cmd}:${msg.id}`, msg.success);
            break;

          case 'info':
            logger.info(`[mic] ${msg.message}`);
            break;

          // Mic level (0–100) — forwarded so index.js can render a meter
          case 'level':
            this.emit('level', msg.value);
            break;

          case 'warn':
            logger.warn(`[Python] ${msg.message}`);
            break;

          case 'error':
            logger.error(`STT error: ${msg.message}`);
            reject(new Error(msg.message));
            break;
        }
      });

      rl.on('close', () => {
        logger.info('STT server stream closed');
      });
    });
  }

  /**
   * Send a JSON command to the Python subprocess via its stdin.
   * @param {object} cmd  Plain object — will be serialised to one JSON line.
   */
  sendCommand(cmd) {
    if (this._proc && this._proc.stdin.writable) {
      this._proc.stdin.write(JSON.stringify(cmd) + '\n');
    }
  }

  /**
   * Stop the Python STT subprocess.
   */
  stop() {
    if (this._proc) {
      // Closing stdin signals the Python server to exit cleanly
      this._proc.stdin.end();
      this._proc.kill('SIGTERM');
      this._proc = null;
    }
  }
}

module.exports = new Recognizer();
