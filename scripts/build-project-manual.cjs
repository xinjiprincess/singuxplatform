const fs = require('fs');
const path = require('path');
const { JSDOM } = require('jsdom');
const Turndown = require('turndown');
const root = path.resolve(__dirname, '..');
const archive = path.join(root, 'docs/manual-archive');
const out = path.join(root, 'docs/user-manual');
fs.mkdirSync(out, { recursive: true });
const manifest = JSON.parse(fs.readFileSync(path.join(archive, 'manifest.json'), 'utf8'));
const chapterName = p => path.basename(p.file, '.html') === 'nuwa-eco-platform-user-manual' ? 'external-resources.md' : path.basename(p.file, '.html') + '.md';
const names = new Map(manifest.pages.map(p => [p.path, encodeURI(chapterName(p))]));
const tick = String.fromCharCode(96);
function clean(s) {
  return s
    .replace(/https?:\/\/(?:[^\s/<>"')]*\.)?nuwax\.(?:com|cn)(?:\/[^\s<>"')\]]*)?/gi, 'https://service.example.invalid')
    .replace(/https?:\/\/github\.com\/nuwax-ai[^\s<>"')\]]*/gi, 'https://repository.example.invalid')
    .replace(/(?:女娲\s*)?(?:Nuwax\s*(?:Agent\s*OS|AgentOS|Eco\s*Platform|AI|OS)?|Nuwa\s*(?:Agent\s*OS|OS|Claw)?)/gi, '智能体平台')
    .replace(/女娲\s*(?:智能体\s*OS|智能体平台|生态平台|OS|官方)?/gi, '智能体平台')
    .replace(/成都第二空间智能科技有限公司/g, '平台运营方')
    .replace(/\b(?:xagi|nuwaclaw)\b/gi, 'agent-platform')
    .replace(/ak-[A-Za-z0-9_-]{12,}/g, 'ak-REPLACE_WITH_API_KEY')
    .replace(/\u200b/g, '').replace(/智能体平台\s*智能体平台/g, '智能体平台');
}
const td = new Turndown({ headingStyle: 'atx', codeBlockStyle: 'fenced', bulletListMarker: '-' });
td.addRule('code', {
  filter: 'pre', replacement: (_, n) => {
    const code = n.querySelector('code');
    const lang = (n.parentElement?.className || '').match(/language-([\w]+)/)?.[1] || '';
    const text = (code || n).textContent.replace(/\n$/, '');
    const fence = tick.repeat(Math.max(3, ...(text.match(/`+/g) || []).map(x => x.length + 1)));
    return '\n\n' + fence + lang + '\n' + text + '\n' + fence + '\n\n';
  }
});
td.addRule('table', {
  filter: 'table', replacement: (_, n) => {
    const rows = Array.from(n.querySelectorAll('tr')).map(r => Array.from(r.children).filter(c => /TH|TD/.test(c.tagName)).map(c => td.turndown(c.innerHTML).replace(/\n/g, '<br>').replace(/\|/g, '\\|')));
    if (!rows.length) return '';
    const width = Math.max(...rows.map(r => r.length));
    const row = r => '| ' + Array.from({length: width}, (_, i) => r[i] || '').join(' | ') + ' |';
    return '\n\n' + [row(rows[0]), row(Array(width).fill('---')), ...rows.slice(1).map(row)].join('\n') + '\n\n';
  }
});
const notes = {
  'workspace': '空间权限与系统角色分别管理；不能因有空间页面而推断全部后端资源隔离已经验收。',
  'first-task-agent': '通用型依赖真实沙箱、调度器和文件服务，本地镜像健康不等于生产创建、回收和权限验收。',
  'general-agent': '独立执行电脑依赖配套服务，当前环境的真实创建、执行和回收需要验收。',
  'model-relay-service': '账号积分与企业额度是两套范围；企业额度目前为预留配置，不承诺原子扣减或结算。',
  'page-develop': '前端已有文件编辑和预览页面；实际生成、编辑、预览和发布仍依赖后端与配套服务联调。',
  'platform-subscription-monetization': '保留既有个人积分界面说明。企业套餐支付仅预留；微信和支付宝真实收款不在已交付范围。',
  'platform-model-config-price-monitor': '模型定价界面不证明企业扣费已实现；Token 估算与供应商账单可能不同。',
  'system-config': '示例服务地址不可解析，必须填写真实配置。品牌和自定义域名仍受套餐与实施开关约束。',
  'permission-management': '线上继续单租户，不把已有 Admin 自动视为平台超级管理员，也不要求普通用户选择企业。',
  'open-api-user-add': '本项目 userName 是登录名，nickName 是昵称。当前工具默认学校代号拼接学号，保留前导零；旧纯数字用户名需兼容补丁。导入只创建 User，默认检查 phone 和 email。',
  'component-integration': '项目存在 /app/:agentId 及 /app/chat/:agentId/:id 路由，ticket 与资源权限必须由服务器验证。',
  'mcp': '本地完成过只读工具代理调用；生产部署、全部工具兼容与运行时隔离仍须验收。',
  'sandbox-management': '真实创建、回收、用户文件隔离和权限边界需按环境验收，不公开调度、VNC 或 Docker 管理端口。',
  'frequently-asked-questions': '与项目操作指南冲突时按项目指南处理，支持渠道为本平台管理员。',
};
const overrides = JSON.parse(fs.readFileSync(path.join(out, 'project-overrides.json'), 'utf8'));
overrides['docker-client-deploy'] = overrides['docker-client-deploy'].replace('v0.1.1', 'v0.1.5');
const sections = [];
for (const p of manifest.pages) {
  const slug = path.basename(p.file, '.html');
  const doc = new JSDOM(fs.readFileSync(path.join(archive, 'html', p.file), 'utf8')).window.document;
  const article = doc.querySelector('.vp-doc');
  article.querySelectorAll('.header-anchor,script,style,button,.copy,.lang,video,iframe,img,picture,source').forEach(n => n.remove());
  article.querySelectorAll('a[href]').forEach(a => {
    const href = a.getAttribute('href');
    if (href.startsWith('#')) { a.replaceWith(...a.childNodes); return; }
    let u;
    try { u = new URL(href, 'https://nuwax.com' + p.path); } catch { return; }
    const local = names.get(decodeURI(u.pathname)) || names.get(u.pathname);
    if (local) a.setAttribute('href', local);
    else if (u.hostname.endsWith('nuwax.com') || u.hostname === 'github.com' && /nuwax-ai/.test(u.pathname)) a.replaceWith(...a.childNodes);
  });
  let md = overrides[slug] || clean(td.turndown(article.innerHTML));
  if (slug === 'open-api-user-add') md = md.replace(/\| userName \| 姓名 \|/g, '| userName | 登录用户名（工号/学号保留前导零） |');
  if (slug === '2025年上半年新手机产品盘点') md = '# 手机产品知识库示例（历史数据）\n\n仅用于客服知识库演示，非当前推荐。价格和性能未经本项目核实，业务应使用自行维护的真实资料。\n\n' + md.replace(/^#.*\n/, '');
  md = md.split('\n').filter(l => !/微信技术支持群|群助理|关注.*公众号|关注.*视频号|抖音账号|小红书|蜀ICP备|川公网安备|技术支持群|官方交流群/.test(l)).join('\n');
  const lines = md.split('\n');
  const title = lines.shift().replace(/^#+\s*/, '').trim();
  let note = notes[slug] || '本章为功能与操作参考，实际菜单取决于服务器授权和环境配置。界面存在不表示生产能力已验收，环境边界以项目操作指南为准。';
  if (/^(open-api-|conversation-)/.test(slug)) note += ' 接口未对线上执行写入验证；服务地址与密钥需替换为实际值。';
  md = '# ' + title + '\n\n> 更新：2026-10-04。' + note + '\n\n' + lines.join('\n').trim() + '\n';
  const name = decodeURI(names.get(p.path));
  fs.writeFileSync(path.join(out, name), md);
  sections.push({ slug, name, title, md, source: p.file, rewritten: !!overrides[slug] });
}
fs.writeFileSync(path.join(out, 'coverage.json'), JSON.stringify(sections.map(({slug,name,title,source,rewritten}) => ({slug,name,title,source,rewritten})), null, 2) + '\n');
const groups = [
  ['开始使用', ['user-manual','first-agent','first-task-agent','workspace','frequently-asked-questions','common-words','常用词解释']],
  ['资源与智能体开发', ['plugin','kb','table','model-management','llm','model-relay-service','mcp','workflow','skill-management','subagents','agent-orchestration','agent-design','qa-agent','general-agent']],
  ['应用、协作与运营', ['page-develop','im-channel-integration','job','log-query','ecosystem-market','nuwa-eco-platform-user-manual','xp','dialog-agent']],
  ['系统管理', ['platform-model-config-price-monitor','platform-subscription-monetization','platform-payment-revenue','permission-management','sandbox-management','system-config']],
  ['部署与客户端', ['deploy','agent-computer-deploy','docker-client-deploy','docker-performance-optimization']],
  ['开放 API', sections.filter(s => /^(open-api-|conversation-)/.test(s.slug) || ['api-key','component-integration'].includes(s.slug)).map(s => s.slug)],
  ['案例与政策边界', ['zhiyuan','kefu','2025年上半年新手机产品盘点','user-agreement','open-agreement','privacy']]
];
const listed = new Set(groups.flatMap(g => g[1]));
groups.push(['补充页面', sections.filter(s => !listed.has(s.slug)).map(s => s.slug)]);
const intro = '# Singu X 智能体平台完整用户手册\n\n更新日期：2026-10-04。基于当前项目源码与实施记录整理，适用于管理员、开发者和普通用户。\n\n线上继续单租户。企业切换、全链路隔离、外部市场与企业支付不作为当前服务承诺。\n\n包含项目操作指南及 ' + sections.length + ' 篇关联文档的 Markdown 章节。原始 HTML 和素材单独保存在下载档案，不用于发布。截图包含旧品牌，整理版不嵌入截图。实际登录、权限和环境边界以项目操作指南为准，其余章节用于详细功能与接口参考。\n\n';
let readme = intro + '## 推荐阅读\n\n1. 阅读 [项目操作指南](project-guide.md)，确认登录和环境。\n2. 普通用户阅读空间、问答智能体及常见问题。\n3. 开发者阅读资源、工作流、通用智能体与网页开发。\n4. 管理员阅读权限、系统配置、部署和批量导入。\n5. 集成开发者阅读 API Key、会话、文件与开放 API。\n\n## 完整目录\n\n- [项目操作指南](project-guide.md)\n- [完整合并版](../user-manual.md)\n\n';
const fixMergedLinks = body => body.replace(/\]\(([^)]+\.md)(#[^)]*)?\)/g, (_, target, hash='') => '](' + (target.startsWith('../') ? target.slice(3) : 'user-manual/' + target) + hash + ')');
let merged = intro + fixMergedLinks(fs.readFileSync(path.join(out, 'project-guide.md'), 'utf8').replace(/^(#{1,5}) /gm, '$1# ')) + '\n\n';
for (const [title, slugs] of groups) {
  const entries = slugs.map(slug => sections.find(s => s.slug === slug)).filter(Boolean);
  if (!entries.length) continue;
  readme += '### ' + title + '\n\n' + entries.map(s => '- [' + s.title + '](' + encodeURI(s.name) + ')').join('\n') + '\n\n';
  merged += '## ' + title + '\n\n';
  for (const s of entries) {
    let body = s.md.replace(/^(#{1,4}) /gm, '$1## ');
    body = body.replace(/\]\(([^)]+\.md)(#[^)]*)?\)/g, (_, target, hash='') => '](' + (target.startsWith('../') ? target.slice(3) : 'user-manual/' + target) + hash + ')');
    merged += body + '\n\n';
  }
}
fs.writeFileSync(path.join(out, 'README.md'), readme);
fs.writeFileSync(path.join(root, 'docs/user-manual.md'), merged);
console.log(JSON.stringify({ chapters: sections.length, mergedBytes: Buffer.byteLength(merged), rewritten: sections.filter(s => s.rewritten).length }));
