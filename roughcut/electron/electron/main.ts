import { app, BrowserWindow, ipcMain, dialog } from 'electron'
import path from 'path'
import { fileURLToPath } from 'url'
import fs from 'fs'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)

let mainWindow: BrowserWindow | null

// Track Resolve connection status
let resolveStatus: 'connected' | 'connecting' | 'disconnected' = 'connecting'

function createWindow() {
  // Resolve preload script path - check multiple possible locations
  const possiblePreloadPaths = [
    path.join(__dirname, 'preload.js'),
    path.join(__dirname, 'electron', 'preload.js'),
    path.join(app.getAppPath(), 'electron', 'preload.js'),
    path.join(process.cwd(), 'electron', 'preload.js'),
  ]
  
  let preloadPath: string | null = null
  for (const testPath of possiblePreloadPaths) {
    console.log('[RoughCut Electron] Checking preload path:', testPath)
    if (fs.existsSync(testPath)) {
      preloadPath = testPath
      console.log('[RoughCut Electron] Found preload script at:', preloadPath)
      break
    }
  }
  
  if (!preloadPath) {
    console.error('[RoughCut Electron] ERROR: preload.js not found in any of the expected locations:')
    possiblePreloadPaths.forEach(p => console.error('  -', p))
    console.error('[RoughCut Electron] __dirname:', __dirname)
    console.error('[RoughCut Electron] app.getAppPath():', app.getAppPath())
    console.error('[RoughCut Electron] process.cwd():', process.cwd())
  }
  
  const webPreferences: Electron.WebPreferences = {
    contextIsolation: true,
    nodeIntegration: false,
  }
  
  if (preloadPath) {
    webPreferences.preload = preloadPath
  }
  
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 1200,
    minHeight: 700,
    webPreferences,
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
    console.error('[RoughCut Electron] ERROR: mainWindow is null, cannot open dialog')
    return { canceled: true, filePath: null, error: 'Main window not available' }
  }
  
  // Check if mainWindow is destroyed
  if (mainWindow.isDestroyed()) {
    console.error('[RoughCut Electron] ERROR: mainWindow is destroyed, cannot open dialog')
    return { canceled: true, filePath: null, error: 'Main window destroyed' }
  }
  
  try {
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
  } catch (error) {
    console.error('[RoughCut Electron] ERROR: Failed to open folder dialog:', error)
    return { canceled: true, filePath: null, error: String(error) }
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
