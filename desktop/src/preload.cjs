const { contextBridge, ipcRenderer } = require('electron');

const api = {
  getStatus: () => ipcRenderer.invoke('jarvis:get-status'),
  saveSettings: (payload) => ipcRenderer.invoke('jarvis:save-settings', payload),
  runPrompt: (payload) => ipcRenderer.invoke('jarvis:run-prompt', payload),
  daemonControl: (payload) => ipcRenderer.invoke('jarvis:daemon-control', payload),
  getIntelligence: () => ipcRenderer.invoke('jarvis:get-intelligence'),
  runUtility: (payload) => ipcRenderer.invoke('jarvis:run-utility', payload),
  exportSession: (payload) => ipcRenderer.invoke('jarvis:export-session', payload),
  stop: () => ipcRenderer.invoke('jarvis:stop'),
  openExternal: (url) => ipcRenderer.invoke('jarvis:open-external', url),
  openProject: () => ipcRenderer.invoke('jarvis:open-project'),
  voiceListen: () => ipcRenderer.invoke('jarvis:listen'),
  getWeather: () => ipcRenderer.invoke('jarvis:get-weather'),
  getGeo: () => ipcRenderer.invoke('jarvis:get-geo'),
  stopListen: () => ipcRenderer.invoke('jarvis:stop-listen'),
  onProcessOutput: (callback) => {
    const listener = (_event, data) => callback(data);
    ipcRenderer.on('jarvis:process-output', listener);
    return () => ipcRenderer.removeListener('jarvis:process-output', listener);
  },
};

contextBridge.exposeInMainWorld('jarvisDesktop', api);
