/**
 * wakeDetector.js
 * State machine that decides when the wake word has been spoken
 * and extracts the text that follows it.
 */

const config = require('./config');

const STATE = {
  LISTENING: 'listening',   // Waiting for wake word
  ACTIVATED: 'activated',   // Wake word detected, collecting speech
};

class WakeDetector {
  constructor() {
    this.state = STATE.LISTENING;
  }

  get isActivated() {
    return this.state === STATE.ACTIVATED;
  }

  get isListening() {
    return this.state === STATE.LISTENING;
  }

  /**
   * Check if the transcribed text contains a wake word.
   * Returns the text portion AFTER the wake word (may be empty string),
   * or null if no wake word found.
   */
  checkForWakeWord(text) {
    const lower = text.toLowerCase();

    for (const word of config.WAKE_WORDS) {
      const idx = lower.indexOf(word);
      if (idx !== -1) {
        // Everything after the wake word
        const after = text.slice(idx + word.length).trim();
        return after;
      }
    }
    return null;
  }

  /**
   * Check if the text contains a deactivation word.
   */
  checkForDeactivate(text) {
    const lower = text.toLowerCase();
    return config.DEACTIVATE_WORDS.some((word) => lower.includes(word));
  }

  activate() {
    this.state = STATE.ACTIVATED;
  }

  deactivate() {
    this.state = STATE.LISTENING;
  }
}

module.exports = new WakeDetector();
module.exports.STATE = STATE;
