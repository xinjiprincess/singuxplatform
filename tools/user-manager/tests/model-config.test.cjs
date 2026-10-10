const {test}=require('node:test');
const assert=require('node:assert/strict');
const {modelConfig}=require('../desktop/model-config.cjs');
const {PlatformApi}=require('../desktop/api.cjs');
const preset={name:'DeepSeek-V4-Flash',model:'DeepSeek-V4-Flash',type:'Chat',apiProtocol:'OpenAI',strategy:'RoundRobin',apiInfoList:[{url:'http://61.188.36.255:18000/maas/v1',key:'',weight:1}]};
test('empty model key stays empty and base path is preserved',async()=>{
  const api=new PlatformApi({baseUrl:'https://example.com',scope:'single'},'admin-key',async(url,opts)=>{
    assert.equal(url,'https://example.com/api/v1/system/model/add');assert.equal(opts.headers.Authorization,'Bearer admin-key');
    assert.deepEqual(JSON.parse(opts.body).apiInfoList,preset.apiInfoList);return {ok:true,json:async()=>({code:'0000',data:null})};
  });assert.equal(await api.addModel(preset),null);
});
test('invalid model configuration rejected',()=>{
  assert.throws(()=>modelConfig({...preset,model:''}));
  assert.throws(()=>modelConfig({...preset,apiInfoList:[{url:'61.188.36.255:18000/maas/v1'}]}));
  assert.throws(()=>modelConfig({...preset,strategy:'invalid'}));
});
