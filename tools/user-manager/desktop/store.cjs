const fs=require('node:fs');
const path=require('node:path');
class EncryptedStore {
  constructor(file,safeStorage) {this.file=file;this.safe=safeStorage;}
  read(fallback) {
    if(!fs.existsSync(this.file))return fallback;
    if(!this.safe.isEncryptionAvailable())throw new Error('系统凭据加密不可用');
    return JSON.parse(this.safe.decryptString(fs.readFileSync(this.file)));
  }
  write(state) {
    if(!this.safe.isEncryptionAvailable())throw new Error('系统凭据加密不可用，未保存任何明文');
    fs.mkdirSync(path.dirname(this.file),{recursive:true});
    const temp=this.file+'.tmp';
    fs.writeFileSync(temp,this.safe.encryptString(JSON.stringify(state)));
    fs.renameSync(temp,this.file);
  }
}
module.exports={EncryptedStore};
