import { app, BrowserWindow, ipcMain, dialog } from 'electron'
import path from 'path'
import { fileURLToPath } from 'url'
import fs from 'fs'
import { executePythonCommand, cancelIndexing, getActiveIndexingOperations, cleanupAllProcesses } from './pythonBridge.js'

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

  // Log all console messages from the renderer (including preload script logs/errors)
  mainWindow.webContents.on('console-message', (event, level, message, line, sourceId) => {
    const levelName = ['debug', 'info', 'warn', 'error'][level] || 'log'
    console.log(`[Renderer ${levelName.toUpperCase()}] ${message}`)
  })

  // Load the app
  if (process.env.VITE_DEV_SERVER_URL) {
    console.log('[RoughCut Electron] Loading from dev server:', process.env.VITE_DEV_SERVER_URL)
    mainWindow.loadURL(process.env.VITE_DEV_SERVER_URL)
    mainWindow.webContents.openDevTools()
  } else {
    const indexPath = path.join(__dirname, '../index.html')
    console.log('[RoughCut Electron] Loading from file:', indexPath)
    mainWindow.loadFile(indexPath)
  }

  mainWindow.once('ready-to-show', () => {
    mainWindow?.show()
    console.log('[RoughCut Electron] Window ready')
    
    // Check if preload script loaded successfully by executing JavaScript in the renderer
    mainWindow?.webContents.executeJavaScript('typeof window.electronAPI !== "undefined"')
      .then((hasAPI) => {
        console.log('[RoughCut Electron] Preload script check - window.electronAPI available:', hasAPI)
        if (!hasAPI) {
          console.error('[RoughCut Electron] WARNING: Preload script did not expose window.electronAPI!')
        }
      })
      .catch((err) => {
        console.error('[RoughCut Electron] Error checking preload script:', err)
      })
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

// ==========================================
// INDEXING IPC HANDLERS
// ==========================================

/**
 * Index folders - performs incremental indexing
 * Params: { folders: [{ id, path, category }], incremental: boolean }
 */
ipcMain.handle('media:index-folders', async (_, params: { folders: Array<{ id: string; path: string; category: string }>; incremental?: boolean }) => {
  console.log('[RoughCut Electron] Starting folder indexing:', params)
  
  try {
    const operationId = `index_${Date.now()}`
    
    // Set up progress tracking
    const progressUpdates: any[] = []
    
    const result: any = await executePythonCommand(
      'index',
      {
        folders: params.folders || [],
        incremental: params.incremental !== false
      },
      (progress: any) => {
        progressUpdates.push(progress)
        // Send progress to renderer via mainWindow
        if (mainWindow && !mainWindow.isDestroyed()) {
          mainWindow.webContents.send('media:index-progress', {
            operationId,
            ...progress
          })
        }
      }
    )
    
    // Include all progress updates in result
    result.progress_updates = progressUpdates
    result.operation_id = operationId
    
    console.log('[RoughCut Electron] Indexing complete:', result)
    return { success: true, ...result }
    
  } catch (error: any) {
    console.error('[RoughCut Electron] Indexing failed:', error)
    return { 
      success: false, 
      error: error.message || String(error),
      error_type: 'INDEXING_FAILED'
    }
  }
})

/**
 * Reindex folders - performs full reindexing (scans all files)
 * Params: { folders: [{ id, path, category }] }
 */
ipcMain.handle('media:reindex-folders', async (_, params: { folders: Array<{ id: string; path: string; category: string }> }) => {
  console.log('[RoughCut Electron] Starting full reindexing:', params)
  
  try {
    const operationId = `reindex_${Date.now()}`
    
    const progressUpdates: any[] = []
    
    const result: any = await executePythonCommand(
      'reindex',
      {
        folders: params.folders || []
      },
      (progress: any) => {
        progressUpdates.push(progress)
        if (mainWindow && !mainWindow.isDestroyed()) {
          mainWindow.webContents.send('media:index-progress', {
            operationId,
            ...progress
          })
        }
      }
    )
    
    result.progress_updates = progressUpdates
    result.operation_id = operationId
    
    console.log('[RoughCut Electron] Reindexing complete:', result)
    return { success: true, ...result }
    
  } catch (error: any) {
    console.error('[RoughCut Electron] Reindexing failed:', error)
    return { 
      success: false, 
      error: error.message || String(error),
      error_type: 'REINDEXING_FAILED'
    }
  }
})

/**
 * Query assets from SpacetimeDB
 * Params: { category: 'music'|'sfx'|'vfx', limit: number }
 */
ipcMain.handle('media:query-assets', async (_, params: { category: string; limit?: number }) => {
  console.log('[RoughCut Electron] Querying assets:', params)
  
  try {
    const result: any = await executePythonCommand('query', {
      category: params.category,
      limit: params.limit || 1000
    })
    
    console.log(`[RoughCut Electron] Query returned ${result.total_count} assets`)
    return { success: true, ...result }
    
  } catch (error: any) {
    console.error('[RoughCut Electron] Asset query failed:', error)
    return { 
      success: false, 
      error: error.message || String(error),
      assets: [],
      total_count: 0
    }
  }
})

/**
 * Get database status and asset counts
 */
ipcMain.handle('media:database-status', async () => {
  console.log('[RoughCut Electron] Getting database status')
  
  try {
    const result: any = await executePythonCommand('status', {})
    return { success: true, ...result }
    
  } catch (error: any) {
    console.error('[RoughCut Electron] Database status check failed:', error)
    return { 
      success: false, 
      error: error.message || String(error),
      connected: false,
      music_count: 0,
      sfx_count: 0,
      vfx_count: 0,
      total_count: 0
    }
  }
})

/**
 * Get active indexing operations
 */
ipcMain.handle('media:indexing-operations', async () => {
  const operations = getActiveIndexingOperations()
  return { success: true, operations }
})

/**
 * Cancel an indexing operation
 */
ipcMain.handle('media:cancel-indexing', async (_, params: { operationId: string }) => {
  const { operationId } = params
  console.log('[RoughCut Electron] Cancelling indexing:', operationId)
  
  const cancelled = cancelIndexing(operationId)
  return { success: cancelled, operation_id: operationId }
})

// ==========================================
// UPDATED ASSET HANDLER (uses real DB)
// ==========================================

ipcMain.handle('media:get-assets', async (_, category: string) => {
  console.log('[RoughCut Electron] Getting assets for category:', category)
  
  try {
    const result: any = await executePythonCommand('query', {
      category: category,
      limit: 10000
    })
    
    if (result.success !== false) {
      // Transform assets to frontend format
      const assets = result.assets.map((asset: any) => ({
        id: asset.id,
        name: asset.file_name,
        tags: asset.ai_tags || [],
        duration: asset.duration || '0:00',
        used: asset.used || false,
        folderId: `folder-${asset.category}` // Simplified mapping
      }))
      
      return assets
    }
    
    return []
    
  } catch (error) {
    console.error('[RoughCut Electron] Failed to get assets:', error)
    return []
  }
})

// Handle graceful shutdown
process.on('SIGTERM', () => {
  console.log('[RoughCut Electron] SIGTERM received, shutting down...')
  cleanupAllProcesses()
  app.quit()
})

process.on('SIGINT', () => {
  console.log('[RoughCut Electron] SIGINT received, shutting down...')
  cleanupAllProcesses()
  app.quit()
})

// Cleanup on window close
app.on('before-quit', () => {
  cleanupAllProcesses()
})
