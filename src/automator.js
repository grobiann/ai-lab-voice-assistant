/**
 * automator.js
 * Desktop automation: find the Claude window, focus it,
 * and type dictated text into its input field.
 *
 * Relies on xdotool and xclip (or xsel) — standard Linux X11 tools.
 * Install: sudo apt install xdotool xclip
 */

const { execSync, spawnSync } = require('child_process');
const fs = require('fs');
const os = require('os');
const path = require('path');
const config = require('./config');
const logger = require('./logger');

// --------------------------------------------------------------------------
// Low-level helpers
// --------------------------------------------------------------------------

function run(cmd, opts = {}) {
  try {
    return execSync(cmd, { encoding: 'utf8', ...opts }).trim();
  } catch {
    return null;
  }
}

function toolAvailable(name) {
  return run(`which ${name}`) !== null;
}

// --------------------------------------------------------------------------
// Clipboard-based typing (reliable for Unicode / Korean)
// --------------------------------------------------------------------------

/**
 * Copy text to the X11 clipboard using xclip or xsel.
 */
function copyToClipboard(text) {
  const tmpFile = path.join(os.tmpdir(), `claude_voice_${process.pid}.txt`);
  fs.writeFileSync(tmpFile, text, 'utf8');

  if (toolAvailable('xclip')) {
    run(`xclip -selection clipboard < "${tmpFile}"`);
  } else if (toolAvailable('xsel')) {
    run(`xsel --clipboard --input < "${tmpFile}"`);
  } else {
    throw new Error(
      'Neither xclip nor xsel found.\n' +
      'Install with: sudo apt install xclip'
    );
  }

  fs.unlinkSync(tmpFile);
}

/**
 * Paste from clipboard into the focused window.
 */
function pasteFromClipboard() {
  if (!toolAvailable('xdotool')) {
    throw new Error(
      'xdotool not found.\n' +
      'Install with: sudo apt install xdotool'
    );
  }
  run('xdotool key --clearmodifiers ctrl+v');
}

// --------------------------------------------------------------------------
// Window management
// --------------------------------------------------------------------------

/**
 * Search for a Claude window by title patterns.
 * Returns the window ID string, or null if not found.
 */
function findClaudeWindowId() {
  if (!toolAvailable('xdotool')) return null;

  for (const name of config.CLAUDE_WINDOW_NAMES) {
    const result = run(`xdotool search --name "${name}" 2>/dev/null`);
    if (result) {
      // xdotool may return multiple IDs; take the last (most recent)
      const ids = result.split('\n').filter(Boolean);
      if (ids.length > 0) return ids[ids.length - 1];
    }
  }

  // Also try searching by class
  const classResult = run('xdotool search --class "Claude" 2>/dev/null');
  if (classResult) {
    const ids = classResult.split('\n').filter(Boolean);
    if (ids.length > 0) return ids[ids.length - 1];
  }

  return null;
}

/**
 * Raise and focus a window by ID.
 */
function focusWindow(windowId) {
  run(`xdotool windowraise ${windowId}`);
  run(`xdotool windowfocus --sync ${windowId}`);
  // Small delay to let the window come to the foreground
  sleepMs(200);
}

/**
 * Try to open Claude (desktop app or browser fallback).
 */
function openClaude() {
  // 1. Configured app path
  if (config.CLAUDE_APP_PATH && fs.existsSync(config.CLAUDE_APP_PATH)) {
    logger.info(`Launching Claude app: ${config.CLAUDE_APP_PATH}`);
    spawnSync(config.CLAUDE_APP_PATH, [], { detached: true, stdio: 'ignore' });
    sleepMs(2000);
    return;
  }

  // 2. `claude` binary in PATH (Claude Code CLI)
  if (toolAvailable('claude')) {
    logger.info('Opening Claude via CLI...');
    // Claude Code is a CLI, open it in a new terminal
    const terminal = findTerminal();
    if (terminal) {
      spawnSync(terminal, ['-e', 'claude'], { detached: true, stdio: 'ignore' });
      sleepMs(2000);
      return;
    }
  }

  // 3. xdg-open to claude.ai in the browser
  logger.info('Opening claude.ai in the default browser...');
  spawnSync('xdg-open', ['https://claude.ai'], { detached: true, stdio: 'ignore' });
  sleepMs(3000);
}

function findTerminal() {
  const candidates = ['gnome-terminal', 'xterm', 'konsole', 'xfce4-terminal', 'lxterminal'];
  return candidates.find((t) => toolAvailable(t)) || null;
}

function sleepMs(ms) {
  const end = Date.now() + ms;
  while (Date.now() < end) { /* busy wait for tiny delays */ }
}

// --------------------------------------------------------------------------
// Public API
// --------------------------------------------------------------------------

/**
 * Ensure Claude is open and focused.
 * Returns true if a window was found/opened, false if unsure.
 */
async function ensureClaudeOpen() {
  let windowId = findClaudeWindowId();

  if (!windowId) {
    logger.info('Claude window not found — attempting to open Claude...');
    openClaude();
    // Give the app/browser time to open, then retry
    await new Promise((r) => setTimeout(r, 2500));
    windowId = findClaudeWindowId();
  }

  if (windowId) {
    logger.success(`Found Claude window (id: ${windowId}) — focusing`);
    focusWindow(windowId);
    return true;
  }

  logger.warn(
    'Could not locate a Claude window.\n' +
    '  Please open Claude manually (desktop app or https://claude.ai) and try again.'
  );
  return false;
}

/**
 * Move cursor to the end of the Claude input field and type text.
 * Uses clipboard paste for reliable Unicode / Korean input.
 *
 * @param {string} text  The text to append.
 * @param {boolean} isFirst  If true, no leading space is added.
 */
async function appendText(text, isFirst = false) {
  const windowId = findClaudeWindowId();
  if (!windowId) {
    logger.warn('Claude window lost — text not typed: ' + text);
    return false;
  }

  focusWindow(windowId);

  // Move caret to the end of the textarea
  run('xdotool key --clearmodifiers End');

  const toType = isFirst ? text : ' ' + text;

  copyToClipboard(toType);
  pasteFromClipboard();

  logger.success(`Typed into Claude: "${toType.trim()}"`);
  return true;
}

module.exports = { ensureClaudeOpen, appendText, findClaudeWindowId };
