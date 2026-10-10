'use strict';
const { execFile } = require('node:child_process');
const path = require('node:path');
const fs = require('node:fs');
const os = require('node:os');
const POWERSHELL = path.join(process.env.SystemRoot || 'C:\\Windows', 'System32', 'WindowsPowerShell', 'v1.0', 'powershell.exe');
const SSH = path.join(process.env.SystemRoot || 'C:\\Windows', 'System32', 'OpenSSH', 'ssh.exe');
const KEYGEN = path.join(path.dirname(SSH), 'ssh-keygen.exe');
function run(file, args, timeout = 25000, includeStderr = false) {
  return new Promise((resolve, reject) => execFile(file, args, { windowsHide: true, timeout, maxBuffer: 12 * 1024 * 1024, encoding: 'utf8' }, (error, stdout, stderr) => {
    if (error) return reject(new Error((stderr || error.message).trim().slice(0, 1400)));
    resolve((includeStderr ? stdout + stderr : stdout).trim());
  }));
}
function ps(script) {
  const code = "[Console]::OutputEncoding=[System.Text.UTF8Encoding]::new();$ErrorActionPreference='Stop';" + script;
  return run(POWERSHELL, ['-NoProfile', '-NonInteractive', '-EncodedCommand', Buffer.from(code, 'utf16le').toString('base64')]);
}
function quote(value) { return "'" + String(value).replace(/'/g, "''") + "'"; }
function arrayJson(raw) { const value = JSON.parse(raw || '[]'); return Array.isArray(value) ? value : value ? [value] : []; }
function jsonLines(raw) { return raw.split(/\r?\n/).filter(Boolean).map(line => JSON.parse(line)); }
function imageId(id) { if (!/^sha256:[a-f0-9]{64}$/.test(id)) throw new Error('镜像 ID 无效，请刷新列表'); return id; }
function containerId(id) { if (!/^[a-f0-9]{12,64}$/.test(id)) throw new Error('容器 ID 无效，请刷新列表'); return id; }
function imageRef(ref) {
  if (typeof ref !== 'string' || ref.length > 250 || !/^[a-zA-Z0-9][a-zA-Z0-9._/:@-]*$/.test(ref)) throw new Error('镜像名称无效');
  return ref;
}
function serverInput(input) {
  if (!input || typeof input !== 'object') throw new Error('服务器配置无效');
  const name = String(input.name || '').trim();
  const host = String(input.host || '').trim();
  const user = String(input.user || '').trim();
  const port = Number(input.port || 22);
  if (!name || name.length > 100 || !/^[a-zA-Z0-9][a-zA-Z0-9.:-]{0,252}$/.test(host) || !/^[a-zA-Z0-9_][a-zA-Z0-9_.-]{0,63}$/.test(user) || !Number.isInteger(port) || port < 1 || port > 65535) throw new Error('请填写有效的名称、主机、用户名和端口');
  const key = String(input.key || '').trim();
  if (key && (!path.isAbsolute(key) || !fs.statSync(key).isFile())) throw new Error('密钥必须是已存在文件的绝对路径');
  return { name, host, user, port, key, group: String(input.group || '').slice(0, 80), note: String(input.note || '').slice(0, 600) };
}
function parseSshConfig(text, home = os.homedir()) {
  const result = []; const warnings = []; let block = null;
  for (const line of text.split(/\r?\n/)) {
    const match = line.trim().match(/^([\w]+)(?:\s*=\s*|\s+)(.*?)\s*$/);
    if (!match || line.trim().startsWith('#')) continue;
    const key = match[1].toLowerCase();
    const value = match[2].replace(/\s+#.*$/, '').replace(/^"(.*)"$/, '$1');
    if (key === 'include' || key === 'match') { warnings.push(key); if (key === 'match') block = null; continue; }
    if (key === 'host') {
      block = null;
      for (const alias of value.split(/\s+/)) {
        if (/[*?!]/.test(alias)) { warnings.push('wildcard'); continue; }
        const item = { name: alias, host: alias, user: '', port: 22, key: '', group: 'SSH config', note: '从 SSH config 导入；连接使用此处明确显示的参数。' };
        result.push(item); if (!block) block = []; block.push(item);
      }
    } else if (block) {
      for (const item of block) {
        if (key === 'hostname') item.host = value;
        if (key === 'user') item.user = value;
        if (key === 'port') item.port = Number(value);
        if (key === 'identityfile' && !item.key) item.key = value.replace(/^~(?=[/\\])/, home).replace(/%d/g, home);
        if (['proxycommand', 'proxyjump', 'localforward', 'remoteforward'].includes(key)) warnings.push(key);
      }
    }
  }
  return { servers: result, warnings: [...new Set(warnings)] };
}
// Every Docker command is pinned to a Windows named pipe. Never inherit DOCKER_HOST or a remote context.
async function localDockerEndpoint() {
  const docker = path.join(process.env.ProgramFiles || 'C:\\Program Files', 'Docker', 'Docker', 'resources', 'bin', 'docker.exe');
  const contexts = jsonLines(await run(docker, ['context', 'ls', '--format', '{{json .}}']));
  const endpoints = contexts.filter(c => ['desktop-linux', 'default', 'desktop-windows'].includes(c.Name))
    .sort((a, b) => Number(b.Current === true || b.Current === 'true') - Number(a.Current === true || a.Current === 'true'))
    .map(c => c.DockerEndpoint).filter(e => typeof e === 'string' && /^npipe:\/\/\/\/\.\/pipe\/[a-zA-Z0-9_.-]+$/.test(e));
  const errors = [];
  for (const endpoint of [...new Set(endpoints)]) {
    try { const version = await run(docker, ['--host', endpoint, 'version', '--format', '{{json .Server}}'], 6500); return { docker, endpoint, version: JSON.parse(version) }; }
    catch (e) { errors.push(e.message); }
  }
  throw new Error('未连接到本机 Docker 引擎。请启动 Docker Desktop。' + (errors[0] ? '\n' + errors[0].slice(0, 250) : ''));
}
function dockerRun(connection, args, timeout) { return run(connection.docker, ['--host', connection.endpoint, ...args], timeout, args[0] === 'logs'); }
module.exports = { run, ps, quote, arrayJson, jsonLines, imageId, containerId, imageRef, serverInput, parseSshConfig, localDockerEndpoint, dockerRun, POWERSHELL, SSH, KEYGEN };
