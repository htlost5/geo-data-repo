const fs = require('fs');
const path = require('path');
const archiver = require('archiver');
const { generateManifest } = require('./generate-manifest');

const version = process.argv[2];
if (!version) {
  console.error('Version required');
  process.exit(1);
}

// mainブランチ側のpath設定
const SRC_DIR = path.join(__dirname, '..', 'build', 'imdf');

// gh-pages(releases)ブランチ側のpath設定
const RELEASE_ROOT = path.join(__dirname, '..', 'releases', version);
const DATA_DIR = path.join(RELEASE_ROOT, 'data');
const DATA_IMDF_DIR = path.join(DATA_DIR, 'imdf');
const MANIFEST_PATH = path.join(DATA_DIR, 'manifest.json');
const ZIP_PATH = path.join(RELEASE_ROOT, `imdf-${version}.zip`);

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

function createZip(zipPath, dataDir) {
  return new Promise((resolve, reject) => {
    const output = fs.createWriteStream(zipPath);
    const archive = archiver('zip', { zlib: { level: 9 } });

    output.on('close', () => resolve());
    output.on('error', reject);
    archive.on('error', reject);

    archive.pipe(output);

    archive.directory(dataDir, 'data');

    archive.finalize();
  })
}


async function main() {
  fs.mkdirSync(DATA_DIR, { recursive: true });
  copyRecursive(SRC_DIR, DATA_IMDF_DIR);

  const manifest = generateManifest(RELEASE_ROOT, version);
  fs.writeFileSync(MANIFEST_PATH, JSON.stringify(manifest, null, 2));

  await createZip(ZIP_PATH, DATA_DIR);

  console.log(`Release ${version} built.`);
}

main().catch(err => {
  console.error(err);
  process.exit(1);
});