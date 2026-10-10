'use strict';
const fs = require('node:fs');
const path = require('node:path');
const { execFileSync } = require('node:child_process');
const { TextDecoder } = require('node:util');

const root = path.resolve(__dirname, '..');
const destination = path.join(root, 'tmp', 'github-snapshot');
const git = (...args) => execFileSync('git', args, { cwd: root, maxBuffer: 100 * 1024 * 1024 });
const action = process.argv[2];
if (action === 'prepare') {
  fs.mkdirSync(destination, { recursive: true });
  const entries = git('ls-files', '--stage', '-z').toString('utf8').split('\0').filter(Boolean);
  const records = entries.map(entry => {
    const match = /^(\d+) ([a-f0-9]+) 0\t([\s\S]+)$/.exec(entry);
    if (!match || match[1] === '160000') throw new Error('Unmerged index or submodule requires review');
    return match.slice(1);
  });
  const packed = execFileSync('git', ['cat-file', '--batch'], {
    cwd: root,
    input: records.map(record => record[1]).join('\n') + '\n',
    maxBuffer: 100 * 1024 * 1024,
  });
  let offset = 0;
  const manifest = { batches: [], binaries: [], files: 0, bytes: 0 };
  let batch = [], size = 0;
  const flush = () => {
    if (!batch.length) return;
    const name = `text-${manifest.batches.length}.json`;
    fs.writeFileSync(path.join(destination, name), JSON.stringify(batch));
    manifest.batches.push(name);
    batch = []; size = 0;
  };
  for (const [mode, sha, name] of records) {
    const newline = packed.indexOf(10, offset);
    const header = packed.subarray(offset, newline).toString('ascii').split(' ');
    if (header[0] !== sha || header[1] !== 'blob') throw new Error('Git object mismatch');
    const length = Number(header[2]);
    const bytes = packed.subarray(newline + 1, newline + 1 + length);
    offset = newline + length + 2;
    manifest.files++; manifest.bytes += bytes.length;
    let content;
    try {
      content = new TextDecoder('utf-8', { fatal: true }).decode(bytes);
      if (bytes.includes(0)) content = null;
    } catch { content = null; }
    if (content !== null) {
      if (/(?:ak-|sk-)[a-zA-Z0-9]{20,}/.test(content) || /BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY/.test(content)) {
        throw new Error(`Credential-like content requires review: ${name}`);
      }
      const item = { path: name, mode, type: 'blob', content };
      const length = Buffer.byteLength(JSON.stringify(item));
      if (size + length > 120000) flush();
      batch.push(item); size += length;
    } else {
      const filename = `binary-${manifest.binaries.length}.json`;
      fs.writeFileSync(path.join(destination, filename), JSON.stringify({ content: bytes.toString('base64'), encoding: 'base64' }));
      manifest.binaries.push({ path: name, mode, type: 'blob', filename, localSha: sha });
    }
  }
  flush();
  fs.writeFileSync(path.join(destination, 'manifest.json'), JSON.stringify(manifest));
  console.log(JSON.stringify({ files: manifest.files, bytes: manifest.bytes, batches: manifest.batches.length, binaries: manifest.binaries.length }));
} else if (action === 'read') {
  const name = process.argv[3];
  if (!/^(manifest|text-\d+|binary-\d+)\.json$/.test(name || '')) throw new Error('Invalid batch name');
  process.stdout.write(fs.readFileSync(path.join(destination, name)));
} else {
  throw new Error('Use prepare or read <batch.json>');
}
