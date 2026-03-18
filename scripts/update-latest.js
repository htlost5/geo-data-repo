const fs3 = require('fs');
const path3 = require('path');

const versionArg = process.argv[2];
if (!versionArg) {
  console.error('Version required');
  process.exit(1);
}

const latestPath = path3.join(__dirname, '..', 'meta', 'latest.json');

const latest = {
  version: versionArg,
  manifest: `/releases/${versionArg}/manifest.json`
};

fs3.writeFileSync(latestPath, JSON.stringify(latest, null, 2));

console.log('latest.json updated');
