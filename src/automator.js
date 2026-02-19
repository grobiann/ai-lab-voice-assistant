/**
 * automator.js
 * Sends automation commands (focus_claude, type_text) to the Python subprocess
 * via its stdin and waits for ack responses via events on the recognizer.
 *
 * Works on Windows and Linux — all platform-specific code lives in
 * python/stt_server.py (uses pygetwindow/pyautogui on Windows,
 * xdotool/xclip on Linux).
 */

const recognizer = require('./recognizer');
const config     = require('./config');
const logger     = require('./logger');

const ACK_TIMEOUT_MS = 12000;  // max wait for focus (window may need to open)
const TYPE_TIMEOUT_MS = 5000;

let _reqId = 0;

/**
 * Send a command to Python and wait for the matching ack.
 * @returns {Promise<boolean>} success flag from Python
 */
function sendAndWait(cmd, extraPayload = {}, timeoutMs = ACK_TIMEOUT_MS) {
  const id  = ++_reqId;
  const msg = { cmd, id, ...extraPayload };

  return new Promise((resolve) => {
    const timer = setTimeout(() => {
      recognizer.removeAllListeners(`ack:${cmd}:${id}`);
      logger.warn(`Command "${cmd}" timed out after ${timeoutMs}ms`);
      resolve(false);
    }, timeoutMs);

    recognizer.once(`ack:${cmd}:${id}`, (success) => {
      clearTimeout(timer);
      resolve(success);
    });

    recognizer.sendCommand(msg);
  });
}

/**
 * Ensure the Claude window is open and focused.
 * @returns {Promise<boolean>}
 */
async function ensureClaudeOpen() {
  return sendAndWait(
    'focus_claude',
    {
      windowNames: config.CLAUDE_WINDOW_NAMES,
      appPath:     config.CLAUDE_APP_PATH || null,
    },
    ACK_TIMEOUT_MS,
  );
}

/**
 * Append text to the Claude input field.
 * @param {string}  text     Text to type.
 * @param {boolean} isFirst  True = no leading space added.
 * @returns {Promise<boolean>}
 */
async function appendText(text, isFirst = false) {
  return sendAndWait(
    'type_text',
    { text, isFirst },
    TYPE_TIMEOUT_MS,
  );
}

module.exports = { ensureClaudeOpen, appendText };
