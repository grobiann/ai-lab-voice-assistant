#!/usr/bin/env node
/**
 * scripts/download-model.js
 * Downloads the Vosk small Korean model (~82 MB) and extracts it to ./models/
 *
 * Usage: npm run download-model
 */

const https = require('https');
const http = require('http');
const fs = require('fs');
const path = require('path');
const AdmZip = require('adm-zip');

const MODEL_URL =
  'https://alphacephei.com/vosk/models/vosk-model-small-ko-0.22.zip';
const MODEL_ZIP = path.join(__dirname, '../models/vosk-model-small-ko-0.22.zip');
const MODEL_DIR = path.join(__dirname, '../models');

function ensureDir(dir) {
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
}

function download(url, dest, onProgress) {
  return new Promise((resolve, reject) => {
    const file = fs.createWriteStream(dest);
    const proto = url.startsWith('https') ? https : http;

    function get(u) {
      proto.get(u, (res) => {
        if (res.statusCode === 301 || res.statusCode === 302) {
          return get(res.headers.location);
        }
        if (res.statusCode !== 200) {
          return reject(new Error(`HTTP ${res.statusCode} — ${u}`));
        }

        const total = parseInt(res.headers['content-length'] || '0', 10);
        let downloaded = 0;

        res.on('data', (chunk) => {
          downloaded += chunk.length;
          if (total > 0 && onProgress) {
            onProgress(downloaded, total);
          }
        });

        res.pipe(file);
        file.on('finish', () => file.close(resolve));
        file.on('error', reject);
      }).on('error', reject);
    }

    get(url);
  });
}

async function main() {
  const targetDir = path.join(MODEL_DIR, 'vosk-model-small-ko-0.22');

  if (fs.existsSync(targetDir)) {
    console.log(`\n✓ Model already exists at: ${targetDir}`);
    console.log('  Delete the folder and re-run to re-download.\n');
    return;
  }

  ensureDir(MODEL_DIR);

  console.log(`\nDownloading Korean Vosk model from:\n  ${MODEL_URL}\n`);

  let lastPct = -1;
  await download(MODEL_URL, MODEL_ZIP, (done, total) => {
    const pct = Math.floor((done / total) * 100);
    if (pct !== lastPct && pct % 5 === 0) {
      process.stdout.write(`\r  ${pct}%  (${(done / 1e6).toFixed(1)} / ${(total / 1e6).toFixed(1)} MB)   `);
      lastPct = pct;
    }
  });

  console.log('\n\nExtracting...');
  const zip = new AdmZip(MODEL_ZIP);
  zip.extractAllTo(MODEL_DIR, true);

  fs.unlinkSync(MODEL_ZIP);

  console.log(`\n✓ Model extracted to: ${targetDir}`);
  console.log('  You can now run: npm start\n');
}

main().catch((err) => {
  console.error('\n✗ Download failed:', err.message);
  process.exit(1);
});
