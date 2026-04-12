export type Category = 'music' | 'sfx' | 'vfx'

export interface MediaFolders {
  music_folder: string | null
  sfx_folder: string | null
  vfx_folder: string | null
}

export interface OnboardingState {
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

export interface SpacetimeRuntimeState {
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

export interface ConfigState {
  media_folders: MediaFolders
  onboarding: OnboardingState
  spacetime: SpacetimeRuntimeState
}

export interface BootstrapStatus {
  status: 'idle' | 'starting' | 'ready' | 'error'
  message: string
  error?: string
  error_code?: 'PORT_IN_USE' | 'DATA_DIR_LOCKED' | 'SERVER_START_FAILED' | 'MODULE_PUBLISH_FAILED'
  spacetime: SpacetimeRuntimeState
}

export interface StorageHealthStatus {
  status: 'idle' | 'starting' | 'ready' | 'degraded' | 'recovering' | 'error'
  message: string
  error?: string
  error_code?: 'PORT_IN_USE' | 'DATA_DIR_LOCKED' | 'SERVER_START_FAILED' | 'MODULE_PUBLISH_FAILED'
  lastHealthyAt?: string | null
  lastCheckAt?: string | null
  recoveryAttemptCount?: number
  spacetime: SpacetimeRuntimeState
}

export interface ResolveConnectionStatus {
  status: 'connected' | 'connecting' | 'disconnected'
  connected: boolean
  available: boolean
  attached: boolean
  project_name: string | null
  version: unknown
  module_error: string | null
  search_paths: string[]
}

export interface AppInfo {
  version: string
  mode: 'electron'
  launchMode: 'standalone' | 'resolve'
  launchedFromResolve: boolean
  projectName: string | null
}

export type IndexPhase = 'scan' | 'index' | 'store' | 'cleanup' | 'complete'
export type IndexSource = 'startup' | 'manual'

export interface IndexJob {
  id: string
  category: Category
  path: string
  incremental: boolean
  source: IndexSource
}

export interface StartupIndexRun {
  id: number
  jobs: IndexJob[]
  signature: string
}

export interface IndexProgressData {
  operationId: string
  category: Category
  type: string
  operation: string
  phase: IndexPhase
  current: number
  total: number
  message: string
  databaseWriting: boolean
  batchCurrent?: number
  batchTotal?: number
}

export interface IndexResult {
  success: boolean
  operation_id: string
  category: Category
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

export interface QueryAssetsParams {
  category: Category
  limit?: number
  folderPath?: string
  verifyOnDisk?: boolean
}
