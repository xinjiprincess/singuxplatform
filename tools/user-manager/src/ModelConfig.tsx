import React,{useState} from 'react';
import {Alert,Button,Form,Input,Select,Typography} from 'antd';
import {PlusOutlined} from '@ant-design/icons';
const preset={name:'DeepSeek-V4-Flash',description:'DeepSeek-V4-Flash',model:'DeepSeek-V4-Flash',type:'Chat',apiProtocol:'OpenAI',strategy:'RoundRobin',apiInfoList:[{url:'http://61.188.36.255:18000/maas/v1',key:'',weight:1}],functionCall:'Unsupported',isReasonModel:0,enabled:1,accessControl:0,usageScenarios:['PageApp','TaskAgent','ChatBot','Workflow','OpenApi']};
export default function ModelConfig({keys,profiles,disabled,call}:{keys:any[];profiles:any[];disabled:boolean;call:(name:string,input:any)=>Promise<any>}){
  const [result,setResult]=useState<string>();
  return <section><h1>平台模型配置</h1><Form layout="vertical" initialValues={{config:JSON.stringify(preset,null,2)}} onFinish={async values=>{
    setResult(undefined);const r=await call('addModel',{keyId:values.keyId,model:JSON.parse(values.config)});
    if(r?.success)setResult(r.id==null?'添加成功，接口未返回模型 ID，请在平台模型列表核对。':`添加成功，模型 ID：${r.id}`);
  }}>
    <Form.Item name="keyId" label="目标平台 / 管理员 API Key" rules={[{required:true}]}><Select disabled={disabled} options={keys.map(k=>({value:k.id,label:`${profiles.find(p=>p.id===k.profileId)?.baseUrl || ''} · ${k.name}`}))}/></Form.Item>
    <Form.Item name="config" label="模型配置 JSON" rules={[{validator:async(_,v)=>{try{const parsed=JSON.parse(v);if(!parsed||Array.isArray(parsed)||typeof parsed!=='object')throw new Error();}catch{throw new Error('请输入有效的 JSON 对象');}}}]}><Input.TextArea spellCheck={false} rows={22} disabled={disabled}/></Form.Item>
    <Button type="primary" icon={<PlusOutlined/>} htmlType="submit" disabled={disabled||!!result}>添加模型</Button>
    {result&&<Alert style={{marginTop:16}} type="success" message={result}/>}
    <Typography.Paragraph type="secondary">模型密钥默认为空；平台管理员 Key 仅用于管理接口。HTTP 模型地址为明文传输。</Typography.Paragraph>
  </Form></section>;
}
