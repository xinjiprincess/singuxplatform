const { endpoint, redact } = require('./core.cjs');
class ApiError extends Error {
  constructor(code, message) { super(redact(message)); this.code = String(code); }
}
class PlatformApi {
  async userDetail(query){return this.request('/api/v1/system/user/detail?'+require('./user-query.cjs').queryParams(query));}
  async updateUser(id,body){
    require('./user-query.cjs').queryParams({id});
    const allowed=['userName','nickName','avatar','role','email','phone','password'];
    if(!body||!Object.keys(body).length||Object.keys(body).some(k=>!allowed.includes(k)||typeof body[k]!=='string'))throw new Error('更新字段无效');
    if(body.role!==undefined&&!['Admin','User'].includes(body.role))throw new Error('角色只能为 Admin 或 User');
    return this.request(`/api/v1/system/user/${id}/update`,body);
  }
  async addModel(input) {
    const body=require('./model-config.cjs').modelConfig(input);
    try { return await this.request('/api/v1/system/model/add',body); }
    catch(error){for(const item of body.apiInfoList)if(item.key)error.message=error.message.split(item.key).join('[hidden]');throw error;}
  }
  constructor(profile, secret, transport = fetch) {
    this.base = endpoint(profile.baseUrl, profile.allowHttp);
    this.scope = profile.scope || 'tenant';
    this.secret = secret; this.transport = transport;
  }
  async request(route, data, method) {
    let response;
    try {
      response = await this.transport(this.base + route, { method:method || (data === undefined ? 'GET' : 'POST'), redirect:'error',
        headers:{ Authorization:`Bearer ${this.secret}`, 'Content-Type':'application/json' },
        body:data === undefined ? undefined : JSON.stringify(data), signal:AbortSignal.timeout(20000) });
    } catch { throw new ApiError('NETWORK', '连接失败或超时，写入结果可能未知'); }
    let result;
    try { result = await response.json(); } catch { throw new ApiError('RESPONSE','响应不是有效 JSON'); }
    if (!response.ok || result.code !== '0000') {
      let message=String(result.message || `HTTP ${response.status}`).split(this.secret).join('[hidden]');
      if(data?.password)message=message.split(data.password).join('[hidden]');
      throw new ApiError(result.code || response.status,message);
    }
    return result.data;
  }
  async users(tenantId, onPage = ()=>{}) {
    const users = []; let total;
    for (let pageNo=1;pageNo<=100;pageNo++) {
      const data = await this.request('/api/v1/system/user/list',{pageNo,pageSize:100,queryFilter:{}});
      if (!data || !Array.isArray(data.records) || !Number.isInteger(Number(data.total))) throw new ApiError('CONTRACT','用户列表格式不兼容');
      if (total === undefined) total = Number(data.total);
      if (total !== Number(data.total) || total > 10000) throw new ApiError('SNAPSHOT','用户数量变化或超过一万条，请重新核对');
      for (const u of data.records) {
        if(!/^[1-9]\d*$/.test(String(u.id))) throw new ApiError('CONTRACT','用户列表包含无效 ID');
        if(typeof u.id==='number' && !Number.isSafeInteger(u.id)) throw new ApiError('CONTRACT','用户 ID 超出安全整数范围，需服务端返回字符串');
        if (this.scope!=='single' && String(u.tenantId) !== String(tenantId)) throw new ApiError('TENANT','返回的用户租户与目标不符，已停止');
        users.push(u);
      }
      if (users.length >= total) break;
      if (!data.records.length) throw new ApiError('SNAPSHOT','用户分页提前结束');
      onPage(); await new Promise(r=>setTimeout(r,600));
    }
    if (users.length !== total || new Set(users.map(u=>String(u.id))).size !== users.length) throw new ApiError('SNAPSHOT','用户分页存在重复或遗漏');
    if(this.scope==='single' && new Set(users.map(u=>String(u.tenantId ?? 'unspecified'))).size>1)throw new ApiError('TENANT','返回了多个租户的数据，不能按单租户导入');
    if (!users.length && this.scope!=='single') throw new ApiError('TENANT','空用户列表无法核对租户，请先确认服务器接口上下文');
    return users;
  }
  async membership(tenantId, userId) {
    const members = await this.request(`/api/platform/tenants/${tenantId}/members`);
    if (!Array.isArray(members)) throw new ApiError('CONTRACT','成员接口格式不兼容');
    const existing = members.find(m=>String(m.userId)===String(userId));
    if (existing?.status === 'ACTIVE') return;
    if (existing) throw new ApiError('MEMBERSHIP','已有成员不是 ACTIVE，请在平台审核处理，不自动恢复');
    await this.request(`/api/platform/tenants/${tenantId}/members/${userId}`, {role:'MEMBER',status:'ACTIVE',version:-1,reason:'Local user import'}, 'PUT');
  }
}
function findExisting(row, users) {
  const matches = users.filter(u => (row.uid && u.uid === row.uid) || (row.phone && u.phone === row.phone) || (row.email && String(u.email || '').toLowerCase() === row.email) || u.userName === row.userName);
  const ids = new Set(matches.map(u=>String(u.id)));
  if (ids.size > 1) throw new ApiError('CONFLICT','多个标识对应不同用户，需人工处理：'+matches.map(u=>`用户ID ${u.id} / 登录名 ${u.userName}`).join('；'));
  const u = matches[0];
  if (u && !(u.uid === row.uid && u.userName === row.userName && (!row.phone || u.phone === row.phone) && (!row.email || String(u.email || '').toLowerCase() === row.email)))
    throw new ApiError('CONFLICT',`身份冲突，已有用户ID ${u.id}，不自动合并：`+[['uid','学工号标识'],['userName','登录名'],['phone','手机号'],['email','邮箱']].filter(([k])=>(k==='uid'||k==='userName'||row[k]) && String(u[k]||'').toLowerCase()!==String(row[k]||'').toLowerCase()).map(([k,label])=>`${label}：导入值「${row[k]||'空'}」，已有值「${u[k]||'空'}」`).join('；'));
  return u;
}
function pauses(error) { return ['NETWORK','RESPONSE','TENANT','SNAPSHOT','CONTRACT','401','403','4010','4030','429','4290'].includes(error.code) || /限流|请求.*频繁|速率|额度|配额|权限|认证|未登录|API.?Key|rate.?limit/i.test(error.message); }
module.exports = {PlatformApi, ApiError, findExisting, pauses};
