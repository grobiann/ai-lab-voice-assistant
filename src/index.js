/**
 * index.js — Voice Activation Trigger for Claude
 *
 * Listens to the microphone continuously.
 * When the wake word "클로드" is detected, it:
 *   1. Opens / focuses the Claude window
 *   2. Transcribes everything said afterwards
 *   3. Types the transcription into Claude's input field
 *   4. Waits for manual submission (never auto-submits)
 *
 * Say "취소" or "그만" to cancel and return to listening mode.
 * Press Ctrl+C to exit.
 */

require('dotenv').config();

const logger    = require('./logger');
const recognizer = require('./recognizer');
const wakeDetector = require('./wakeDetector');
const { ensureClaudeOpen, appendText } = require('./automator');
const notifier  = require('node-notifier');

// ── State ─────────────────────────────────────────────────────────────────────

let activated    = false;   // Are we in "dictating to Claude" mode?
let sessionBuffer = '';     // Accumulated text in the current session
let isFirstChunk = true;    // First text chunk after activation?
let claudeReady  = false;   // Has the Claude window been found/opened?

// ── Helpers ───────────────────────────────────────────────────────────────────

function notify(title, message) {
  try {
    notifier.notify({ title, message, sound: false, wait: false });
  } catch {
    // Desktop notifications are optional
  }
}

async function handleActivation(textAfterWakeWord) {
  activated     = true;
  sessionBuffer = '';
  isFirstChunk  = true;
  claudeReady   = false;

  logger.wake('🔔  "클로드" 감지!  Claude를 여는 중...');
  notify('클로드 활성화', '말씀하세요. 수동으로 제출할 때까지 받아씁니다.');

  claudeReady = await ensureClaudeOpen();

  // If there was text immediately after the wake word, type it right away
  if (textAfterWakeWord) {
    await typeToClaud(textAfterWakeWord);
  }
}

async function handleDeactivation() {
  activated = false;
  logger.section('활성화 취소 — 다시 "클로드"를 기다리는 중...');
  notify('클로드 비활성화', '"클로드"라고 말하면 다시 시작됩니다.');
}

async function typeToClaud(text) {
  if (!text.trim()) return;

  sessionBuffer += (isFirstChunk ? '' : ' ') + text;

  if (claudeReady) {
    await appendText(text, isFirstChunk);
  } else {
    logger.warn(`Claude 창 준비 안됨 — 버퍼에 저장: "${text}"`);
    // Retry once
    claudeReady = await ensureClaudeOpen();
    if (claudeReady) {
      // Type the entire buffer accumulated so far
      await appendText(sessionBuffer, true);
      isFirstChunk = false;
      return;
    } else {
      logger.error('Claude 창을 찾을 수 없습니다. Claude를 직접 열어주세요.');
    }
  }

  isFirstChunk = false;
}

// ── Main ──────────────────────────────────────────────────────────────────────

async function main() {
  logger.section('Claude 음성 활성화 트리거');
  logger.info('"클로드"라고 말하면 Claude를 열고 받아쓰기를 시작합니다.');
  logger.info('"취소" 또는 "그만"이라고 말하면 비활성화됩니다.');
  logger.info('종료하려면 Ctrl+C를 누르세요.\n');

  // Start the Python STT server (handles mic + Vosk internally)
  try {
    await recognizer.start();
  } catch (err) {
    logger.error(err.message);
    process.exit(1);
  }

  // Show a live microphone level meter so the user can confirm audio is captured
  recognizer.on('level', (value) => {
    if (activated) return;  // hide meter while dictating to reduce noise
    const bars  = Math.round(value / 5);           // 0–20 bars
    const filled = '█'.repeat(bars);
    const empty  = '░'.repeat(20 - bars);
    const label  = value > 10 ? ' (sound detected)' : '';
    logger.partial(`MIC [${filled}${empty}] ${String(value).padStart(3)}%${label}`);
  });

  // Handle partial results — show in console only, don't type yet
  recognizer.on('partial', (text) => {
    logger.partial(`... ${text}`);
  });

  // Handle confirmed (final) results
  recognizer.on('final', async (text) => {
    logger.clearPartial();

    if (!activated) {
      // ── LISTENING mode: check for wake word ─────────────────────────────
      const afterWake = wakeDetector.checkForWakeWord(text);
      if (afterWake !== null) {
        await handleActivation(afterWake);
      }
      // Otherwise: normal background speech, ignore
    } else {
      // ── ACTIVATED mode: transcribe and type into Claude ─────────────────
      if (wakeDetector.checkForDeactivate(text)) {
        await handleDeactivation();
        return;
      }

      logger.speech(text);
      await typeToClaud(text);
    }
  });

  // Graceful shutdown
  process.on('SIGINT', () => {
    logger.clearPartial();
    logger.info('\n종료 중...');
    recognizer.stop();
    process.exit(0);
  });

  logger.info(`현재 상태: 🟢 대기 중 — "클로드"를 기다리는 중`);
}

main().catch((err) => {
  logger.error(`치명적 오류: ${err.message}`);
  process.exit(1);
});
