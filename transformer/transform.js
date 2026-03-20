// transform-geojson-to-json-gha.js
const fs = require('fs');
const path = require('path');

// -----------------------------
// 入力・出力パス
// -----------------------------
const INPUT_BUILD = path.join(__dirname, '..', 'exports', 'build'); // GitHub Actions用
const INPUT_BASE  = path.join(__dirname, '..', 'exports', 'base');  // venue / address.json
const OUTPUT_ROOT = path.join(__dirname, '..', 'build', 'imdf');     // 出力先

// -----------------------------
// root直下に出す footprint 系の名前
// -----------------------------
const FOOTPRINT_OUTPUT_NAME = {
  studyhall: 'footprint.json',
  interact:  'footprint.json', // tree に合わせて必要なら 'foorprint.json'
};

// -----------------------------
// 出力先を空にする（venue, address.jsonは残さず上書き）
// -----------------------------
function cleanOutputRoot(dir) {
  if (!fs.existsSync(dir)) return;
  const entries = fs.readdirSync(dir, { withFileTypes: true });
  for (const entry of entries) {
    fs.rmSync(path.join(dir, entry.name), { recursive: true, force: true });
    console.log(`[REMOVED] ${entry.name}`);
  }
}

// -----------------------------
// exports/base の venue と address.json をコピー
// -----------------------------
function copyBaseFiles() {
  // address.json
  const baseAddress = path.join(INPUT_BASE, 'address.json');
  if (fs.existsSync(baseAddress)) {
    fs.mkdirSync(OUTPUT_ROOT, { recursive: true });
    fs.copyFileSync(baseAddress, path.join(OUTPUT_ROOT, 'address.json'));
    console.log('[COPIED] address.json');
  }

  // venue フォルダ
  const baseVenue = path.join(INPUT_BASE, 'venue');
  const outVenue  = path.join(OUTPUT_ROOT, 'venue');
  if (fs.existsSync(baseVenue)) {
    fs.cpSync(baseVenue, outVenue, { recursive: true });
    console.log('[COPIED] venue/');
  }
}

// -----------------------------
// GeoJSON -> JSON
// -----------------------------
function transformGeoJSONFile(inputPath, outputPath) {
  const raw = fs.readFileSync(inputPath, 'utf8');
  const data = JSON.parse(raw);

  if (Array.isArray(data.features)) {
    for (const feature of data.features) {
      if (feature?.properties && Object.prototype.hasOwnProperty.call(feature.properties, 'fid')) {
        delete feature.properties.fid;
      }
    }
  }

  fs.mkdirSync(path.dirname(outputPath), { recursive: true });
  fs.writeFileSync(outputPath, JSON.stringify(data, null, 2), 'utf8');
  console.log(`[OK] ${inputPath} -> ${outputPath}`);
}

// -----------------------------
// 入力パスから出力パスへ変換
// -----------------------------
function mapOutputPath(inputPath) {
  const rel = path.relative(INPUT_BUILD, inputPath);
  const parts = rel.split(path.sep);
  const root = parts[0];
  const fileName = path.parse(parts[parts.length - 1]).name;

  if (!['studyhall', 'interact'].includes(root)) return null;

  // root直下 footprint / stairs
  if (fileName === 'footprint' || fileName === 'foorprint') {
    return path.join(OUTPUT_ROOT, root, 'footprint.json');
  }
  if (fileName === 'stairs') {
    return path.join(OUTPUT_ROOT, root, 'stairs.json');
  }

  // floors/floorN
  if (parts[1] === 'floors' && parts.length >= 3) {
    const floorName = parts[2];
    if (fileName.toLowerCase() === 'units') {
      return path.join(OUTPUT_ROOT, root, 'units', `${floorName}.json`);
    }
    if (fileName.toLowerCase() === 'section') {
      return path.join(OUTPUT_ROOT, root, 'sections', `${floorName}.json`);
    }
  }

  // levels 以下
  if (parts[1] === 'levels') {
    return path.join(OUTPUT_ROOT, root, 'levels', `${fileName}.json`);
  }

  return null;
}

// -----------------------------
// 再帰走査
// -----------------------------
function walk(dir) {
  const entries = fs.readdirSync(dir, { withFileTypes: true });

  for (const entry of entries) {
    const fullPath = path.join(dir, entry.name);

    if (entry.isDirectory()) {
      walk(fullPath);
      continue;
    }

    if (!entry.name.toLowerCase().endsWith('.geojson')) continue;

    const outputPath = mapOutputPath(fullPath);
    if (!outputPath) {
      console.log(`[SKIP] ${fullPath}`);
      continue;
    }

    transformGeoJSONFile(fullPath, outputPath);
  }
}

// -----------------------------
// 実行
// -----------------------------
console.log('[START] Cleaning output...');
cleanOutputRoot(OUTPUT_ROOT);

console.log('[START] Copy base files...');
copyBaseFiles();

console.log('[START] Transforming .geojson -> .json...');
walk(INPUT_BUILD);

console.log('[DONE]');