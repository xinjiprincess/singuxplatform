const { contextBridge, ipcRenderer } = require('electron');
contextBridge.exposeInMainWorld('localManager', {
  invoke: async (name, input) => {
    const result = await ipcRenderer.invoke('manager', { name, input });
    if (!result.ok) throw new Error(result.error);
    return result.data;
  }
});
