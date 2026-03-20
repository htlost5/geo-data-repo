// transform-geojson-to-json-full.js
const fs = require('fs');
const path = require('path');

// 入力: GeoJSONが置かれている場所
const INPUT_ROOT = 'D:\\htlost5_projects\\geo-data-repo\\exports\\raw';

// 出力: JSONを書き込む場所
const OUTPUT_ROOT = 'D:\\htlost5_projects\\geo-data-repo\\build\\imdf';

// 変更しないもの
const PRESERVE_FILES = new Set(['address.json']);
const PRESERVE_DIRS = new Set(['venue']);

// root直下に出す footprint 系の名前
// interact の表記が tree では "foorprint.json" になっていますが、
// もし誤記なら 'footprint.json' に直してください。
const FOOTPRINT_OUTPUT_NAME = {
  studyhall: 'footprint.json',
  interact: 'footprint.json', // ← tree を厳密に再現したいなら 'foorprint.json'
};

// -----------------------------
// 出力先を空にする（address.json と venue は残す）
// -----------------------------
function cleanOutputRoot(dir) {
  if (!fs.existsSync(dir)) return;

  const entries = fs.readdirSync(dir, { withFileTypes: true });
  for (const entry of entries) {
    const fullPath = path.join(dir, entry.name);

    if (entry.isDirectory()) {
      if (PRESERVE_DIRS.has(entry.name)) {
        console.log(`[SKIP DIR] ${fullPath}`);
        continue;
      }
      fs.rmSync(fullPath, { recursive: true, force: true });
      console.log(`[REMOVED DIR] ${fullPath}`);
      continue;
    }

    if (PRESERVE_FILES.has(entry.name)) {
      console.log(`[SKIP FILE] ${fullPath}`);
      continue;
    }

    fs.unlinkSync(fullPath);
    console.log(`[REMOVED FILE] ${fullPath}`);
  }
}

// -----------------------------
// GeoJSON -> JSON
// -----------------------------
function transformGeoJSONFile(inputPath, outputPath) {
  const raw = fs.readFileSync(inputPath, 'utf8');
  const data = JSON.parse(raw);

  if (data && Array.isArray(data.features)) {
    for (const feature of data.features) {
      if (feature?.properties && Object.prototype.hasOwnProperty.call(feature.properties, 'fid')) {
        delete feature.properties.fid;
      }
    }
  }

  const outDir = path.dirname(outputPath);
  fs.mkdirSync(outDir, { recursive: true });

  fs.writeFileSync(outputPath, JSON.stringify(data, null, 2), 'utf8');
  console.log(`[OK] ${inputPath} -> ${outputPath}`);
}

// -----------------------------
// 入力パスから出力パスへ変換
// -----------------------------
function mapOutputPath(inputPath) {
  const rel = path.relative(INPUT_ROOT, inputPath);
  const parts = rel.split(path.sep);
  const root = parts[0]; // studyhall / interact
  const fileName = path.parse(parts[parts.length - 1]).name;

  if (!['studyhall', 'interact'].includes(root)) return null;

  // address.json / venue は触らない
  if (fileName.toLowerCase() === 'address' || root === 'venue') return null;

  // studyhall / interact 直下の footprint.geojson
  if (fileName === 'footprint' || fileName === 'foorprint') {
    return path.join(OUTPUT_ROOT, root, 'footprint.json');
  }

  // stairs.geojson → root直下
  if (fileName === 'stairs') {
    return path.join(OUTPUT_ROOT, root, 'stairs.json');
  }

  // floors/floorN/units.geojson -> units/floorN.json
  if (parts[1] === 'floors' && parts.length >= 3) {
    const floorName = parts[2]; // floor1, floor2 ...
    if (fileName.toLowerCase() === 'units') {
      return path.join(OUTPUT_ROOT, root, 'units', `${floorName}.json`);
    }
    if (fileName.toLowerCase() === 'section') {
      return path.join(OUTPUT_ROOT, root, 'sections', `${floorName}.json`);
    }
  }

  // levels 以下は従来通り
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
      if (PRESERVE_DIRS.has(entry.name)) {
        console.log(`[SKIP DIR] ${fullPath}`);
        continue;
      }
      walk(fullPath);
      continue;
    }

    if (!entry.name.toLowerCase().endsWith('.geojson')) {
      continue;
    }

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

console.log('[START] Transforming .geojson -> .json...');
walk(INPUT_ROOT);

console.log('[DONE]');