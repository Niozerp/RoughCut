import { contextBridge, ipcRenderer } from 'electron'

interface MediaFolders {
  music_folder: string | null
  sfx_folder: string | null
  vfx_folder: string | null
}

interface OnboardingState {
  completed: boolean
  configured_count: number
  folders: {
    music: boolean
    sfx: boolean
    vfx: boolean
  }
  has_invalid_folders: boolean
  invalid_folders: {
    music?: string
    sfx?: string
    vfx?: string
  }
}

interface SpacetimeRuntimeState {
  host: string
  port: number
  database_name: string
  module_path: string | null
  data_dir: string | null
  binary_path: string | null
  binary_version: string | null
  module_published: boolean
  module_fingerprint: string | null
  published_fingerprint: string | null
  last_ready_at: string | null
  last_health_check_at: string | null
}

interface ConfigState {
  media_folders: MediaFolders
  onboarding: OnboardingState
  spacetime: SpacetimeRuntimeState
}

interface BootstrapStatus {
  status: 'idle' | 'starting' | 'ready' | 'error'
  message: string
  error?: string
  spacetime: SpacetimeRuntimeState
}

interface StorageHealthStatus {
  status: 'idle' | 'starting' | 'ready' | 'degraded' | 'recovering' | 'error'
  message: string
  error?: string
  lastHealthyAt?: string | null
  lastCheckAt?: string | null
  recoveryAttemptCount?: number
  spacetime: SpacetimeRuntimeState
}

interface ResolveConnectionStatus {
  status: 'connected' | 'connecting' | 'disconnected'
  connected: boolean
  available: boolean
  attached: boolean
  project_name: string | null
  version: unknown
  module_error: string | null
  search_paths: string[]
}

interface IndexFoldersParams {
  folders: Array<{
    id: string
    path: string
    category: 'music' | 'sfx' | 'vfx'
  }>
  incremental?: boolean
  operationId?: string
}

interface ReindexFoldersParams {
  folders: Array<{
    id: string
    path: string
    category: 'music' | 'sfx' | 'vfx'
  }>
  operationId?: string
}

interface QueryAssetsParams {
  category: 'music' | 'sfx' | 'vfx'
  limit?: number
  folderPath?: string
  verifyOnDisk?: boolean
}

interface IndexProgressData {
  operationId: string
  category: 'music' | 'sfx' | 'vfx'
  type: string
  operation: string
  phase: 'discovery' | 'cataloguing' | 'writing' | 'cleanup' | 'complete'
  current: number
  total: number
  message: string
  databaseWriting: boolean
  batchCurrent?: number
  batchTotal?: number
}

interface StreamingAssetData {
  operationId: string
  category: 'music' | 'sfx' | 'vfx'
  asset: IndexedAsset
}

interface IndexedAsset {
  id: string
  file_name?: string
  file_path?: string
  ai_tags?: string[]
  duration?: string
  used?: boolean
}

interface QueryAssetsResult {
  success: boolean
  assets: IndexedAsset[]
  total_count: number
  database_connected: boolean
  error?: string
}

interface IndexResult {
  success: boolean
  operation_id: string
  category: 'music' | 'sfx' | 'vfx'
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

interface DatabaseStatus {
  success: boolean
  connected: boolean
  music_count: number
  sfx_count: number
  vfx_count: number
  total_count: number
  error?: string
}

interface AppInfo {
  version: string
  mode: 'electron'
  launchMode: 'standalone' | 'resolve'
  launchedFromResolve: boolean
  projectName: string | null
}

contextBridge.exposeInMainWorld('electronAPI', {
  getBootstrapStatus: () => ipcRenderer.invoke('bootstrap:get-status'),
  retryBootstrap: () => ipcRenderer.invoke('bootstrap:retry'),
  getStorageHealth: () => ipcRenderer.invoke('storage:get-health'),
  retryStorageRecovery: () => ipcRenderer.invoke('storage:retry-recovery'),
  getResolveStatus: () => ipcRenderer.invoke('resolve:get-status'),
  connectResolve: () => ipcRenderer.invoke('resolve:connect'),
  disconnectResolve: () => ipcRenderer.invoke('resolve:disconnect'),
  sendTimeline: (data: unknown) => ipcRenderer.invoke('resolve:send-timeline', data),
  getAppInfo: () => ipcRenderer.invoke('app:get-info'),
  getConfigState: () => ipcRenderer.invoke('config:get-state'),
  saveMediaFolders: (folders: MediaFolders) => ipcRenderer.invoke('config:save-media-folders', folders),
  setOnboardingComplete: (completed: boolean) =>
    ipcRenderer.invoke('config:set-onboarding-complete', { completed }),
  selectFolder: () => ipcRenderer.invoke('media:select-folder'),
  indexFolders: (params: IndexFoldersParams) => ipcRenderer.invoke('media:index-folders', params),
  reindexFolders: (params: ReindexFoldersParams) => ipcRenderer.invoke('media:reindex-folders', params),
  queryAssets: (params: QueryAssetsParams) => ipcRenderer.invoke('media:query-assets', params),
  getDatabaseStatus: () => ipcRenderer.invoke('media:database-status'),
  purgeCategoryAssets: (category: 'music' | 'sfx' | 'vfx') => ipcRenderer.invoke('media:purge-category', { category }),
  cancelIndexing: (operationId: string) => ipcRenderer.invoke('media:cancel-indexing', { operationId }),
  onIndexProgress: (callback: (event: unknown, data: IndexProgressData) => void) => {
    ipcRenderer.on('media:index-progress', callback)
  },
  removeIndexProgressListener: (callback: (event: unknown, data: IndexProgressData) => void) => {
    ipcRenderer.removeListener('media:index-progress', callback)
  },
  onStorageHealthChanged: (callback: (event: unknown, data: StorageHealthStatus) => void) => {
    ipcRenderer.on('storage:health-changed', callback)
  },
  removeStorageHealthListener: (callback: (event: unknown, data: StorageHealthStatus) => void) => {
    ipcRenderer.removeListener('storage:health-changed', callback)
  },
  onPythonLog: (callback: (event: unknown, data: { type: 'stdout' | 'stderr', message: string }) => void) => {
    ipcRenderer.on('python:log', callback)
  },
  removePythonLogListener: (callback: (event: unknown, data: { type: 'stdout' | 'stderr', message: string }) => void) => {
    ipcRenderer.removeListener('python:log', callback)
  },
  onStreamingAsset: (callback: (event: unknown, data: StreamingAssetData) => void) => {
    ipcRenderer.on('media:streaming-asset', callback)
  },
  removeStreamingAssetListener: (callback: (event: unknown, data: StreamingAssetData) => void) => {
    ipcRenderer.removeListener('media:streaming-asset', callback)
  },
})

declare global {
  interface Window {
    electronAPI: {
      getBootstrapStatus: () => Promise<BootstrapStatus>
      retryBootstrap: () => Promise<BootstrapStatus>
      getStorageHealth: () => Promise<StorageHealthStatus>
      retryStorageRecovery: () => Promise<StorageHealthStatus>
      getResolveStatus: () => Promise<ResolveConnectionStatus>
      connectResolve: () => Promise<ResolveConnectionStatus>
      disconnectResolve: () => Promise<ResolveConnectionStatus>
      sendTimeline: (data: unknown) => Promise<{ success: boolean; error?: string }>
      getAppInfo: () => Promise<AppInfo>
      getConfigState: () => Promise<ConfigState>
      saveMediaFolders: (folders: MediaFolders) => Promise<{
        success: boolean
        message: string
        media_folders: MediaFolders
        onboarding: OnboardingState
      }>
      setOnboardingComplete: (completed: boolean) => Promise<{
        success: boolean
        message: string
        onboarding: OnboardingState
      }>
      selectFolder: () => Promise<{ canceled: boolean; filePath: string | null; error?: string }>
      indexFolders: (params: IndexFoldersParams) => Promise<IndexResult>
      reindexFolders: (params: ReindexFoldersParams) => Promise<IndexResult>
      queryAssets: (params: QueryAssetsParams) => Promise<QueryAssetsResult>
      getDatabaseStatus: () => Promise<DatabaseStatus>
      purgeCategoryAssets: (category: 'music' | 'sfx' | 'vfx') => Promise<{ success: boolean; deleted_count: number; error?: string }>
      cancelIndexing: (operationId: string) => Promise<{ success: boolean; operation_id: string }>
      onIndexProgress: (callback: (event: unknown, data: IndexProgressData) => void) => void
      removeIndexProgressListener: (callback: (event: unknown, data: IndexProgressData) => void) => void
      onStorageHealthChanged: (callback: (event: unknown, data: StorageHealthStatus) => void) => void
      removeStorageHealthListener: (callback: (event: unknown, data: StorageHealthStatus) => void) => void
      onPythonLog: (callback: (event: unknown, data: { type: 'stdout' | 'stderr', message: string }) => void) => void
      removePythonLogListener: (callback: (event: unknown, data: { type: 'stdout' | 'stderr', message: string }) => void) => void
      onStreamingAsset: (callback: (event: unknown, data: StreamingAssetData) => void) => void
      removeStreamingAssetListener: (callback: (event: unknown, data: StreamingAssetData) => void) => void
    }
  }
}

export type {
  AppInfo,
  BootstrapStatus,
  ConfigState,
  DatabaseStatus,
  IndexProgressData,
  IndexResult,
  MediaFolders,
  OnboardingState,
  QueryAssetsResult,
  ResolveConnectionStatus,
  StorageHealthStatus,
}
