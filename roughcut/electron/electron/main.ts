import { app, BrowserWindow, ipcMain, dialog } from 'electron'
import path from 'path'
import { fileURLToPath } from 'url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)

let mainWindow: BrowserWindow | null

// Track Resolve connection status
let resolveStatus: 'connected' | 'connecting' | 'disconnected' = 'connecting'

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 1200,
    minHeight: 700,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
    titleBarStyle: 'hiddenInset',
    show: false,
  })

  // Load the app
  if (process.env.VITE_DEV_SERVER_URL) {
    mainWindow.loadURL(process.env.VITE_DEV_SERVER_URL)
    mainWindow.webContents.openDevTools()
  } else {
    mainWindow.loadFile(path.join(__dirname, '../index.html'))
  }

  mainWindow.once('ready-to-show', () => {
    mainWindow?.show()
    console.log('[RoughCut Electron] Window ready')
  })

  mainWindow.on('closed', () => {
    mainWindow = null
    console.log('[RoughCut Electron] Window closed')
  })
}

app.whenReady().then(() => {
  console.log('[RoughCut Electron] App starting...')
  console.log('[RoughCut Electron] Launched from DaVinci Resolve')
  
  createWindow()

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow()
    }
  })
})

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit()
  }
})

// IPC handlers for Python/Resolve communication
ipcMain.handle('resolve:check-connection', async () => {
  // Simulate connection check - in real implementation would communicate with Python backend
  // Wait a moment to simulate checking
  await new Promise(resolve => setTimeout(resolve, 500))
  
  // For now, simulate successful connection
  resolveStatus = 'connected'
  return { status: resolveStatus }
})

ipcMain.handle('resolve:send-timeline', async (_, data) => {
  console.log('[RoughCut Electron] Sending timeline to Resolve:', data)
  // Placeholder - will integrate with Python backend
  return { success: true }
})

ipcMain.handle('media:get-assets', async (_, category: string) => {
  console.log('[RoughCut Electron] Getting assets for category:', category)
  // Placeholder - will integrate with Python backend
  return []
})

ipcMain.handle('media:select-folder', async () => {
  console.log('[RoughCut Electron] Opening folder selection dialog')
  
  if (!mainWindow) {
    return { canceled: true, filePath: null }
  }
  
  const result = await dialog.showOpenDialog(mainWindow, {
    properties: ['openDirectory'],
    title: 'Select Media Folder',
    buttonLabel: 'Select Folder'
  })
  
  console.log('[RoughCut Electron] Folder selection result:', result.canceled ? 'canceled' : result.filePaths[0])
  
  return {
    canceled: result.canceled,
    filePath: result.canceled ? null : result.filePaths[0]
  }
})

ipcMain.handle('app:get-info', async () => {
  return {
    version: app.getVersion(),
    mode: 'electron',
    launchedFromResolve: true
  }
})

// Handle graceful shutdown
process.on('SIGTERM', () => {
  console.log('[RoughCut Electron] SIGTERM received, shutting down...')
  app.quit()
})

process.on('SIGINT', () => {
  console.log('[RoughCut Electron] SIGINT received, shutting down...')
  app.quit()
})
