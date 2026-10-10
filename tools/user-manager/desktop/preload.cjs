const {contextBridge,ipcRenderer}=require('electron');
const channels=['state','completeContacts','reviewConflict','approveConflict','saveProfile','deleteProfile','saveKey','deleteKey','setDefaultKey','accountReport','testKey','choose','map','preview','editRow','suggest','startTask','resumeTask','retryTask','pauseTask','exportTask','clearHistory'];
channels.push('addModel');
channels.push('userDetail','updateUser','roleFile','prepareRoles','executeRoles','exportRoles');
contextBridge.exposeInMainWorld('manager',Object.fromEntries(channels.map(name=>[name,(input)=>ipcRenderer.invoke('manager:'+name,input)])));
