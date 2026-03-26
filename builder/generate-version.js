// version情報, manifestSha256
const fs2 = require("fs");
const { sha256 } = require("./generate-manifest");

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
