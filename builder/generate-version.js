// version情報, manifestSha256
const fs2 = require("fs");
const crypto2 = require("crypto");

function sha256(filePath) {
  const data = fs2.readFileSync(filePath, "utf-8");
  const normalized = data.replace(/^\uFEFF/, "");
  return crypto2.createHash("sha256").update(normalized, "utf-8").digest("hex");
}

function generateVersion(version, MANIFEST_PATH) {
  const manifestSha256 = sha256(MANIFEST_PATH);
  const manifestSize = fs2.statSync(MANIFEST_PATH).size;
  return {
    version,
    manifestSha256,
    manifestSize,
  };
}

module.exports = { generateVersion };
