import { app, BrowserWindow, dialog, ipcMain } from 'electron'
import fs from 'fs'
import path from 'path'
import { fileURLToPath } from 'url'

import {
  cancelIndexing,
  cleanupAllProcesses,
  executePythonCommand,
  getActiveIndexingOperations,
} from './pythonBridge.js'
import { bootstrapAndCreateWindow } from './appBootstrap.js'
import { getSpacetimeManager } from './spacetimeManager.js'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)

type ResolveUiStatus = 'connected' | 'connecting' | 'disconnected'

interface ResolveConnectionStatus {
  status: ResolveUiStatus
  connected: boolean
  available: boolean
  attached: boolean
  project_name: string | null
  version: unknown
  module_error: string | null
  search_paths: string[]
}

interface MediaFolderPayload {
  music_folder?: string | null
  sfx_folder?: string | null
  vfx_folder?: string | null
}

let mainWindow: BrowserWindow | null = null
const launchMode = process.env.ROUGHCUT_LAUNCH_MODE === 'resolve' ? 'resolve' : 'standalone'
let resolveAttached = launchMode === 'resolve'

const spacetimeManager = getSpacetimeManager()

spacetimeManager.onHealthChanged((status) => {
  if (mainWindow && !mainWindow.isDestroyed()) {
    mainWindow.webContents.send('storage:health-changed', status)
  }
})

function createWindow() {
  const possiblePreloadPaths = [
    path.join(__dirname, 'preload.js'),
    path.join(__dirname, 'electron', 'preload.js'),
    path.join(app.getAppPath(), 'electron', 'preload.js'),
    path.join(process.cwd(), 'electron', 'preload.js'),
  ]

  const preloadPath = possiblePreloadPaths.find((candidate) => fs.existsSync(candidate)) ?? null

  if (!preloadPath) {
    console.error('[RoughCut Electron] preload.js not found in expected locations:', possiblePreloadPaths)
  }

  const webPreferences: Electron.WebPreferences = {
    contextIsolation: true,
    nodeIntegration: false,
    preload: preloadPath ?? undefined,
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

  mainWindow.webContents.on('console-message', (_event, level, message) => {
    const levelName = ['debug', 'info', 'warn', 'error'][level] || 'log'
    console.log(`[Renderer ${levelName.toUpperCase()}] ${message}`)
  })

  if (process.env.VITE_DEV_SERVER_URL) {
    mainWindow.loadURL(process.env.VITE_DEV_SERVER_URL)
    mainWindow.webContents.openDevTools()
  } else {
    mainWindow.loadFile(path.join(__dirname, '../index.html'))
  }

  mainWindow.once('ready-to-show', () => {
    mainWindow?.show()
  })

  mainWindow.on('closed', () => {
    mainWindow = null
  })
}

function normalizeResolveStatus(result: any): ResolveConnectionStatus {
  const available = Boolean(result?.available ?? result?.connected)
  if (!available) {
    resolveAttached = false
  }

  const attached = available ? resolveAttached : false
  return {
    status: attached ? 'connected' : 'disconnected',
    connected: attached,
    available,
    attached,
    project_name: result?.project_name ?? null,
    version: result?.version ?? null,
    module_error: result?.module_error ?? null,
    search_paths: Array.isArray(result?.search_paths) ? result.search_paths : [],
  }
}

async function getResolveStatus(command: 'resolve_status' | 'resolve_connect' = 'resolve_status') {
  const result = await executePythonCommand(command, {})
  if (command === 'resolve_connect') {
    resolveAttached = Boolean(result?.available ?? result?.connected)
  }
  return normalizeResolveStatus(result)
}

async function ensureStorageReady() {
  const status = await spacetimeManager.ensureReady()
  if (status.status !== 'ready') {
    throw new Error(status.error || status.message)
  }

  return status
}

function mapFolder(category: string, folderPath: string) {
  return {
    id: `${category}-${Date.now()}`,
    path: folderPath,
    category,
  }
}

app.whenReady().then(async () => {
  console.log(`[RoughCut Electron] App starting in ${launchMode} mode...`)
  const launched = await bootstrapAndCreateWindow({
    createWindow,
    ensureReady: () => spacetimeManager.ensureReady(),
    logFailure: (message) => {
      console.error('[RoughCut Electron] Prelaunch bootstrap failed:', message)
    },
    quit: () => {
      app.quit()
    },
  })

  if (!launched) {
    return
  }

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

ipcMain.handle('bootstrap:get-status', async () => {
  return spacetimeManager.ensureReady()
})

ipcMain.handle('bootstrap:retry', async () => {
  return spacetimeManager.retry()
})

ipcMain.handle('storage:get-health', async () => {
  return spacetimeManager.getStorageHealth()
})

ipcMain.handle('storage:retry-recovery', async () => {
  return spacetimeManager.retryRecovery()
})

ipcMain.handle('resolve:get-status', async () => {
  try {
    return await getResolveStatus()
  } catch (error: any) {
    resolveAttached = false
    return normalizeResolveStatus({
      available: false,
      connected: false,
      module_error: error?.message || String(error),
      search_paths: [],
    })
  }
})

ipcMain.handle('resolve:connect', async () => {
  try {
    return await getResolveStatus('resolve_connect')
  } catch (error: any) {
    resolveAttached = false
    return normalizeResolveStatus({
      available: false,
      connected: false,
      module_error: error?.message || String(error),
      search_paths: [],
    })
  }
})

ipcMain.handle('resolve:disconnect', async () => {
  resolveAttached = false

  try {
    await executePythonCommand('resolve_disconnect', {})
  } catch (error) {
    console.warn('[RoughCut Electron] Resolve disconnect command failed:', error)
  }

  return normalizeResolveStatus({
    available: false,
    connected: false,
    project_name: null,
    version: null,
    module_error: null,
    search_paths: [],
  })
})

ipcMain.handle('resolve:send-timeline', async (_event, data) => {
  if (!resolveAttached) {
    return {
      success: false,
      error: 'Not connected to DaVinci Resolve.',
    }
  }

  try {
    const result = await executePythonCommand('resolve_send_timeline', data ?? {})
    return {
      success: true,
      ...result,
    }
  } catch (error: any) {
    return {
      success: false,
      error: error?.message || String(error),
    }
  }
})

ipcMain.handle('config:get-state', async () => {
  return executePythonCommand('config_state', {})
})

ipcMain.handle('config:save-media-folders', async (_event, payload: MediaFolderPayload) => {
  return executePythonCommand('save_media_folders', payload)
})

// Read version from version.md
function getAppVersion(): string {
  try {
    const versionPath = path.join(__dirname, '..', 'version.md')
    if (fs.existsSync(versionPath)) {
      const version = fs.readFileSync(versionPath, 'utf-8').trim()
      return version || '1.0.0'
    }
  } catch (e) {
    console.error('[Main] Failed to read version.md:', e)
  }
  return app.getVersion()
}

ipcMain.handle('config:set-onboarding-complete', async (_event, payload: { completed: boolean }) => {
  return executePythonCommand('set_onboarding_complete', payload)
})

ipcMain.handle('app:get-info', async () => {
  const version = getAppVersion()
  console.log(`[Main] RoughCut version: ${version}`)
  return {
    version,
    mode: 'electron',
    launchMode,
    launchedFromResolve: launchMode === 'resolve',
    projectName: process.env.ROUGHCUT_PROJECT ?? null,
  }
})

ipcMain.handle('media:select-folder', async () => {
  if (!mainWindow || mainWindow.isDestroyed()) {
    return { canceled: true, filePath: null, error: 'Main window not available' }
  }

  try {
    const result = await dialog.showOpenDialog(mainWindow, {
      properties: ['openDirectory'],
      title: 'Select Media Folder',
      buttonLabel: 'Select Folder',
    })

    return {
      canceled: result.canceled,
      filePath: result.canceled ? null : result.filePaths[0],
    }
  } catch (error) {
    return { canceled: true, filePath: null, error: String(error) }
  }
})

ipcMain.handle(
  'media:index-folders',
  async (
    _event,
    params: {
      folders: Array<{ id: string; path: string; category: string }>
      incremental?: boolean
      operationId?: string
    }
  ) => {
    try {
      await ensureStorageReady()

      const folder = (params.folders || [])[0]
      if (!folder) {
        throw new Error('No folder was provided for indexing.')
      }

      const operationId = params.operationId || `index_${folder.category}_${Date.now()}`
      const progressUpdates: any[] = []
      const result: any = await executePythonCommand(
        'index',
        {
          folders: [folder],
          incremental: params.incremental !== false,
        },
        (progress: any) => {
          progressUpdates.push(progress)
          if (mainWindow && !mainWindow.isDestroyed()) {
            mainWindow.webContents.send('media:index-progress', {
              operationId,
              category: folder.category,
              ...progress,
            })
          }
        },
        (log: { type: 'stdout' | 'stderr', message: string }) => {
          // Forward Python logs to renderer/web console
          if (mainWindow && !mainWindow.isDestroyed()) {
            mainWindow.webContents.send('python:log', log)
          }
        },
        (asset: any) => {
          // Real-time asset streaming - send to renderer immediately as each asset is indexed
          if (mainWindow && !mainWindow.isDestroyed()) {
            mainWindow.webContents.send('media:streaming-asset', {
              operationId,
              category: folder.category,
              asset,
            })
          }
        },
        operationId
      )

      result.progress_updates = progressUpdates
      result.operation_id = operationId
      result.category = folder.category
      return { success: true, ...result }
    } catch (error: any) {
      return {
        success: false,
        error: error?.message || String(error),
        error_type: 'INDEXING_FAILED',
      }
    }
  }
)

ipcMain.handle(
  'media:reindex-folders',
  async (
    _event,
    params: {
      folders: Array<{ id: string; path: string; category: string }>
      operationId?: string
    }
  ) => {
    try {
      await ensureStorageReady()

      const folder = (params.folders || [])[0]
      if (!folder) {
        throw new Error('No folder was provided for reindexing.')
      }

      const operationId = params.operationId || `reindex_${folder.category}_${Date.now()}`
      const progressUpdates: any[] = []
      const result: any = await executePythonCommand(
        'reindex',
        {
          folders: [folder],
        },
        (progress: any) => {
          progressUpdates.push(progress)
          if (mainWindow && !mainWindow.isDestroyed()) {
            mainWindow.webContents.send('media:index-progress', {
              operationId,
              category: folder.category,
              ...progress,
            })
          }
        },
        (log: { type: 'stdout' | 'stderr', message: string }) => {
          // Forward Python logs to renderer/web console
          if (mainWindow && !mainWindow.isDestroyed()) {
            mainWindow.webContents.send('python:log', log)
          }
        },
        (asset: any) => {
          // Real-time asset streaming - send to renderer immediately as each asset is indexed
          if (mainWindow && !mainWindow.isDestroyed()) {
            mainWindow.webContents.send('media:streaming-asset', {
              operationId,
              category: folder.category,
              asset,
            })
          }
        },
        operationId
      )

      result.progress_updates = progressUpdates
      result.operation_id = operationId
      result.category = folder.category
      return { success: true, ...result }
    } catch (error: any) {
      return {
        success: false,
        error: error?.message || String(error),
        error_type: 'REINDEXING_FAILED',
      }
    }
  }
)

ipcMain.handle('media:query-assets', async (_event, params: { category: string; limit?: number; folderPath?: string; verifyOnDisk?: boolean }) => {
  try {
    await ensureStorageReady()
    const result: any = await executePythonCommand('query', {
      category: params.category,
      limit: params.limit || 1000,
      folder_path: params.folderPath,
      verify_on_disk: params.verifyOnDisk === true,
    })

    return { success: true, ...result }
  } catch (error: any) {
    return {
      success: false,
      error: error?.message || String(error),
      assets: [],
      total_count: 0,
      database_connected: false,
    }
  }
})

ipcMain.handle('media:purge-category', async (_event, params: { category: string }) => {
  try {
    await ensureStorageReady()
    const result: any = await executePythonCommand('purge_category', {
      category: params.category,
    })
    return { success: true, ...result }
  } catch (error: any) {
    return {
      success: false,
      deleted_count: 0,
      error: error?.message || String(error),
    }
  }
})

ipcMain.handle('media:database-status', async () => {
  try {
    const bootstrap = await ensureStorageReady()
    const result = spacetimeManager.getDatabaseStatus()

    return {
      bootstrap,
      ...result,
    }
  } catch (error: any) {
    return {
      success: false,
      error: error?.message || String(error),
      connected: false,
      music_count: 0,
      sfx_count: 0,
      vfx_count: 0,
      total_count: 0,
    }
  }
})

ipcMain.handle('media:indexing-operations', async () => {
  const operations = getActiveIndexingOperations()
  return { success: true, operations }
})

ipcMain.handle('media:cancel-indexing', async (_event, params: { operationId: string }) => {
  return {
    success: cancelIndexing(params.operationId),
    operation_id: params.operationId,
  }
})

ipcMain.handle('media:get-assets', async (_event, category: string) => {
  try {
    await ensureStorageReady()
    const result: any = await executePythonCommand('query', {
      category,
      limit: 10000,
    })

    if (!Array.isArray(result.assets)) {
      return []
    }

    return result.assets.map((asset: any) => ({
      id: asset.id,
      name: asset.file_name,
      tags: asset.ai_tags || [],
      duration: asset.duration || '0:00',
      used: asset.used || false,
      folderId: mapFolder(category, asset.file_path).id,
    }))
  } catch (error) {
    console.error('[RoughCut Electron] Failed to get assets:', error)
    return []
  }
})

process.on('SIGTERM', () => {
  cleanupAllProcesses()
  spacetimeManager.stop()
  app.quit()
})

process.on('SIGINT', () => {
  cleanupAllProcesses()
  spacetimeManager.stop()
  app.quit()
})

app.on('before-quit', () => {
  cleanupAllProcesses()
  spacetimeManager.stop()
})
