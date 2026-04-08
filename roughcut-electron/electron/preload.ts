import { contextBridge, ipcRenderer } from 'electron'

// Expose protected methods that allow the renderer process to use
// the ipcRenderer without exposing the entire object
contextBridge.exposeInMainWorld('electronAPI', {
  checkResolveConnection: () => ipcRenderer.invoke('resolve:check-connection'),
  sendTimeline: (data: unknown) => ipcRenderer.invoke('resolve:send-timeline', data),
  getAssets: (category: string) => ipcRenderer.invoke('media:get-assets', category),
})

// TypeScript support
declare global {
  interface Window {
    electronAPI: {
      checkResolveConnection: () => Promise<{ status: string }>
      sendTimeline: (data: unknown) => Promise<{ success: boolean }>
      getAssets: (category: string) => Promise<unknown[]>
    }
  }
}
