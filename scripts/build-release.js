const fs = require('fs');
const path = require('path');
const { generateManifest } = require('./generate-manifest');

const version = process.argv[2];
if (!version) {
  console.error('Version required');
  process.exit(1);
}

const SRC_DIR = path.join(__dirname, '..', 'src', 'imdf');

const RELEASE_ROOT = path.join(__dirname, '..', 'releases', version);
const RELEASE_IMDF_DIR = path.join(RELEASE_ROOT, 'imdf');

function copyRecursive(src, dest) {
  if (!fs.existsSync(dest)) fs.mkdirSync(dest, { recursive: true });

  for (const item of fs.readdirSync(src)) {
    const srcPath = path.join(src, item);
    const destPath = path.join(dest, item);

    const stat = fs.statSync(srcPath);

    if (stat.isDirectory()) {
      copyRecursive(srcPath, destPath);
    } else {
      fs.copyFileSync(srcPath, destPath);
    }
  }
}

// 1. copy src -> releases/version
copyRecursive(SRC_DIR, RELEASE_IMDF_DIR);

// 2. generate manifest
const manifest = generateManifest(RELEASE_ROOT, version);

fs.writeFileSync(
  path.join(RELEASE_ROOT, 'manifest.json'),
  JSON.stringify(manifest, null, 2)
);

console.log(`Release ${version} built.`);
