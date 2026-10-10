const {app,safeStorage}=require('electron');
const fs=require('node:fs');
const path=require('node:path');
app.whenReady().then(()=>{
  const key=process.env.SINGUX_INITIAL_PLATFORM_KEY;
  delete process.env.SINGUX_INITIAL_PLATFORM_KEY;
  if(!key || /[\r\n]/.test(key) || !safeStorage.isEncryptionAvailable())throw new Error('Local encrypted provisioning unavailable');
  const dir=path.join(app.getPath('appData'),'singux-user-manager');
  fs.mkdirSync(dir,{recursive:true});
  fs.writeFileSync(path.join(dir,'default-key.enc'),safeStorage.encryptString(key));
  console.log('Encrypted local default saved; applied on next client start.');
  app.exit(0);
}).catch(()=>{console.error('Local provisioning failed');app.exit(1);});
