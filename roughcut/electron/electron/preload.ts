import { contextBridge, ipcRenderer } from 'electron'

console.log('[Preload] Script starting execution...')
console.log('[Preload] process.contextIsolated:', process.contextIsolated)

try {
  if (!process.contextIsolated) {
    console.warn('[Preload] WARNING: contextIsolation is disabled - this is insecure!')
    // Fall back to direct window assignment (for debugging only)
    throw new Error('contextIsolation must be enabled for security')
  }

  // Use contextBridge for secure exposure
  contextBridge.exposeInMainWorld('electronAPI', {
    // Existing methods
    checkResolveConnection: () => ipcRenderer.invoke('resolve:check-connection'),
    sendTimeline: (data: unknown) => ipcRenderer.invoke('resolve:send-timeline', data),
    getAssets: (category: string) => ipcRenderer.invoke('media:get-assets', category),
    selectFolder: () => ipcRenderer.invoke('media:select-folder'),
    
    // NEW: Indexing methods
    indexFolders: (params: IndexFoldersParams) => ipcRenderer.invoke('media:index-folders', params),
    reindexFolders: (params: ReindexFoldersParams) => ipcRenderer.invoke('media:reindex-folders', params),
    queryAssets: (params: QueryAssetsParams) => ipcRenderer.invoke('media:query-assets', params),
    getDatabaseStatus: () => ipcRenderer.invoke('media:database-status'),
    cancelIndexing: (operationId: string) => ipcRenderer.invoke('media:cancel-indexing', { operationId }),
    
    // NEW: Progress listener setup
    onIndexProgress: (callback: (event: unknown, data: IndexProgressData) => void) => {
      ipcRenderer.on('media:index-progress', callback)
    },
    removeIndexProgressListener: (callback: (event: unknown, data: IndexProgressData) => void) => {
      ipcRenderer.removeListener('media:index-progress', callback)
    }
  })

  console.log('[Preload] electronAPI exposed via contextBridge')
  console.log('[Preload] Script execution completed')
} catch (error) {
  console.error('[Preload] FATAL ERROR exposing API:', error)
}

// Type definitions for the new API
interface IndexFoldersParams {
  folders: Array<{
    id: string
    path: string
    category: 'music' | 'sfx' | 'vfx'
  }>
  incremental?: boolean
}

interface ReindexFoldersParams {
  folders: Array<{
    id: string
    path: string
    category: 'music' | 'sfx' | 'vfx'
  }>
}

interface QueryAssetsParams {
  category: 'music' | 'sfx' | 'vfx'
  limit?: number
}

interface IndexProgressData {
  operationId: string
  type: string
  operation: string
  current: number
  total: number
  message: string
}

interface IndexResult {
  success: boolean
  operation_id: string
  indexed_count: number
  new_count: number
  modified_count: number
  deleted_count: number
  moved_count: number
  total_scanned: number
  duration_ms: number
  errors: string[]
  database_connected: boolean
  progress_updates: IndexProgressData[]
  error?: string
  error_type?: string
}

interface Asset {
  id: string
  name: string
  tags: string[]
  duration: string
  used: boolean
  folderId: string
}

interface DatabaseStatus {
  success: boolean
  connected: boolean
  music_count: number
  sfx_count: number
  vfx_count: number
  total_count: number
  error?: string
}

// TypeScript support
declare global {
  interface Window {
    electronAPI: {
      // Existing
      checkResolveConnection: () => Promise<{ status: string }>
      sendTimeline: (data: unknown) => Promise<{ success: boolean }>
      getAssets: (category: string) => Promise<Asset[]>
      selectFolder: () => Promise<{ canceled: boolean; filePath: string | null; error?: string }>
      
      // NEW: Indexing
      indexFolders: (params: IndexFoldersParams) => Promise<IndexResult>
      reindexFolders: (params: ReindexFoldersParams) => Promise<IndexResult>
      queryAssets: (params: QueryAssetsParams) => Promise<{ success: boolean; assets: Asset[]; total_count: number; database_connected: boolean; error?: string }>
      getDatabaseStatus: () => Promise<DatabaseStatus>
      cancelIndexing: (operationId: string) => Promise<{ success: boolean; operation_id: string }>
      
      // NEW: Progress events
      onIndexProgress: (callback: (event: unknown, data: IndexProgressData) => void) => void
      removeIndexProgressListener: (callback: (event: unknown, data: IndexProgressData) => void) => void
    }
  }
}
