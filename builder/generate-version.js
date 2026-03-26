// version情報, manifestSha256
const fs2 = require('fs');
const crypto2 = require('crypto');

function generateVersion(version, manifest, MANIFEST_PATH) {
    const manifestSha256 = crypto2.createHash('sha256').update(JSON.stringify(manifest)).digest('hex');
    const manifestSize = fs2.statSync(MANIFEST_PATH).size;
    return {
        version,
        manifestSha256,
        manifestSize
    };
}

module.exports = { generateVersion }