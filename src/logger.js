const chalk = require('chalk');

// Clear the current line and write partial speech feedback
let lastPartialLength = 0;

const logger = {
  info(msg) {
    this.clearPartial();
    console.log(chalk.blue(`[INFO]  ${msg}`));
  },

  success(msg) {
    this.clearPartial();
    console.log(chalk.green(`[  OK]  ${msg}`));
  },

  warn(msg) {
    this.clearPartial();
    console.log(chalk.yellow(`[WARN]  ${msg}`));
  },

  error(msg) {
    this.clearPartial();
    console.error(chalk.red(`[ ERR]  ${msg}`));
  },

  // Shown when wake word is detected
  wake(msg) {
    this.clearPartial();
    console.log('\n' + chalk.magenta.bold(`🎤  ${msg}`) + '\n');
  },

  // Confirmed (final) speech result
  speech(text) {
    this.clearPartial();
    console.log(chalk.cyan(`[말씀]  "${text}"`));
  },

  // Partial in-progress transcription (overwrites same line)
  partial(text) {
    const line = chalk.gray(`[ ... ] ${text}`);
    const padded = line.padEnd(lastPartialLength + 10);
    process.stdout.write(`\r${padded}`);
    lastPartialLength = line.length;
  },

  clearPartial() {
    if (lastPartialLength > 0) {
      process.stdout.write('\r' + ' '.repeat(lastPartialLength + 10) + '\r');
      lastPartialLength = 0;
    }
  },

  section(msg) {
    this.clearPartial();
    console.log(chalk.white.bold(`\n${'─'.repeat(50)}\n  ${msg}\n${'─'.repeat(50)}\n`));
  },
};

module.exports = logger;
