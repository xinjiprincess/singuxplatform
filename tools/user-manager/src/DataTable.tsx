import React,{useState} from 'react';
import {Table,Select,Space} from 'antd';
import type {TableProps} from 'antd';

export default function DataTable(props:TableProps<any>){
  const [size,setSize]=useState<number|'all'>(20),[current,setCurrent]=useState(1);
  const count=props.dataSource?.length || 0;
  const virtual=size==='all' && count>100;
  return <>
    <div className="table-tools"><Space><span>共 {count} 条</span><Select aria-label="显示条数" value={size} style={{width:130}} onChange={v=>{setSize(v);setCurrent(1);}} options={[{value:20,label:'20 条 / 页'},{value:50,label:'50 条 / 页'},{value:'all',label:'全部显示'}]}/></Space></div>
    <Table {...props} virtual={virtual} scroll={virtual?{x:1000,...props.scroll,y:560}:props.scroll} pagination={size==='all'?false:{pageSize:size,current:Math.min(current,Math.max(1,Math.ceil(count/size))),showSizeChanger:false,onChange:setCurrent}}/>
  </>;
}
