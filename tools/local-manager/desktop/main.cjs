'use strict';
const { app, BrowserWindow, ipcMain, dialog, shell, safeStorage, clipboard } = require('electron');
const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');
const crypto = require('node:crypto');
const { spawn } = require('node:child_process');
const core = require('./core.cjs');
const { ps, quote: q, arrayJson, dockerRun } = core;
// The test profile is accepted only in explicitly launched development tests.
if (!app.isPackaged && process.env.LOCAL_MANAGER_TEST_DATA) app.setPath('userData', process.env.LOCAL_MANAGER_TEST_DATA);
let win, state, dataFile, dockerConnection;
let startupSnapshot = [], processSnapshot = [], keysSnapshot = [];
let previousCpu = new Map(), previousTime = 0;
const jobs = new Set();
const busy = new Set();
const empty = () => ({ servers: [], registryBackups: [], logs: [] });
function persist() {
  if (!safeStorage.isEncryptionAvailable()) throw new Error('Windows 用户加密不可用，不能保存配置');
  const bytes = safeStorage.encryptString(JSON.stringify(state));
  fs.writeFileSync(dataFile + '.tmp', bytes);
  fs.renameSync(dataFile + '.tmp', dataFile);
}
function audit(action, result) {
  state.logs.unshift({ time: new Date().toISOString(), action: String(action).slice(0, 150), result: String(result).slice(0, 250) });
  state.logs = state.logs.slice(0, 300); persist();
}
async function confirm(title, detail) {
  const { response } = await dialog.showMessageBox(win, { type: 'warning', title, message: title, detail, buttons: ['取消', '确认执行'], defaultId: 0, cancelId: 0, noLink: true });
  if (response !== 1) throw new Error('已取消');
}
async function connection() {
  if (!dockerConnection) dockerConnection = await core.localDockerEndpoint();
  return dockerConnection;
}
async function dockerList() {
  dockerConnection = null;
  const c = await connection();
  const results = await Promise.allSettled([
    dockerRun(c, ['ps', '-a', '--no-trunc', '--format', '{{json .}}']),
    dockerRun(c, ['image', 'ls', '--no-trunc', '--format', '{{json .}}']),
    dockerRun(c, ['stats', '--no-stream', '--format', '{{json .}}'])
  ]);
  if (results[0].status === 'rejected' || results[1].status === 'rejected') throw new Error('Docker 列表读取失败，请刷新重试');
  return { endpoint: c.endpoint, version: c.version.Version, containers: core.jsonLines(results[0].value), images: core.jsonLines(results[1].value), stats: results[2].status === 'fulfilled' ? core.jsonLines(results[2].value) : [], statsError: results[2].status === 'rejected' ? results[2].reason.message : '' };
}
async function systemList(mode) {
  // PowerShell cannot open a file inside app.asar. Read it through Electron's fs, then send encoded source.
  const source = fs.readFileSync(path.join(__dirname, 'system.ps1'), 'utf8').replace(/^\uFEFF/, '');
  const output = await ps(`& {${source}\n} -Mode ${q(mode)}`);
  return arrayJson(output);
}
async function processes() {
  const rows = await systemList('processes'); const now = Date.now();
  const elapsed = (now - previousTime) / 1000; const next = new Map();
  for (const p of rows) {
    const key = `${p.id}|${p.created}`; const prior = previousCpu.get(key);
    p.cpuPercent = prior === undefined || !previousTime ? null : Math.max(0, Math.min(100, (p.cpu - prior) / elapsed / os.cpus().length * 100));
    next.set(key, p.cpu);
  }
  previousCpu = next; previousTime = now; processSnapshot = rows;
  return rows;
}
async function startup() {
  const rows = await systemList('startup');
  for (const b of state.registryBackups) if (!rows.some(r => r.id === b.row.id)) rows.push({ ...b.row, enabled: false, managed: true });
  startupSnapshot = rows; return rows;
}
async function toggleStartup(id) {
  const row = startupSnapshot.find(r => r.id === id);
  if (!row || row.kind === 'notice') throw new Error('请先刷新开机项列表');
  await confirm(row.enabled ? '禁用开机项' : '恢复开机项', `${row.name}\n来源：${row.source}\n${row.command}`);
  if (row.kind === 'registry') {
    const b = state.registryBackups.find(b => b.row.id === id);
    if (b && !row.enabled) {
      await ps(`$p=${q(b.row.source)};$n=${q(b.row.name)};if(-not(Test-Path -LiteralPath $p)){throw '注册表路径已不存在'};$k=Get-Item -LiteralPath $p;if($k.GetValueNames() -contains $n){throw '同名开机项已存在，不能覆盖'};New-ItemProperty -LiteralPath $p -Name $n -Value ${q(b.value)} -PropertyType ${q(b.type)} -ErrorAction Stop|Out-Null`);
      state.registryBackups = state.registryBackups.filter(x => x !== b); persist();
    } else {
      if (!row.enabled) throw new Error('此项由 Windows 或其他工具禁用，请在任务管理器中恢复；本工具只恢复自己禁用的注册表项');
      const existing = JSON.parse(await ps(`$k=Get-Item -LiteralPath ${q(row.source)};$n=${q(row.name)};if($k.GetValueNames() -notcontains $n){throw '开机项已改变'};@{value=$k.GetValue($n,$null,[Microsoft.Win32.RegistryValueOptions]::DoNotExpandEnvironmentNames);type=$k.GetValueKind($n).ToString()}|ConvertTo-Json -Compress`));
      if (!['String', 'ExpandString'].includes(existing.type) || existing.value !== row.command) throw new Error('开机项已变化或类型不支持，请刷新');
      state.registryBackups = state.registryBackups.filter(x => x.row.id !== id);
      state.registryBackups.push({ row, ...existing }); persist(); // Backup before removal, survives interruption.
      await ps(`$k=Get-Item -LiteralPath ${q(row.source)};$n=${q(row.name)};if($k.GetValue($n,$null,[Microsoft.Win32.RegistryValueOptions]::DoNotExpandEnvironmentNames) -cne ${q(existing.value)}){throw '开机项已变化'};Remove-ItemProperty -LiteralPath ${q(row.source)} -Name $n -ErrorAction Stop`);
    }
  } else if (row.kind === 'folder') {
    const source = path.resolve(row.command); const root = path.resolve(row.source); const disabled = path.join(root, 'LocalManager.Disabled');
    if (![root, disabled].includes(path.dirname(source))) throw new Error('启动项目录不匹配');
    const target = path.join(row.enabled ? disabled : root, path.basename(source));
    if (fs.existsSync(target)) throw new Error('目标文件已存在，不能覆盖');
    fs.mkdirSync(path.dirname(target), { recursive: true }); fs.renameSync(source, target);
  } else if (row.kind === 'task') {
    await ps(`$task=Get-ScheduledTask -TaskPath ${q(row.source)} -TaskName ${q(row.name)};$eligible=@($task.Triggers|Where-Object {$_.CimClass.CimClassName -in @('MSFT_TaskBootTrigger','MSFT_TaskLogonTrigger')});if($eligible.Count -eq 0){throw '任务触发器已变化'};$cmd=($task.Actions|ForEach-Object {"$($_.Execute) $($_.Arguments)"}) -join '; ';if($cmd -cne ${q(row.command)}){throw '任务动作已变化，请刷新'};${row.enabled ? 'Disable' : 'Enable'}-ScheduledTask -TaskPath ${q(row.source)} -TaskName ${q(row.name)}|Out-Null`);
  }
  audit(`${row.enabled ? '禁用' : '恢复'}开机项：${row.name}`, '成功');
  return startup();
}
async function sshInventory() {
  const dir = path.join(os.homedir(), '.ssh'); const keys = [];
  if (fs.existsSync(dir)) {
    for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
      if (!entry.isFile() || /^(config|known_hosts|authorized_keys)(\.|$)/i.test(entry.name) || entry.name.endsWith('.pub')) continue;
      const file = path.join(dir, entry.name); const stat = fs.statSync(file);
      if (stat.size > 65536) continue;
      const fd = fs.openSync(file, 'r'); const head = Buffer.alloc(150); fs.readSync(fd, head, 0, head.length, 0); fs.closeSync(fd);
      if (!/-----BEGIN (OPENSSH|RSA|EC|DSA|ENCRYPTED)? ?PRIVATE KEY-----/.test(head.toString())) continue;
      const publicFile = file + '.pub'; let fingerprint = '缺少公钥文件';
      if (fs.existsSync(publicFile)) { try { fingerprint = await core.run(core.KEYGEN, ['-l', '-f', publicFile]); } catch { fingerprint = '公钥无法解析'; } }
      keys.push({ name: entry.name, path: file, publicFile: fs.existsSync(publicFile) ? publicFile : '', fingerprint });
    }
  }
  let agent;
  try { agent = await core.run(path.join(path.dirname(core.SSH), 'ssh-add.exe'), ['-l'], 4000); } catch (e) { agent = 'SSH agent 无密钥或不可用'; }
  keysSnapshot = keys;
  return { dir, keys, agent, servers: state.servers };
}
function sshArgs(s, test = false) {
  // Ignore implicit config commands/forwarding. Import only explicit supported fields.
  return ['-F', 'NUL', '-o', 'StrictHostKeyChecking=ask', '-o', 'ForwardAgent=no', '-o', 'ClearAllForwardings=yes', '-o', 'PermitLocalCommand=no', '-o', 'ConnectTimeout=8', ...(test ? ['-o', 'BatchMode=yes'] : []), '-p', String(s.port), ...(s.key ? ['-i', s.key, '-o', 'IdentitiesOnly=yes'] : []), `${s.user}@${s.host}`, ...(test ? ['exit', '0'] : [])];
}
const actions = {
  state: async () => ({ servers: state.servers, logs: state.logs, profile: app.getPath('userData'), version: app.getVersion() }),
  overview: async () => ({ totalMemory: os.totalmem(), freeMemory: os.freemem(), hostname: os.hostname(), platform: `${os.type()} ${os.release()}`, cpus: os.cpus().length, uptime: os.uptime() }),
  dockerList,
  dockerAction: async input => {
    const kind = input?.kind; const id = core.containerId(input?.id || '');
    if (!['start', 'stop', 'restart', 'rm', 'logs', 'inspect'].includes(kind)) throw new Error('不支持的操作');
    const c = await connection();
    if (kind === 'logs') return dockerRun(c, ['logs', '--tail', '250', '--timestamps', id]);
    if (kind === 'inspect') {
      const obj = JSON.parse(await dockerRun(c, ['inspect', id]))[0];
      return JSON.stringify({ Name: obj.Name, State: { Status: obj.State.Status, StartedAt: obj.State.StartedAt }, Image: obj.Config.Image, Ports: obj.NetworkSettings.Ports, Mounts: obj.Mounts, Compose: obj.Config.Labels?.['com.docker.compose.project'] }, null, 2);
    }
    const info = JSON.parse(await dockerRun(c, ['inspect', id]))[0];
    await confirm({ start: '启动容器', stop: '停止容器', restart: '重启容器', rm: '删除容器' }[kind], `${info.Name}\n${id}\n${kind === 'rm' ? '仅删除已停止的容器，不删除数据卷；容器可写层会丢失。' : '操作会改变本机容器状态。'}`);
    await dockerRun(c, [kind, id]); audit(`Docker ${kind} ${info.Name}`, '成功'); return true;
  },
  imageAction: async input => {
    const c = await connection(); const kind = input?.kind;
    if (kind === 'pull') { const ref = core.imageRef(input.ref); await dockerRun(c, ['pull', ref], 600000); audit(`拉取镜像 ${ref}`, '成功'); return true; }
    if (kind === 'load') {
      const file = await dialog.showOpenDialog(win, { title: '导入 Docker 镜像归档', properties: ['openFile'], filters: [{ name: '镜像归档', extensions: ['tar'] }] });
      if (file.canceled) return false;
      await confirm('导入镜像', file.filePaths[0]); await dockerRun(c, ['load', '-i', file.filePaths[0]], 600000); audit('导入 Docker 镜像', '成功'); return true;
    }
    const id = core.imageId(input?.id || '');
    if (kind === 'rm') { await confirm('删除 Docker 镜像', `${id}\n不使用强制删除；被容器依赖的镜像可能无法删除。`); await dockerRun(c, ['image', 'rm', id]); audit(`删除镜像 ${id.slice(0, 22)}`, '成功'); return true; }
    if (kind === 'save') {
      const out = await dialog.showSaveDialog(win, { title: '导出 Docker 镜像', defaultPath: 'docker-image.tar', filters: [{ name: 'Docker TAR', extensions: ['tar'] }] });
      if (out.canceled) return false;
      const ref = input.ref && input.ref !== '<none>:<none>' ? core.imageRef(input.ref) : id;
      const temp = out.filePath + '.local-manager-' + crypto.randomUUID() + '.tmp';
      try { await dockerRun(c, ['save', '-o', temp, ref], 600000); fs.renameSync(temp, out.filePath); } finally { if (fs.existsSync(temp)) fs.unlinkSync(temp); }
      audit('导出 Docker 镜像', '成功'); return true;
    }
    throw new Error('不支持的镜像操作');
  },
  processes,
  endProcess: async input => {
    const item = processSnapshot.find(p => p.id === Number(input?.id) && p.created === input.created);
    if (!item || !item.created) throw new Error('进程信息已失效，请刷新');
    const protectedNames = /^(System|Registry|Secure System|Memory Compression|smss|csrss|wininit|winlogon|services|lsass|svchost|Local-Manager|electron)(\.exe)?$/i;
    if (item.id <= 4 || item.id === process.pid || protectedNames.test(item.name)) throw new Error('此进程受保护，不能由本工具结束');
    await confirm('结束进程', `${item.name} · PID ${item.id}\n${item.path || ''}\n这会强制结束进程，未保存的内容可能丢失。`);
    await ps(`$p=Get-CimInstance Win32_Process -Filter 'ProcessId=${item.id}';if(-not $p -or $p.CreationDate.ToUniversalTime().ToString('o') -ne ${q(item.created)}){throw '原进程已退出或 PID 已复用，请刷新'};$r=Invoke-CimMethod -InputObject $p -MethodName Terminate;if($r.ReturnValue -ne 0){throw "结束失败，错误码 $($r.ReturnValue)，可能需要管理员权限"}`);
    audit(`结束进程 ${item.name} (${item.id})`, '成功'); return true;
  },
  processFolder: async input => {
    const item = processSnapshot.find(p => p.id === Number(input?.id) && p.created === input.created);
    if (!item?.path) throw new Error('无法读取此进程路径'); shell.showItemInFolder(item.path); return true;
  },
  services: () => systemList('services'),
  startup,
  toggleStartup,
  sshInventory,
  chooseKey: async () => { const r = await dialog.showOpenDialog(win, { title: '选择已有 SSH 私钥', defaultPath: path.join(os.homedir(), '.ssh'), properties: ['openFile'] }); return r.canceled ? '' : r.filePaths[0]; },
  saveServer: async input => {
    const s = core.serverInput(input); const existing = state.servers.find(x => x.id === input.id);
    if (existing) Object.assign(existing, s); else state.servers.push({ ...s, id: crypto.randomUUID() });
    persist(); audit(`保存服务器 ${s.name}`, '成功'); return state.servers;
  },
  deleteServer: async id => { const s = state.servers.find(x => x.id === id); if (!s) throw new Error('服务器不存在'); await confirm('移除服务器配置', `${s.name}\n仅移除本工具中的配置，不删除私钥或远端内容。`); state.servers = state.servers.filter(x => x.id !== id); persist(); return true; },
  importSsh: async () => {
    const file = path.join(os.homedir(), '.ssh', 'config');
    if (!fs.existsSync(file)) throw new Error('本机没有 ~/.ssh/config，可手动添加服务器');
    const parsed = core.parseSshConfig(fs.readFileSync(file, 'utf8')); let count = 0, skipped = 0;
    for (const s of parsed.servers) {
      try { const value = core.serverInput(s); if (state.servers.some(x => x.name === value.name)) { skipped++; continue; } state.servers.push({ ...value, id: crypto.randomUUID() }); count++; } catch { skipped++; }
    }
    persist(); audit('导入 SSH 配置', `新增 ${count}，跳过 ${skipped}`);
    return { count, skipped, warnings: parsed.warnings };
  },
  sshConnect: async id => {
    const s = state.servers.find(x => x.id === id); if (!s) throw new Error('服务器不存在'); core.serverInput(s);
    const script = `& ${q(core.SSH)} ${sshArgs(s).map(q).join(' ')};Write-Host '\nSSH 会话已结束。';Read-Host '按 Enter 关闭窗口'`;
    const child = spawn(core.POWERSHELL, ['-NoProfile', '-EncodedCommand', Buffer.from(script, 'utf16le').toString('base64')], { detached: true, windowsHide: false, stdio: 'ignore' });
    await new Promise((resolve, reject) => { child.once('spawn', resolve); child.once('error', reject); }); child.unref();
    audit(`打开 SSH 终端 ${s.name}`, '已启动；连接结果请在终端查看'); return true;
  },
  sshTest: async id => {
    const s = state.servers.find(x => x.id === id); if (!s) throw new Error('服务器不存在'); core.serverInput(s);
    try { await core.run(core.SSH, sshArgs(s, true), 15000); return '认证成功，服务器可连接。'; }
    catch (e) { throw new Error('连接未通过：' + e.message + '\n首次连接需要在终端核对主机指纹；加密私钥可先在终端输入口令或加载到 SSH agent。'); }
  },
  copyPublicKey: async keyPath => {
    const k = keysSnapshot.find(x => x.path === keyPath); if (!k?.publicFile) throw new Error('没有对应公钥文件');
    clipboard.writeText(fs.readFileSync(k.publicFile, 'utf8')); return true;
  },
  generateKey: async () => {
    const dir = path.join(os.homedir(), '.ssh'); fs.mkdirSync(dir, { recursive: true });
    const file = await dialog.showSaveDialog(win, { title: '选择新 SSH 密钥保存位置（终端中设置口令）', defaultPath: path.join(dir, 'id_ed25519_local') });
    if (file.canceled) return false;
    if (fs.existsSync(file.filePath) || fs.existsSync(file.filePath + '.pub')) throw new Error('密钥文件已存在，不能覆盖');
    const script = `& ${q(core.KEYGEN)} -t ed25519 -f ${q(file.filePath)};Read-Host '按 Enter 关闭窗口'`;
    const child = spawn(core.POWERSHELL, ['-NoProfile', '-EncodedCommand', Buffer.from(script, 'utf16le').toString('base64')], { detached: true, windowsHide: false, stdio: 'ignore' });
    await new Promise((resolve, reject) => { child.once('spawn', resolve); child.once('error', reject); }); child.unref(); return true;
  },
  openTaskManager: async () => { await core.run(path.join(process.env.SystemRoot, 'System32', 'cmd.exe'), ['/d', '/c', 'start', '', 'taskmgr.exe']); return true; }
};
app.whenReady().then(async () => {
  dataFile = path.join(app.getPath('userData'), 'local-manager.enc'); fs.mkdirSync(path.dirname(dataFile), { recursive: true });
  try { state = fs.existsSync(dataFile) ? JSON.parse(safeStorage.decryptString(fs.readFileSync(dataFile))) : empty(); }
  catch { dialog.showErrorBox('配置无法解密', '原配置已保留。请使用原 Windows 用户打开；本工具不会覆盖无法读取的配置。'); app.quit(); return; }
  win = new BrowserWindow({ width: 1360, height: 880, minWidth: 1050, minHeight: 680, title: '本机管理中心', backgroundColor: '#0c1321', webPreferences: { preload: path.join(__dirname, 'preload.cjs'), contextIsolation: true, nodeIntegration: false, sandbox: true } });
  win.setMenuBarVisibility(false);
  win.webContents.setWindowOpenHandler(() => ({ action: 'deny' }));
  win.webContents.on('will-navigate', e => e.preventDefault());
  win.webContents.session.setPermissionRequestHandler((_wc, _permission, callback) => callback(false));
  ipcMain.handle('manager', async (event, request) => {
    if (event.sender !== win.webContents || event.senderFrame !== win.webContents.mainFrame || !Object.hasOwn(actions, request?.name)) return { ok: false, error: '请求被拒绝' };
    const name = request.name;
    if (busy.has(name)) return { ok: false, error: '该操作仍在执行，请稍候' };
    busy.add(name); jobs.add(name);
    try { return { ok: true, data: await actions[name](request.input) }; }
    catch (e) { return { ok: false, error: e.message }; }
    finally { busy.delete(name); jobs.delete(name); }
  });
  win.on('close', event => { if (jobs.size) { event.preventDefault(); dialog.showMessageBox(win, { type: 'info', message: '后台操作尚未结束，请完成后再关闭窗口。', detail: [...jobs].join(', ') }); } });
  await win.loadFile(path.join(__dirname, '../ui/index.html'));
});
app.on('window-all-closed', () => app.quit());
