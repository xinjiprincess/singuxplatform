'use strict';
const $ = selector => document.querySelector(selector);
const esc = value => String(value ?? '').replace(/[&<>"']/g, char => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[char]);
const bytes = value => { if (!Number.isFinite(Number(value))) return '—'; let n = Number(value); let i = 0; while (n >= 1024 && i < 3) { n /= 1024; i++; } return `${n.toFixed(i ? 1 : 0)} ${['B','KB','MB','GB'][i]}`; };
const pages = { overview: ['总览', '查看本机资源，快速进入你的工作空间'], docker: ['Docker', '管理本机镜像和容器，查看状态、日志与资源占用'], ssh: ['SSH 与服务器', '整理本机密钥，一键连接你的服务器'], startup: ['开机项', '查看启动来源，禁用与恢复开机启动'], processes: ['运行程序', '找到 CPU 和内存占用来源，管理运行中的程序'], services: ['Windows 服务', '只读查看服务状态、启动方式与所属进程'], logs: ['操作记录', '查看本工具执行的操作，以及本地配置位置'] };
let page = 'overview', dockerTab = 'containers', data = null, query = '', sortKey = 'memory', renderId = 0, refreshTimer, inAction = false;
const api = (name, input) => window.localManager.invoke(name, input);
function notice(message, error = false) { $('#notice').textContent = message; $('#notice').className = 'notice' + (error ? ' error' : ''); }
function clearNotice() { $('#notice').className = 'notice hidden'; }
function details(title, text) { $('#detailTitle').textContent = title; $('#detailText').textContent = text; $('#details').showModal(); }
function button(label, action, id = '', cls = 'ghost', extra = '') { return `<button class="button small ${cls}" data-action="${esc(action)}" data-id="${esc(id)}" ${extra}>${esc(label)}</button>`; }
function badge(label, color = '') { return `<span class="badge ${color}">${esc(label)}</span>`; }
function table(headers, rows) { return `<div class="table-wrap"><table><thead><tr>${headers.map(h => `<th>${h}</th>`).join('')}</tr></thead><tbody>${rows.join('') || `<tr><td colspan="${headers.length}" class="empty">没有符合条件的记录</td></tr>`}</tbody></table></div><div class="row-count">当前显示 ${rows.length} 条</div>`; }
function search(placeholder = '搜索名称、路径…') { return `<input class="search" id="search" aria-label="搜索列表" placeholder="${esc(placeholder)}" value="${esc(query)}">`; }
function matches(value) { return JSON.stringify(value).toLowerCase().includes(query.toLowerCase()); }
async function load(silent = false) {
  const id = ++renderId; const target = page;
  $('#refresh').disabled = true;
  if (!silent) { clearNotice(); $('#content').innerHTML = '<div class="loading">正在读取本机数据…</div>'; }
  try {
    const action = { overview: 'overview', docker: 'dockerList', ssh: 'sshInventory', startup: 'startup', processes: 'processes', services: 'services', logs: 'state' }[target];
    const result = await api(action);
    if (id !== renderId) return;
    data = result; render(); $('#updated').textContent = '更新于 ' + new Date().toLocaleTimeString();
  } catch (e) {
    if (id !== renderId) return;
    if (!silent) $('#content').innerHTML = '<div class="card empty">暂时无法读取数据。<br>查看上方提示，处理后点击刷新重试。</div>';
    notice(e.message, true);
  } finally { if (id === renderId) $('#refresh').disabled = false; }
}
function navigate(next) {
  page = next; query = ''; clearInterval(refreshTimer);
  document.querySelectorAll('nav button').forEach(b => b.classList.toggle('active', b.dataset.page === next));
  $('#title').textContent = pages[next][0]; $('#subtitle').textContent = pages[next][1]; load();
  if (['processes','overview'].includes(next)) refreshTimer = setInterval(() => { if (!inAction && !document.querySelector('dialog[open]') && !$('#search')?.matches(':focus')) load(true); }, 6000);
}
function render() {
  if (!data) return;
  const content = $('#content');
  if (page === 'overview') {
    const used = data.totalMemory - data.freeMemory; const percent = used / data.totalMemory * 100;
    content.innerHTML = `<div class="grid metrics">
      <div class="card"><div class="card-label">内存使用率</div><div class="metric">${percent.toFixed(0)}<small> %</small></div><div class="metric-note">${bytes(used)} / ${bytes(data.totalMemory)}</div><div class="progress"><progress max="100" value="${percent}"></progress></div></div>
      <div class="card"><div class="card-label">可用内存</div><div class="metric">${esc(bytes(data.freeMemory))}</div><div class="metric-note">系统当前可用物理内存</div></div>
      <div class="card"><div class="card-label">逻辑处理器</div><div class="metric">${data.cpus}<small> 核</small></div><div class="metric-note">进程 CPU 按全部逻辑核归一化</div></div>
      <div class="card"><div class="card-label">本次运行时间</div><div class="metric">${Math.floor(data.uptime / 3600)}<small> 小时</small></div><div class="metric-note">${esc(data.hostname)}</div></div>
    </div><div class="section-heading"><h2>管理工作空间</h2><p>${esc(data.platform)}</p></div><div class="grid quick-grid">
      ${[['docker','▦','Docker','镜像、容器、运行日志与端口挂载'],['ssh','⌁','SSH 与服务器','已有密钥、服务器分组与终端连接'],['startup','↗','开机项','启动目录、注册表与登录计划任务'],['processes','▥','运行程序','内存与 CPU 排序、路径和进程详情']].map(([p, icon, title, desc]) => `<div class="card quick-card"><span class="quick-icon">${icon}</span><div class="quick-text"><h3>${title}</h3><p>${desc}</p></div><button class="button" data-page="${p}">打开 →</button></div>`).join('')}
    </div><div class="info-strip key-section">本工具按需读取本机信息。涉及停止、删除或禁用的操作会展示系统确认框。系统范围的开机项若权限不足，可退出后以管理员身份运行。</div>`;
  } else if (page === 'docker') renderDocker();
  else if (page === 'processes') renderProcesses();
  else if (page === 'startup') {
    const rows = data.filter(matches).map(r => `<tr><td><div class="name">${esc(r.name)}</div><div class="sub">${esc(r.source)}</div></td><td>${badge({registry:'注册表',folder:'启动目录',task:'计划任务',notice:'读取提示'}[r.kind])}</td><td>${badge(r.enabled ? '已启用' : '已禁用', r.enabled ? 'green' : 'gray')}</td><td><div class="sub">${esc(r.command)}</div></td><td>${r.kind === 'notice' ? '' : !r.enabled && r.kind === 'registry' && !r.managed ? badge('请在系统中恢复','gray') : r.externallyDisabled ? badge('请在系统中恢复','gray') : button(r.enabled ? '禁用' : '恢复','toggle-startup',r.id,r.enabled ? 'ghost' : '')}</td></tr>`);
    content.innerHTML = `<div class="info-strip">禁用的启动目录文件保留在原目录下的 LocalManager.Disabled 文件夹；注册表原值加密备份。已由其他工具禁用的注册表项请在任务管理器中恢复。计划任务可能需要管理员权限。</div><div class="toolbar">${search()}<span class="spacer"></span>${button('打开任务管理器','task-manager','','')}</div>${table(['名称 / 来源','类型','状态','执行内容','操作'],rows)}`;
  } else if (page === 'services') {
    content.innerHTML = `<div class="toolbar">${search('搜索服务名称、PID…')}<span class="spacer"></span>${badge('只读')}</div>${table(['服务名称','显示名称','状态','启动方式','PID'],data.filter(matches).map(s => `<tr><td class="mono">${esc(s.Name)}</td><td>${esc(s.DisplayName)}</td><td>${badge(s.State,s.State === 'Running' ? 'green' : 'gray')}</td><td>${esc(s.StartMode)}</td><td>${s.ProcessId}</td></tr>`))}`;
  } else if (page === 'ssh') renderSsh();
  else if (page === 'logs') {
    content.innerHTML = `<div class="info-strip">版本 ${esc(data.version)} · 配置与操作记录使用 Windows 用户加密保存。<br>配置目录：${esc(data.profile)}<br>这里记录本工具完成的操作，不代表其他程序的活动历史。SSH 终端启动记录不代表登录成功。</div><div class="toolbar">${search('搜索操作记录…')}</div>${table(['时间','操作','结果'],data.logs.filter(matches).map(l => `<tr><td>${esc(new Date(l.time).toLocaleString())}</td><td>${esc(l.action)}</td><td>${esc(l.result)}</td></tr>`))}`;
  }
}
function renderDocker() {
  const containers = dockerTab === 'containers';
  const rows = (containers ? data.containers : data.images).filter(matches);
  $('#content').innerHTML = `<div class="info-strip">${badge('本机连接','green')} &nbsp; ${esc(data.endpoint)} &nbsp; · &nbsp; Docker ${esc(data.version)}${data.statsError ? '<br>资源统计暂不可用，容器与镜像列表仍可查看。' : ''}</div>
    <div class="tabs"><button data-tab="containers" class="${containers ? 'active' : ''}">容器 (${data.containers.length})</button><button data-tab="images" class="${containers ? '' : 'active'}">镜像 (${data.images.length})</button></div>
    <div class="toolbar">${search('搜索名称、镜像、Compose 项目…')}<span class="spacer"></span>${containers ? '' : `${button('拉取镜像','pull','','')}${button('导入 TAR','load-image','','')}`}</div>`;
  if (containers) {
    $('#content').innerHTML += table(['容器 / Compose 项目','状态','资源占用','端口','操作'],rows.map(c => {
      const stat = data.stats.find(s => c.ID.startsWith(s.ID || s.Container));
      const project = String(c.Labels || '').split(',').find(x => x.startsWith('com.docker.compose.project='))?.split('=')[1];
      return `<tr><td><div class="name">${esc(c.Names)}</div><div class="sub">${esc(c.Image)}</div>${project ? badge(project) : ''}</td><td>${badge(c.State,c.State === 'running' ? 'green' : 'gray')}<div class="sub">${esc(c.Status)}</div></td><td>${stat ? `<div>CPU ${esc(stat.CPUPerc)}</div><div class="sub">${esc(stat.MemUsage)}</div>` : '—'}</td><td class="sub">${esc(c.Ports || '未公开端口')}</td><td><div class="actions">${c.State === 'running' ? button('停止','stop',c.ID) + button('重启','restart',c.ID) : button('启动','start',c.ID)}${button('日志','container-logs',c.ID)}${button('详情','inspect',c.ID)}${c.State === 'running' ? '' : button('删除','rm',c.ID,'danger')}</div></td></tr>`;
    }));
  } else {
    $('#content').innerHTML += table(['镜像 / 标签','镜像 ID','大小','创建时间','操作'],rows.map(i => `<tr><td><div class="name">${esc(i.Repository)}</div>${badge(i.Tag)}</td><td class="mono sub">${esc(i.ID.slice(0, 26))}…</td><td>${esc(i.Size)}</td><td>${esc(i.CreatedSince)}</td><td><div class="actions">${button('导出','save-image',i.ID,'ghost',`data-ref="${esc(i.Repository + ':' + i.Tag)}"`)}${button('删除','rm-image',i.ID,'danger')}</div></td></tr>`));
  }
}
function renderProcesses() {
  const rows = data.filter(matches).sort((a,b) => sortKey === 'name' ? a.name.localeCompare(b.name) : (b[sortKey] || 0) - (a[sortKey] || 0));
  $('#content').innerHTML = `<div class="toolbar">${search('搜索程序、PID、命令行…')}<select id="sort" aria-label="排序"><option value="memory" ${sortKey === 'memory' ? 'selected' : ''}>按内存从高到低</option><option value="cpuPercent" ${sortKey === 'cpuPercent' ? 'selected' : ''}>按 CPU 从高到低</option><option value="name" ${sortKey === 'name' ? 'selected' : ''}>按名称</option></select><span class="spacer"></span>${badge('每 6 秒刷新')}</div>
    <div class="info-strip">CPU 需要两次采样，首次显示“采样中”；内存为工作集，多个进程可能共享内存，不能简单相加。输入搜索或查看详情时暂停自动刷新。系统保护进程不可结束。</div>
    ${table(['程序名称','PID','CPU','内存工作集','操作'],rows.map(p => `<tr><td><div class="name">${esc(p.name)}</div><div class="sub">${esc(p.path || '系统进程或权限不足')}</div></td><td>${p.id}</td><td>${p.cpuPercent === null ? '采样中' : p.cpuPercent.toFixed(1) + '%'}</td><td>${bytes(p.memory)}</td><td><div class="actions">${button('详情','process-details',p.id)}${p.path ? button('打开目录','process-folder',p.id) : ''}${button('结束','end-process',p.id,'danger')}</div></td></tr>`))}`;
}
function renderSsh() {
  $('#content').innerHTML = `<div class="toolbar">${search('搜索服务器、地址、分组…')}<span class="spacer"></span>${button('导入 SSH config','import-ssh','','')}${button('添加服务器','add-server','','primary')}</div>
    ${table(['服务器 / 分组','连接地址','认证','操作'],data.servers.filter(matches).map(s => `<tr><td><div class="name">${esc(s.name)}</div>${s.group ? badge(s.group) : ''}<div class="sub">${esc(s.note)}</div></td><td class="mono">${esc(s.user)}@${esc(s.host)}:${s.port}</td><td class="sub">${esc(s.key || 'SSH agent / 终端密码')}</td><td><div class="actions">${button('连接终端','ssh-connect',s.id,'')}${button('测试','ssh-test',s.id)}${button('编辑','edit-server',s.id)}${button('移除','delete-server',s.id)}</div></td></tr>`))}
    <div class="section-heading key-section"><h2>本机 SSH 密钥</h2>${button('生成新密钥','generate-key','','')}</div>
    <p class="muted">扫描目录：${esc(data.dir)}。此处只展示路径、指纹与公钥；服务器可手动选择其他位置的私钥。生成新密钥后请刷新。</p>
    ${data.keys.map(k => `<div class="key-card"><div><div class="name">${esc(k.name)}</div><code>${esc(k.path)}</code><div class="sub mono">${esc(k.fingerprint)}</div></div>${k.publicFile ? button('复制公钥','copy-public',k.path,'') : badge('缺少公钥','gray')}</div>`).join('') || '<div class="card empty">默认 SSH 目录中未发现支持的私钥，可手动选择密钥路径。</div>'}
    <div class="info-strip key-section">SSH agent<br><span class="mono">${esc(data.agent)}</span></div>`;
}
function serverDialog(server) {
  const form = $('#serverForm'); form.reset();
  for (const key of ['id','name','host','user','port','key','group','note']) form.elements[key].value = server?.[key] || (key === 'port' ? 22 : '');
  $('#serverDialog').showModal();
}
async function action(target) {
  const kind = target.dataset.action, id = target.dataset.id;
  if (inAction) { notice('有操作正在执行，请稍候'); return; }
  if (kind === 'add-server') { serverDialog(); return; }
  if (kind === 'edit-server') { serverDialog(data.servers.find(s => s.id === id)); return; }
  if (kind === 'process-details') { details('进程详情', JSON.stringify(data.find(p => p.id === Number(id)), null, 2)); return; }
  if (kind === 'pull') {
    details('拉取 Docker 镜像', '');
    $('#detailText').innerHTML = '<form id="pullForm"><label>镜像名称<input name="ref" required placeholder="例如 nginx:alpine" pattern="[a-zA-Z0-9][a-zA-Z0-9._/:@\\-]*"></label><button class="button primary" type="submit">开始拉取</button></form>';
    $('#pullForm').onsubmit = async e => { e.preventDefault(); const ref = new FormData(e.target).get('ref'); $('#details').close(); await perform(target, () => api('imageAction', { kind:'pull', ref }), true, '正在拉取镜像，最多等待 10 分钟…'); }; return;
  }
  let operation, refresh = true, waiting = '正在执行，请稍候…';
  if (['start','stop','restart','rm'].includes(kind)) operation = () => api('dockerAction',{ kind,id });
  else if (['container-logs','inspect'].includes(kind)) { refresh = false; operation = async () => details(kind === 'inspect' ? '容器详情（不包含环境变量）' : '最近 250 行日志', await api('dockerAction',{kind:kind === 'inspect' ? 'inspect' : 'logs',id}) || '没有日志'); }
  else if (['save-image','rm-image','load-image'].includes(kind)) { operation = () => api('imageAction',{kind:{'save-image':'save','rm-image':'rm','load-image':'load'}[kind],id,ref:target.dataset.ref}); waiting = '正在处理镜像归档，最多等待 10 分钟…'; }
  else if (['end-process','process-folder'].includes(kind)) { const p = data.find(p => p.id === Number(id)); operation = () => api(kind === 'end-process' ? 'endProcess' : 'processFolder',{id:p.id,created:p.created}); refresh = kind === 'end-process'; }
  else if (kind === 'toggle-startup') operation = () => api('toggleStartup',id);
  else if (kind === 'task-manager') { operation = () => api('openTaskManager'); refresh = false; }
  else if (kind === 'ssh-connect') { operation = () => api('sshConnect',id); refresh = false; }
  else if (kind === 'ssh-test') { operation = async () => { details('SSH 连接测试',await api('sshTest',id)); }; refresh = false; }
  else if (kind === 'delete-server') operation = () => api('deleteServer',id);
  else if (kind === 'import-ssh') operation = async () => { const r = await api('importSsh'); details('SSH 配置导入结果',`新增 ${r.count} 台，跳过 ${r.skipped} 台（重复名称或缺少有效参数）。\n${r.warnings.length ? '以下配置没有自动应用，需手动核对：' + r.warnings.join(', ') : ''}\n只导入明确的 Host 块；不解析 Include、通配默认值、Match 或代理命令。`); };
  else if (kind === 'copy-public') { operation = () => api('copyPublicKey',id); refresh = false; }
  else if (kind === 'generate-key') { operation = () => api('generateKey'); refresh = false; }
  if (operation) await perform(target,operation,refresh,waiting);
}
async function perform(target, operation, refresh, waiting = '正在执行，请稍候…') {
  inAction = true; target.disabled = true; notice(waiting);
  try { const result = await operation(); notice(result === false ? '已取消。' : '操作已完成。'); if (refresh) await load(true); }
  catch (e) { notice(e.message,true); }
  finally { inAction = false; target.disabled = false; }
}
document.addEventListener('click', e => {
  const nav = e.target.closest('[data-page]'); if (nav) { navigate(nav.dataset.page); return; }
  const tab = e.target.closest('[data-tab]'); if (tab) { dockerTab = tab.dataset.tab; query = ''; render(); return; }
  const target = e.target.closest('[data-action]'); if (target) action(target).catch(e => notice(e.message,true));
});
document.addEventListener('input',e => { if (e.target.id === 'search') { const pos = e.target.selectionStart; query = e.target.value; render(); $('#search').focus(); $('#search').setSelectionRange(pos,pos); } });
document.addEventListener('change',e => { if (e.target.id === 'sort') { sortKey = e.target.value; render(); } });
$('#refresh').onclick = () => load();
$('#closeDetails').onclick = () => $('#details').close();
$('#closeServer').onclick = () => $('#serverDialog').close();
$('#chooseKey').onclick = async () => { try { const file = await api('chooseKey'); if (file) $('#serverForm').elements.key.value = file; } catch (e) { notice(e.message,true); } };
$('#serverForm').onsubmit = async e => { e.preventDefault(); const input = Object.fromEntries(new FormData(e.target)); const submit = e.target.querySelector('[type=submit]'); await perform(submit,async () => { await api('saveServer',input); $('#serverDialog').close(); },true); };
navigate('overview');
