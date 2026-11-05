const fs = require('fs');
const path = require('path');

const src = path.join(__dirname, 'frontend', 'dist');
const destPublic = path.join(__dirname, 'public');
const destDist = path.join(__dirname, 'dist');

if (fs.existsSync(src)) {
  fs.mkdirSync(destPublic, { recursive: true });
  fs.cpSync(src, destPublic, { recursive: true });

  fs.mkdirSync(destDist, { recursive: true });
  fs.cpSync(src, destDist, { recursive: true });
  console.log('[Build] Copied frontend/dist to public and dist successfully.');
} else {
  console.error('[Build Error] frontend/dist does not exist.');
  process.exit(1);
}
