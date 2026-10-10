const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const core = require('../desktop/core.cjs');
test('reject Docker option injection and malformed identifiers', () => {
  for (const value of ['--all',';whoami','a & calc','a\nb','', '../escape']) {
    assert.throws(() => core.containerId(value)); assert.throws(() => core.imageId(value));
  }
  for (const value of ['--all','nginx;whoami','a b','a\nb','$()']) assert.throws(() => core.imageRef(value));
  assert.equal(core.imageRef('registry.example:5000/team/app:v1'), 'registry.example:5000/team/app:v1');
  assert.equal(core.containerId('abc012345678'), 'abc012345678');
  assert.equal(core.imageId('sha256:'+'a'.repeat(64)), 'sha256:'+'a'.repeat(64));
});
test('SSH endpoints reject arguments, commands and invalid ports', () => {
  const base = { name:'Test',host:'example.invalid',user:'demo',port:22 };
  for (const patch of [{host:'-oProxyCommand=calc'},{host:'a;calc'},{user:'demo;calc'},{user:'-root'},{port:65536},{port:2.4},{key:'relative'}]) assert.throws(() => core.serverInput({...base,...patch}));
  assert.equal(core.serverInput(base).port,22);
  assert.equal(core.serverInput({...base,host:'2001:db8::1'}).host,'2001:db8::1');
});
test('SSH import never evaluates Include, Match exec, proxy commands or wildcard defaults', () => {
  const result = core.parseSshConfig('Include arbitrary\nHost *\n User root\nHost dev other\n HostName example.invalid\n User demo\n Port 2200\n IdentityFile "~/.ssh/id_ed25519"\n ProxyCommand calc.exe\nMatch exec "calc.exe"\n HostName attacker.invalid', 'C:\\Users\\test');
  assert.equal(result.servers.length,2);
  assert.equal(result.servers[0].host,'example.invalid');
  assert.equal(result.servers[1].user,'demo');
  assert.equal(result.servers[0].key,'C:\\Users\\test/.ssh/id_ed25519');
  assert.deepEqual(result.warnings,['include','wildcard','proxycommand','match']);
});
test('SSH paths support spaces and require existing absolute files', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(),'local-manager-unit-')); const file = path.join(dir,'test key');
  try { fs.writeFileSync(file,'synthetic'); assert.equal(core.serverInput({name:'n',host:'example.invalid',user:'demo',key:file}).key,file); }
  finally { fs.rmSync(file); fs.rmdirSync(dir); }
});
test('PowerShell quoting round trips shell metacharacters as inert data', async () => {
  const value = "space ' quote ; $env:USERNAME `n $(Get-Date) 中文";
  const actual = await core.ps(`ConvertTo-Json -InputObject ${core.quote(value)} -Compress`);
  assert.equal(JSON.parse(actual),value);
});
test('JSON line errors are not silently treated as an empty list', () => {
  assert.deepEqual(core.jsonLines('{"a":1}\r\n{"b":2}'),[{a:1},{b:2}]);
  assert.throws(() => core.jsonLines('daemon failure'));
});
