const fs2 = require("fs");
const path2 = require("path");
const crypto2 = require("crypto");

function walk(dir, baseDir) {
  let results = [];

  for (const file of fs2.readdirSync(dir)) {
    const fullPath = path2.join(dir, file);
    const stat = fs2.statSync(fullPath);

    if (stat.isDirectory()) {
      results = results.concat(walk(fullPath, baseDir));
    } else {
      results.push(fullPath);
    }
  }

  return results;
}

function sha256(filePath) {
  const data = fs2.readFileSync(filePath, "utf-8");
  const normalized = data.replace(/^\uFEFF/, "");
  return crypto2.createHash("sha256").update(normalized, "utf-8").digest("hex");
}

function toRelative(base, target) {
  return path2.relative(base, target).replace(/\\/g, "/");
}

function toLogicalId(relativePath) {
  return relativePath
    .replace(/^data\/imdf\//, "")
    .replace(/\//g, "_")
    .replace(/\.json$/, "");
}

function generateManifest(rootDir, version) {
  const files = walk(rootDir, rootDir);

  const manifestFiles = {};

  for (const file of files) {
    if (file.endsWith("manifest.json")) continue;

    const relativePath = toRelative(rootDir, file);
    const logicalId = toLogicalId(relativePath);

    const stat = fs2.statSync(file);

    manifestFiles[logicalId] = {
      logicalId,
      relativePath,
      sha256: sha256(file),
      size: stat.size,
    };
  }

  return {
    version,
    count: Object.keys(manifestFiles).length,
    totalSize: Object.values(manifestFiles).reduce(
      (sum, item) => sum + item.size,
      0,
    ),
    files: manifestFiles,
  };
}

module.exports = { generateManifest, sha256 };
