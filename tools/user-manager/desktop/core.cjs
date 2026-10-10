const crypto = require('node:crypto');
const fields = ['uid', 'userName', 'nickName', 'phone', 'email'];
const aliases = {
  uid: ['uid', '学号', '工号', '工号/学号', '学工号', '用户唯一标识'],
  userName: ['username', '登录账号', '登录名', '用户名', '账号'],
  nickName: ['nickname', '姓名', '昵称', '真实姓名'],
  phone: ['phone', '手机号', '手机号码', '电话', '联系电话'],
  email: ['email', '邮箱', '电子邮箱', '电子邮件'],
};
const text = v => String(v ?? '').trim();
const key = v => text(v).replace(/[\s*＊]/g, '').toLowerCase();
function autoMapping(rows, headerRow) {
  if (headerRow === undefined) {
    headerRow = 0; let best = -1;
    rows.slice(0, 10).forEach((row, r) => {
      const score = row.filter(v => Object.values(aliases).some(a => a.includes(key(v)))).length;
      if (score > best) { best = score; headerRow = r; }
    });
  }
  const mapping = {};
  for (const [field, names] of Object.entries(aliases)) {
    const column = (rows[headerRow] || []).findIndex(v => names.includes(key(v)));
    if (column >= 0) mapping[field] = column;
  }
  return { headerRow, mapping };
}
function isCompetition(rows) {
  return rows[2]?.[6] === '工号/学号' && rows[2]?.[7] === '姓名' && rows[2]?.[15] === '团队成员情况';
}
function extract(sheet, options) {
  const records = []; const { rows } = sheet;
  const add = (raw, row, kind, team = '', track = '', instance = '') => {
    if (!Object.values(raw).some(v => text(v))) return;
    records.push({ ...Object.fromEntries(Object.entries(raw).map(([k,v])=>[k,text(v)])), kind, team, track, instance,
      id: crypto.createHash('sha256').update(`${sheet.id}:${row}:${kind}`).digest('hex').slice(0,24),
      sources: [{file:sheet.file, sheet:sheet.name, row:row + 1, kind, team, track, instance}] });
  };
  if (isCompetition(rows)) {
    let context;
    rows.slice(3).forEach((row, offset) => {
      const r = offset + 3;
      if (text(row[0]) && /^\d+$/.test(text(row[0]))) {
        context = { team:text(row[4]), track:text(row[3]), instance:text(row[41]) };
        add({ uid:row[6], nickName:row[7], phone:row[9], email:row[11], college:row[12], grade:row[13] }, r, '报名人', context.team, context.track, context.instance);
      }
      if (!context) return;
      if (text(row[16]) && text(row[16]) !== '姓名')
        add({uid:row[15],nickName:row[16],phone:row[20],college:row[18]},r,'成员',context.team,context.track,context.instance);
      if (options.includeTeachers && text(row[22]) && text(row[22]) !== '姓名')
        add({uid:row[24],nickName:row[22],phone:row[27],college:row[25]},r,'教师',context.team,context.track,context.instance);
    });
  } else {
    const {mapping, headerRow} = sheet;
    for (let r = headerRow + 1; r < rows.length; r++) {
      if (!fields.some(f => mapping[f] !== undefined && text(rows[r][mapping[f]]))) continue;
      // Repeated headers are data separators, not new people.
      if (Object.entries(mapping).every(([f,c]) => aliases[f]?.includes(key(rows[r][c])))) continue;
      add(Object.fromEntries(fields.map(f=>[f,mapping[f] !== undefined ? rows[r][mapping[f]] : ''])),r,'用户');
    }
  }
  return records;
}
function normalize(records, options) {
  return records.map(source => {
    const r = {...source};
    r.phone = text(r.phone).replace(/[\s()-]/g,'');
    r.email = text(r.email).toLowerCase();
    r.originalUid = text(r.uid);
    const identity = r.originalUid || r.email || r.phone;
    r.uid = identity ? `${options.schoolCode}:${r.kind === '教师' ? 'teacher' : 'person'}:${identity}` : '';
    r.userName = options.usernameMode === 'schoolIdentifier' ? (r.originalUid ? `${options.schoolCode}${r.originalUid}` : '') : options.usernameMode === 'identifier' ? r.originalUid : text(r.userName) || (r.originalUid ? `${options.usernamePrefix || ''}${r.originalUid}` : r.uid ? `u_${crypto.createHash('sha256').update(r.uid).digest('hex').slice(0,12)}` : '');
    r.nickName = text(r.nickName);
    r.errors = validate(r, options);
    return r;
  });
}
function validate(r, options) {
  const errors = [];
  if (!r.uid) errors.push('缺少学工号、邮箱或手机号');
  if(options.passwordMode==='schoolIdentifier' && (!r.originalUid || !/^[a-zA-Z][a-zA-Z0-9_-]{1,31}$/.test(options.schoolCode||'')))errors.push('学校代号加学号密码要求有效学校代号和原始学号');
  if (!r.userName || /\s/.test(r.userName) || /^user\d{10}$/.test(r.userName) || r.userName.length > 64) errors.push('登录名为空或格式无效，请核对工号/学号');
  if (['phone','schoolPhone'].includes(options.passwordMode) && !r.phone) errors.push('手机号初始密码要求填写手机号');
  if (!r.phone && !r.email) errors.push('缺少手机号和邮箱');
  if (options.requireBoth && (!r.phone || !r.email)) errors.push('当前规则要求同时填写手机号和邮箱');
  if (r.phone && !/^\+?\d{7,15}$/.test(r.phone)) errors.push('手机号格式异常');
  if (r.email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(r.email)) errors.push('邮箱格式异常');
  if (!r.nickName || /^\d+$/.test(r.nickName)) errors.push('姓名为空或为纯数字');
  if (r.uid.length > 128) errors.push('唯一标识过长');
  if (/(?:^|:)[+-]?\d+(?:\.\d+)?e[+-]?\d+$/i.test(r.uid)) errors.push('学工号为科学计数法，请核对原始文本');
  return errors;
}
function deduplicate(records) {
  const merged = new Map();
  for (const row of records) {
    const identity = row.uid ? JSON.stringify(fields.map(f=>row[f] || '')) : row.id;
    const previous = merged.get(identity);
    if (previous) {
      previous.sources.push(...row.sources);
      continue;
    }
    merged.set(identity, structuredClone(row));
  }
  const result = [...merged.values()];
  for (const f of ['uid','userName','phone','email']) {
    const index = new Map();
    for (const row of result) {
      if (!row[f]) continue;
      const other = index.get(row[f]);
      if (other && other.id !== row.id) {
        other.errors.push(`${f}对应多条不一致记录`); row.errors.push(`${f}对应多条不一致记录`);
      } else index.set(row[f],row);
    }
  }
  result.forEach(r=>r.errors=[...new Set(r.errors)]);
  return result;
}
function endpoint(value, allowHttp = false) {
  const u = new URL(value);
  if (u.username || u.password || u.search || u.hash || !['https:','http:'].includes(u.protocol)) throw new Error('服务地址必须是无凭据的 HTTP(S) URL');
  if (u.protocol === 'http:' && !['localhost','127.0.0.1','[::1]'].includes(u.hostname) && !allowHttp) throw new Error('远程连接必须使用 HTTPS，或显式允许不安全 HTTP');
  return u.href.replace(/\/$/,'');
}
function csvCell(value) {
  let s = text(value);
  if (/^[=+\-@\t\r]/.test(s)) s = "'" + s;
  return '"' + s.replace(/"/g,'""') + '"';
}
function redact(value) {
  return text(value).replace(/Bearer\s+\S+/gi,'Bearer [hidden]').replace(/(?:sk|ak)-[\w-]+/g,'[hidden]').replace(/[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/gi,'[email]').replace(/\+?\d[\d -]{7,}\d/g,'[number]');
}
function verifyMapping(mapping, width) {
  if (!mapping || typeof mapping!=='object' || Array.isArray(mapping)) throw new Error('字段映射必须是对象');
  const clean = {};
  for (const [f,c] of Object.entries(mapping || {})) {
    if (!fields.includes(f) || !Number.isInteger(c) || c < 0 || c >= width) throw new Error('字段映射超出允许范围');
    if (Object.values(clean).includes(c)) throw new Error('同一列不能重复映射');
    clean[f] = c;
  }
  return clean;
}
module.exports = { fields, text, autoMapping, isCompetition, extract, normalize, validate, deduplicate, endpoint, csvCell, redact, verifyMapping };
