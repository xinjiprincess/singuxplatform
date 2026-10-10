const enums={type:['Completions','Chat','Multi','Edits','Images','Embeddings','Audio','Other'],apiProtocol:['OpenAI','Ollama','Zhipu','Anthropic'],strategy:['RoundRobin','WeightedRoundRobin','LeastConnections','WeightedLeastConnections','Random','ResponseTime'],functionCall:['Unsupported','CallSupported','StreamCallSupported']};
function modelConfig(input){
  const result={};
  for(const field of ['name','model']){if(typeof input[field]!=='string'||!input[field].trim())throw new Error(`${field} 不能为空`);result[field]=input[field].trim();}
  if(input.description!==undefined)result.description=String(input.description);
  for(const [field,values] of Object.entries(enums)){if(input[field]===undefined&&field==='functionCall')continue;if(!values.includes(input[field]))throw new Error(`${field} 无效`);result[field]=input[field];}
  for(const field of ['maxTokens','maxContextTokens','dimension','isReasonModel','enabled','accessControl']){
    if(input[field]===undefined)continue;
    const v=input[field];if(!Number.isInteger(v)||(['isReasonModel','enabled','accessControl'].includes(field)?![0,1].includes(v):v<1||v>2147483647))throw new Error(`${field} 无效`);result[field]=v;
  }
  if(!Array.isArray(input.apiInfoList)||!input.apiInfoList.length)throw new Error('至少配置一个模型接口');
  result.apiInfoList=input.apiInfoList.map(item=>{
    let url;try{url=new URL(item.url);}catch{throw new Error('模型 URL 必须包含 http:// 或 https://');}
    if(!['http:','https:'].includes(url.protocol)||url.username||url.password||url.search||url.hash)throw new Error('模型 URL 无效');
    const weight=item.weight??1;if(!Number.isInteger(weight)||weight<1)throw new Error('权重必须为正整数');
    if(item.key!==undefined&&typeof item.key!=='string')throw new Error('模型 Key 必须为字符串');
    return {url:url.toString().replace(/\/$/,''),key:item.key??'',weight};
  });
  if(input.usageScenarios!==undefined){if(!Array.isArray(input.usageScenarios)||input.usageScenarios.some(v=>!['PageApp','TaskAgent','ChatBot','Workflow','OpenApi'].includes(v)))throw new Error('使用场景无效');result.usageScenarios=[...new Set(input.usageScenarios)];}
  return result;
}
module.exports={modelConfig};
