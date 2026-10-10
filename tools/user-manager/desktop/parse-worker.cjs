const {parentPort,workerData}=require('node:worker_threads');
const fs=require('node:fs');
const crypto=require('node:crypto');
const path=require('node:path');
const XLSX=require('xlsx');
const yauzl=require('yauzl');
const {autoMapping,isCompetition}=require('./core.cjs');
async function checkZip(file) {
  const bytes=fs.readFileSync(file);
  if (bytes[0]!==0x50 || bytes[1]!==0x4b) return;
  await new Promise((resolve,reject)=>yauzl.fromBuffer(bytes,{lazyEntries:true},(err,zip)=>{
    if(err)return reject(err);
    let size=0,count=0;
    zip.on('error',reject);zip.on('end',resolve);
    zip.on('entry',entry=>{
      size+=entry.uncompressedSize;count++;
      if(size>80*1024*1024 || count>5000 || entry.generalPurposeBitFlag & 1){zip.close();reject(new Error('压缩表格过大或已加密'));return;}
      zip.readEntry();
    });zip.readEntry();
  }));
}
(async()=>{
  const sheets=[],issues=[];
  for(const file of workerData.files) {
    try {
      if(fs.statSync(file).size>10*1024*1024)throw new Error('超过 10 MB');
      await checkZip(file);
      const hash=crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex');
      const book=XLSX.readFile(file,{cellText:true,cellFormula:false,cellHTML:false,sheetRows:10002,raw:true,codepage:65001});
      for(const name of book.SheetNames) {
        const ws=book.Sheets[name];
        const range=XLSX.utils.decode_range(ws['!fullref']||ws['!ref']||'A1');
        if(range.e.r>=10000 || range.e.c>=80)throw new Error('单表超过一万行或 80 列');
        const rows=XLSX.utils.sheet_to_json(ws,{header:1,raw:false,defval:'',blankrows:true});
        if(!rows.some(row=>row.some(String)))continue;
        const mapping=autoMapping(rows);
        sheets.push({id:crypto.createHash('sha256').update(hash+name).digest('hex').slice(0,24),file:path.basename(file),name,hash,rows,...mapping,competition:isCompetition(rows)});
      }
    } catch {issues.push({file:path.basename(file),error:'读取失败、加密、格式不支持或超出大小限制'});}
  }
  parentPort.postMessage({sheets,issues});
})().catch(()=>parentPort.postMessage({sheets:[],issues:[{file:'',error:'读取失败'}]}));
