const {Worker}=require('node:worker_threads');
const path=require('node:path');
const core=require('../desktop/core.cjs');
if(!process.argv[2])throw Error('Provide a local workbook path');
const worker=new Worker(path.resolve(__dirname,'../desktop/parse-worker.cjs'),{workerData:{files:[process.argv[2]]}});
worker.on('message',result=>{
  const options={schoolCode:'sample',usernamePrefix:'stu_',requireBoth:true,includeTeachers:false};
  const records=result.sheets.flatMap(sheet=>core.extract(sheet,options));
  const normalized=core.deduplicate(core.normalize(records,options));
  // Only aggregates: no names, phone numbers, emails or raw records leave this process.
  console.log(JSON.stringify({sheets:result.sheets.length,knownTemplates:result.sheets.filter(s=>s.competition).length,issues:result.issues.length,records:records.length,unique:normalized.length,valid:normalized.filter(r=>!r.errors.length).length,needsReview:normalized.filter(r=>r.errors.length).length}));
});
worker.on('error',()=>{console.error('Template inspection failed');process.exitCode=1;});
