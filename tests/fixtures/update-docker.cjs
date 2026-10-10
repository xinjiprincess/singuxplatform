// Test-only Docker replacement: never contacts a Docker daemon.
const fs = require('node:fs');
const path = require('node:path');
const args = process.argv.slice(2);
const root = process.env.TEST_ROOT;
fs.appendFileSync(path.join(root, 'calls.jsonl'), JSON.stringify(args) + '\n');
const old = (service) =>
  'sha256:' + (service === 'frontend' ? 'c' : 'd').repeat(64);
if (
  args[0] === 'compose' &&
  args.includes('config') &&
  args.includes('--format')
) {
  console.log(fs.readFileSync(path.join(root, 'deploy/compose.json'), 'utf8'));
} else if (args[0] === 'compose' && args.includes('ps')) {
  console.log(args.at(-1));
} else if (args[0] === 'inspect') {
  console.log(
    args.includes('{{.State.Status}}') ? 'running' : old(args.at(-1)),
  );
} else if (args.includes('exec')) {
  if (process.env.SCENARIO === 'backup-fail') process.exit(1);
  console.log('-- test SQL backup');
} else if (args.includes('up') && process.env.SCENARIO === 'health-fail') {
  const marker = path.join(root, 'failed-once');
  if (!fs.existsSync(marker)) {
    fs.writeFileSync(marker, 'yes');
    process.exit(1);
  }
}
