const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const crypto = require('node:crypto');
const { spawnSync } = require('node:child_process');
const bash =
  process.platform === 'win32'
    ? 'C:/Program Files/Git/bin/bash.exe'
    : '/bin/bash';
const shellPath = (p) =>
  process.platform === 'win32'
    ? p
        .replaceAll('\\', '/')
        .replace(/^([A-Z]):/i, (_, d) => '/' + d.toLowerCase())
    : p;
const newFrontend = 'sha256:' + 'a'.repeat(64);
const newBackend = 'sha256:' + 'b'.repeat(64);
const oldFrontend = 'sha256:' + 'c'.repeat(64);
const oldBackend = 'sha256:' + 'd'.repeat(64);

function run(scenario) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'singux-update-test-'));
  const deploy = path.join(root, 'deploy');
  const release = path.join(root, 'release');
  const bin = path.join(root, 'bin');
  for (const dir of [deploy, release, bin]) fs.mkdirSync(dir);
  const config = {
    name: 'test-only',
    services: {
      frontend: { image: oldFrontend, healthcheck: { test: ['CMD', 'true'] } },
      backend: { image: oldBackend, healthcheck: { test: ['CMD', 'true'] } },
      mysql: { image: 'mysql:8.4' },
    },
  };
  if (scenario === 'bind')
    config.services.backend.volumes = [
      { type: 'bind', source: '/code', target: '/app/app.jar' },
    ];
  if (scenario === 'nginx' || scenario === 'nginx-writable')
    config.services.frontend.volumes = [{
      type: 'bind', source: '/config/default.conf.template',
      target: '/etc/nginx/templates/default.conf.template',
      read_only: scenario === 'nginx',
    }];
  fs.writeFileSync(path.join(deploy, 'compose.json'), JSON.stringify(config));
  fs.writeFileSync(path.join(deploy, '.env'), 'TEST_ONLY=true\n');
  const archive = Buffer.from('not a real image archive; Docker is mocked');
  fs.writeFileSync(path.join(release, 'images.tar'), archive);
  const manifest = {
    release: 'test',
    mode: scenario === 'online' ? 'online' : 'offline',
    schemaUnchanged: scenario !== 'schema',
    dataBackwardCompatible: true,
    frontend: newFrontend,
    backend: newBackend,
    archiveSha256: crypto.createHash('sha256').update(archive).digest('hex'),
  };
  if (scenario === 'online') {
    manifest.frontend = 'example.invalid/frontend@' + newFrontend;
    manifest.backend = 'example.invalid/backend@' + newBackend;
  }
  if (scenario === 'checksum') manifest.archiveSha256 = '0'.repeat(64);
  fs.writeFileSync(path.join(release, 'update.json'), JSON.stringify(manifest));
  if (scenario === 'lock') fs.mkdirSync(path.join(deploy, '.update-lock'));
  const mock = path.resolve(__dirname, 'fixtures/update-docker.cjs');
  fs.writeFileSync(
    path.join(bin, 'docker'),
    '#!/bin/sh\nexec node "$MOCK_DOCKER" "$@"\n',
    { mode: 0o755 },
  );
  const result = spawnSync(
    bash,
    [
      '-c',
      'export PATH="$TEST_BIN:$PATH"; exec bash "$UPDATE_SCRIPT" "$DEPLOY" "$RELEASE"',
    ],
    {
      encoding: 'utf8',
      timeout: 30000,
      env: {
        ...process.env,
        TEST_BIN: shellPath(bin),
        MOCK_DOCKER: mock,
        UPDATE_SCRIPT: shellPath(
          path.resolve(__dirname, '../deploy/offline/update.sh'),
        ),
        DEPLOY: shellPath(deploy),
        RELEASE: shellPath(release),
        TEST_ROOT: root,
        SCENARIO: scenario,
      },
    },
  );
  const log = fs.existsSync(path.join(root, 'calls.jsonl'))
    ? fs.readFileSync(path.join(root, 'calls.jsonl'), 'utf8')
    : '';
  const current = JSON.parse(
    fs.readFileSync(path.join(deploy, 'compose.json'), 'utf8'),
  );
  const backups = fs.existsSync(path.join(deploy, 'backups'))
    ? fs.readdirSync(path.join(deploy, 'backups'))
    : [];
  // Each test owns this unique temporary fixture, never a project/deployment directory.
  assert.equal(path.dirname(path.resolve(root)), path.resolve(os.tmpdir()));
  assert.ok(path.basename(root).startsWith('singux-update-test-'));
  fs.rmSync(root, { recursive: true, force: true });
  return { result, log, current, backups };
}
for (const scenario of ['offline', 'online', 'nginx'])
  test(`updates ${scenario} images after backup`, () => {
    const { result, log, current, backups } = run(scenario);
    assert.equal(result.status, 0, result.stderr);
    assert.equal(backups.length, 1);
    assert.ok(log.indexOf('stop') < log.indexOf('mysqldump'));
    assert.ok(log.indexOf('mysqldump') < log.indexOf('"up"'));
    assert.ok(current.services.frontend.image.endsWith(newFrontend));
  });
for (const scenario of ['schema', 'checksum', 'lock', 'bind', 'nginx-writable'])
  test(`rejects ${scenario} before downtime`, () => {
    const { result, log, current } = run(scenario);
    assert.notEqual(result.status, 0);
    assert.ok(!log.includes('"stop"'));
    assert.equal(current.services.frontend.image, oldFrontend);
  });
for (const scenario of ['backup-fail', 'health-fail'])
  test(`restores previous images on ${scenario}`, () => {
    const { result, log, current } = run(scenario);
    assert.notEqual(result.status, 0);
    assert.ok(log.includes('"up"'));
    assert.equal(current.services.frontend.image, oldFrontend);
    assert.equal(current.services.backend.image, oldBackend);
  });
