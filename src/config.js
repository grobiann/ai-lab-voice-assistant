require('dotenv').config();
const path = require('path');

module.exports = {
  // Wake words that trigger activation
  WAKE_WORDS: (process.env.WAKE_WORDS || '클로드,claude,클로디')
    .split(',')
    .map((w) => w.trim().toLowerCase()),

  // Words that cancel activation and return to listening mode
  DEACTIVATE_WORDS: (process.env.DEACTIVATE_WORDS || '취소,그만,cancel,stop')
    .split(',')
    .map((w) => w.trim().toLowerCase()),

  // Vosk Korean model directory
  MODEL_PATH: process.env.MODEL_PATH
    ? path.resolve(process.env.MODEL_PATH)
    : path.join(__dirname, '../models/vosk-model-small-ko-0.22'),

  // Audio recording settings (Vosk requires 16kHz mono signed 16-bit PCM)
  SAMPLE_RATE: 16000,
  CHANNELS: 1,
  BIT_DEPTH: 16,

  // 'arecord' (ALSA/Linux) or 'sox'
  RECORD_PROGRAM: process.env.RECORD_PROGRAM || 'arecord',

  // null = system default device
  AUDIO_DEVICE: process.env.AUDIO_DEVICE || null,

  // Claude window search patterns
  CLAUDE_WINDOW_NAMES: (process.env.CLAUDE_WINDOW_NAMES || 'Claude,claude.ai')
    .split(',')
    .map((w) => w.trim()),

  // Optional path to Claude desktop app binary
  CLAUDE_APP_PATH: process.env.CLAUDE_APP_PATH || null,
};
