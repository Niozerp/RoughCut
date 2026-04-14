import { useEffect, useMemo, useRef, useState } from 'react'
import {
  AlertTriangle,
  Film,
  FolderOpen,
  HelpCircle,
  Loader2,
  Music,
  Search,
  Settings,
  Sparkles,
  Wand2,
  Zap,
} from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import {
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandShortcut,
} from '@/components/ui/command'
import { FormatTemplates } from '@/features/format-templates/FormatTemplates'
import { MediaBrowser } from '@/features/media-browser/MediaBrowser'
import { OnboardingWizard } from '@/features/onboarding/OnboardingWizard'
import { TimelineWorkspace } from '@/features/timeline/TimelineWorkspace'
import { buildStartupIndexRun, needsSetupReminder, shouldShowOnboarding } from '@/lib/app-state'
import type {
  AppInfo,
  BootstrapStatus,
  ConfigState,
  MediaFolders,
  ResolveConnectionStatus,
  StorageHealthStatus,
  StartupIndexRun,
} from '@/lib/roughcut-types'

const EMPTY_FOLDERS: MediaFolders = {
  music_folder: null,
  sfx_folder: null,
  vfx_folder: null,
}

const DEFAULT_CONFIG_STATE: ConfigState = {
  media_folders: EMPTY_FOLDERS,
  onboarding: {
    completed: false,
    configured_count: 0,
    folders: {
      music: false,
      sfx: false,
      vfx: false,
    },
    has_invalid_folders: false,
    invalid_folders: {},
  },
  spacetime: {
    host: 'localhost',
    port: 3000,
    database_name: 'roughcut',
    module_path: null,
    data_dir: null,
    binary_path: null,
    binary_version: null,
    module_published: false,
    module_fingerprint: null,
    published_fingerprint: null,
    last_ready_at: null,
    last_health_check_at: null,
  },
}

const DEFAULT_BOOTSTRAP_STATUS: BootstrapStatus = {
  status: 'starting',
  message: 'Starting local media storage...',
  spacetime: DEFAULT_CONFIG_STATE.spacetime,
}

const DEFAULT_RESOLVE_STATUS: ResolveConnectionStatus = {
  status: 'connecting',
  connected: false,
  available: false,
  attached: false,
  project_name: null,
  version: null,
  module_error: null,
  search_paths: [],
}

const DEFAULT_STORAGE_HEALTH: StorageHealthStatus = {
  status: 'starting',
  message: 'Starting local media storage...',
  error: undefined,
  lastHealthyAt: null,
  lastCheckAt: null,
  recoveryAttemptCount: 0,
  spacetime: DEFAULT_CONFIG_STATE.spacetime,
}

const DEFAULT_APP_INFO: AppInfo = {
  version: '0.0.0',
  mode: 'electron',
  launchMode: 'standalone',
  launchedFromResolve: false,
  projectName: null,
}

type InitialAppState = {
  appInfo: AppInfo
  bootstrapStatus: BootstrapStatus
  storageHealth: StorageHealthStatus
  configState: ConfigState
  resolveStatus: ResolveConnectionStatus
}

let initialAppStatePromise: Promise<InitialAppState> | null = null

function loadInitialAppState(): Promise<InitialAppState> {
  if (!initialAppStatePromise) {
    initialAppStatePromise = Promise.all([
      window.electronAPI.getAppInfo(),
      window.electronAPI.getBootstrapStatus(),
      window.electronAPI.getStorageHealth(),
      window.electronAPI.getConfigState(),
      window.electronAPI.getResolveStatus(),
    ])
      .then(([appInfo, bootstrapStatus, storageHealth, configState, resolveStatus]) => ({
        appInfo,
        bootstrapStatus,
        storageHealth,
        configState,
        resolveStatus,
      }))
      .catch((error) => {
        initialAppStatePromise = null
        throw error
      })
  }

  return initialAppStatePromise
}

function App() {
  const [bootstrapStatus, setBootstrapStatus] = useState<BootstrapStatus>(DEFAULT_BOOTSTRAP_STATUS)
  const [storageHealth, setStorageHealth] = useState<StorageHealthStatus>(DEFAULT_STORAGE_HEALTH)
  const [configState, setConfigState] = useState<ConfigState>(DEFAULT_CONFIG_STATE)
  const [resolveStatus, setResolveStatus] = useState<ResolveConnectionStatus>(DEFAULT_RESOLVE_STATUS)
  const [appInfo, setAppInfo] = useState<AppInfo>(DEFAULT_APP_INFO)
  const [commandOpen, setCommandOpen] = useState(false)
  const [isLoading, setIsLoading] = useState(true)
  const [showOnboarding, setShowOnboarding] = useState(false)
  const [isCompletingOnboarding, setIsCompletingOnboarding] = useState(false)
  const [onboardingError, setOnboardingError] = useState<string | null>(null)
  const [startupIndexRun, setStartupIndexRun] = useState<StartupIndexRun | null>(null)
  const processedStartupSignatures = useRef<Set<string>>(new Set())

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key === 'k') {
        event.preventDefault()
        setCommandOpen((current) => !current)
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [])

  // Listen for Python indexer logs and output to web console
  useEffect(() => {
    const handlePythonLog = (_event: unknown, data: { type: 'stdout' | 'stderr', message: string }) => {
      if (data.type === 'stderr') {
        console.warn(`[Python] ${data.message}`)
      } else {
        console.log(`[Python] ${data.message}`)
      }
    }

    window.electronAPI.onPythonLog(handlePythonLog)
    return () => {
      window.electronAPI.removePythonLogListener(handlePythonLog)
    }
  }, [])

  useEffect(() => {
    const loadState = async () => {
      try {
        const { appInfo, bootstrapStatus, storageHealth, configState, resolveStatus } =
          await loadInitialAppState()

        // Log version to web console for debugging
        console.log(`%c[RoughCut] Version: ${appInfo.version}`, 'color: #4CAF50; font-weight: bold; font-size: 14px;')

        setAppInfo(appInfo)
        setBootstrapStatus(bootstrapStatus)
        setStorageHealth(storageHealth)
        setConfigState(configState)
        setResolveStatus(resolveStatus)
        setShowOnboarding(shouldShowOnboarding(bootstrapStatus, configState))
        if (
          bootstrapStatus.status === 'ready' &&
          storageHealth.status === 'ready' &&
          !shouldShowOnboarding(bootstrapStatus, configState)
        ) {
          const nextRun = buildStartupIndexRun(configState.media_folders, Date.now())
          if (nextRun && !processedStartupSignatures.current.has(nextRun.signature)) {
            setStartupIndexRun(nextRun)
          }
        }
      } catch (error) {
        const message = error instanceof Error ? error.message : String(error)
        setBootstrapStatus({
          ...DEFAULT_BOOTSTRAP_STATUS,
          status: 'error',
          message: 'RoughCut could not finish startup.',
          error: message,
        })
        setStorageHealth({
          ...DEFAULT_STORAGE_HEALTH,
          status: 'error',
          message: 'Local media storage could not finish startup.',
          error: message,
        })
      } finally {
        setIsLoading(false)
      }
    }

    void loadState()
  }, [])

  useEffect(() => {
    const handleStorageHealth = (_event: unknown, nextHealth: StorageHealthStatus) => {
      setStorageHealth(nextHealth)
    }

    window.electronAPI.onStorageHealthChanged(handleStorageHealth)
    return () => {
      window.electronAPI.removeStorageHealthListener(handleStorageHealth)
    }
  }, [])

  const resolveIndicatorClass = useMemo(() => {
    if (resolveStatus.connected) {
      return 'bg-emerald-400'
    }

    if (resolveStatus.available) {
      return 'bg-amber-400'
    }

    return 'bg-zinc-500'
  }, [resolveStatus.available, resolveStatus.connected])

  const resolveStatusText = useMemo(() => {
    if (resolveStatus.connected) {
      return resolveStatus.project_name
        ? `Attached to ${resolveStatus.project_name}`
        : 'Attached to DaVinci'
    }

    if (resolveStatus.available) {
      return 'DaVinci detected and ready to attach'
    }

    return 'DaVinci not detected'
  }, [resolveStatus.available, resolveStatus.connected, resolveStatus.project_name])

  const showSetupReminder = needsSetupReminder(configState.onboarding)

  const handleRefreshResolveStatus = async () => {
    setResolveStatus((current) => ({ ...current, status: 'connecting' }))
    try {
      const nextStatus = await window.electronAPI.getResolveStatus()
      setResolveStatus(nextStatus)
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error)
      setResolveStatus({
        ...DEFAULT_RESOLVE_STATUS,
        status: 'disconnected',
        module_error: message,
      })
    }
  }

  const handleConnectResolve = async () => {
    setResolveStatus((current) => ({ ...current, status: 'connecting' }))
    try {
      const nextStatus = await window.electronAPI.connectResolve()
      setResolveStatus(nextStatus)
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error)
      setResolveStatus({
        ...DEFAULT_RESOLVE_STATUS,
        status: 'disconnected',
        module_error: message,
      })
    }
  }

  const handleDisconnectResolve = async () => {
    const nextStatus = await window.electronAPI.disconnectResolve()
    setResolveStatus(nextStatus)
  }

  const handleRetryBootstrap = async () => {
    setBootstrapStatus((current) => ({
      ...current,
      status: 'starting',
      message: 'Retrying local media storage startup...',
      error: undefined,
    }))

    const nextBootstrap = await window.electronAPI.retryBootstrap()
    setBootstrapStatus(nextBootstrap)
    setStorageHealth(await window.electronAPI.getStorageHealth())

    if (nextBootstrap.status === 'ready') {
      const nextConfigState = await window.electronAPI.getConfigState()
      const nextStorageHealth = await window.electronAPI.getStorageHealth()
      setConfigState(nextConfigState)
      setStorageHealth(nextStorageHealth)
      const shouldOnboard = shouldShowOnboarding(nextBootstrap, nextConfigState)
      setShowOnboarding(shouldOnboard)
      if (!shouldOnboard && nextStorageHealth.status === 'ready') {
        const nextRun = buildStartupIndexRun(nextConfigState.media_folders, Date.now())
        if (nextRun && !processedStartupSignatures.current.has(nextRun.signature)) {
          setStartupIndexRun(nextRun)
        }
      }
    }
  }

  const handleConfigStateChange = (nextState: ConfigState) => {
    setConfigState(nextState)
  }

  const handleRetryStorageRecovery = async () => {
    const nextHealth = await window.electronAPI.retryStorageRecovery()
    setStorageHealth(nextHealth)
    if (nextHealth.status === 'ready' && bootstrapStatus.status === 'ready' && !showOnboarding) {
      const nextRun = buildStartupIndexRun(configState.media_folders, Date.now())
      if (nextRun && !processedStartupSignatures.current.has(nextRun.signature)) {
        setStartupIndexRun(nextRun)
      }
    }
  }

  const handleOpenOnboarding = () => {
    setOnboardingError(null)
    setShowOnboarding(true)
    setCommandOpen(false)
  }

  const handleCompleteOnboarding = async (folders: MediaFolders) => {
    setIsCompletingOnboarding(true)
    setOnboardingError(null)

    try {
      const saveResult = await window.electronAPI.saveMediaFolders(folders)
      const onboardingResult = await window.electronAPI.setOnboardingComplete(true)

      const nextConfigState: ConfigState = {
        ...configState,
        media_folders: saveResult.media_folders,
        onboarding: onboardingResult.onboarding,
      }

      setConfigState(nextConfigState)
      setShowOnboarding(false)

      const requestId = Date.now()
      const nextIndexRun = buildStartupIndexRun(saveResult.media_folders, requestId)
      if (nextIndexRun) {
        setStartupIndexRun(nextIndexRun)
      }
    } catch (error) {
      setOnboardingError(error instanceof Error ? error.message : String(error))
    } finally {
      setIsCompletingOnboarding(false)
    }
  }

  useEffect(() => {
    if (
      isLoading ||
      bootstrapStatus.status !== 'ready' ||
      storageHealth.status !== 'ready' ||
      showOnboarding ||
      configState.onboarding.has_invalid_folders
    ) {
      return
    }

    const nextRun = buildStartupIndexRun(configState.media_folders, Date.now())
    if (!nextRun || processedStartupSignatures.current.has(nextRun.signature)) {
      return
    }

    setStartupIndexRun(nextRun)
  }, [
    bootstrapStatus.status,
    configState.media_folders,
    configState.onboarding.has_invalid_folders,
    isLoading,
    showOnboarding,
    storageHealth.status,
  ])

  const handleStartupIndexProcessed = (signature: string) => {
    processedStartupSignatures.current.add(signature)
  }

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background p-6">
        <Card className="w-full max-w-lg">
          <CardHeader>
            <CardTitle>Loading RoughCut</CardTitle>
            <CardDescription>Preparing the standalone workspace and local media storage.</CardDescription>
          </CardHeader>
          <CardContent className="flex items-center gap-3 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" />
            <span>{bootstrapStatus.message}</span>
          </CardContent>
        </Card>
      </div>
    )
  }

  if (bootstrapStatus.status === 'error') {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background p-6">
        <Card className="w-full max-w-2xl">
          <CardHeader>
            <Badge variant="destructive" className="w-fit">
              Local Storage Required
            </Badge>
            <CardTitle className="mt-3">SpacetimeDB Could Not Start</CardTitle>
            <CardDescription>
              RoughCut blocks indexing and media search until the local SpacetimeDB runtime is
              healthy.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="whitespace-pre-wrap rounded-lg border border-destructive/30 bg-destructive/10 p-4 text-sm text-destructive">
              {bootstrapStatus.error || bootstrapStatus.message}
            </div>
            <div className="space-y-2 text-sm text-muted-foreground">
              <p>Binary: {bootstrapStatus.spacetime.binary_path || 'Not found'}</p>
              <p>Module: {bootstrapStatus.spacetime.module_path || 'Not found'}</p>
              <p>Data dir: {bootstrapStatus.spacetime.data_dir || 'Not set'}</p>
            </div>
            <div className="flex flex-wrap gap-3">
              <Button onClick={() => void handleRetryBootstrap()}>Retry Startup</Button>
              <Button variant="outline" onClick={() => void handleRefreshResolveStatus()}>
                Refresh DaVinci Status
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    )
  }

  if (showOnboarding) {
    return (
      <OnboardingWizard
        initialFolders={configState.media_folders}
        onboardingState={configState.onboarding}
        allowClose={configState.onboarding.completed}
        isCompleting={isCompletingOnboarding}
        completionError={onboardingError}
        onClose={configState.onboarding.completed ? () => setShowOnboarding(false) : undefined}
        onComplete={handleCompleteOnboarding}
      />
    )
  }

  return (
    <div className="flex h-screen flex-col overflow-hidden bg-background text-foreground">
      <header className="flex h-12 items-center justify-between border-b border-border bg-card/50 px-4">
        <div className="flex items-center gap-3">
          <Film className="h-5 w-5 text-primary" />
          <div className="flex items-center gap-2">
            <h1 className="text-lg font-semibold">RoughCut</h1>
            <Badge variant="outline">{appInfo.launchMode === 'resolve' ? 'Resolve Mode' : 'Standalone'}</Badge>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 text-sm">
            <span className={`h-2.5 w-2.5 rounded-full ${resolveIndicatorClass}`} />
            <span className="text-muted-foreground">{resolveStatusText}</span>
          </div>

          <Button
            variant={resolveStatus.connected ? 'outline' : 'default'}
            size="sm"
            onClick={() => void (resolveStatus.connected ? handleDisconnectResolve() : handleConnectResolve())}
          >
            {resolveStatus.connected ? 'Disconnect' : 'Connect to DaVinci'}
          </Button>

          {showSetupReminder && (
            <Button variant="outline" size="sm" onClick={handleOpenOnboarding}>
              <FolderOpen className="mr-2 h-4 w-4" />
              Finish Setup
            </Button>
          )}

          <Button
            variant="outline"
            size="sm"
            className="h-8 gap-2 text-muted-foreground"
            onClick={() => setCommandOpen(true)}
          >
            <Search className="h-3.5 w-3.5" />
            <span className="text-xs">Search...</span>
            <kbd className="pointer-events-none hidden h-5 select-none items-center gap-1 rounded border bg-muted px-1.5 font-mono text-[10px] font-medium opacity-100 sm:flex">
              <span className="text-xs">⌘</span>K
            </kbd>
          </Button>

          <div className="flex items-center gap-1">
            <Button variant="ghost" size="icon" className="h-8 w-8">
              <Settings className="h-4 w-4" />
            </Button>
            <Button variant="ghost" size="icon" className="h-8 w-8">
              <HelpCircle className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </header>

      {storageHealth.status !== 'ready' && (
        <div className="border-b border-amber-500/30 bg-amber-500/10 px-4 py-3">
          <div className="flex items-center justify-between gap-4">
            <div className="flex items-start gap-3">
              <AlertTriangle className="mt-0.5 h-4 w-4 text-amber-500" />
              <div className="space-y-1">
                <p className="text-sm font-medium text-amber-200">
                  Local media storage is {storageHealth.status}.
                </p>
                <p className="text-sm text-amber-100/80">
                  {storageHealth.error || storageHealth.message}
                </p>
              </div>
            </div>
            <Button variant="outline" size="sm" onClick={() => void handleRetryStorageRecovery()}>
              Retry Storage Recovery
            </Button>
          </div>
        </div>
      )}

      <CommandDialog open={commandOpen} onOpenChange={setCommandOpen}>
        <CommandInput placeholder="Search assets, templates, or actions..." />
        <CommandList>
          <CommandEmpty>No results found.</CommandEmpty>
          <CommandGroup heading="Assets">
            <CommandItem>
              <Music className="mr-2 h-4 w-4" />
              <span>Music Library</span>
              <CommandShortcut>⌘M</CommandShortcut>
            </CommandItem>
            <CommandItem>
              <Zap className="mr-2 h-4 w-4" />
              <span>Sound Effects</span>
              <CommandShortcut>⌘S</CommandShortcut>
            </CommandItem>
            <CommandItem>
              <Sparkles className="mr-2 h-4 w-4" />
              <span>VFX Templates</span>
              <CommandShortcut>⌘V</CommandShortcut>
            </CommandItem>
          </CommandGroup>
          <CommandGroup heading="Actions">
            <CommandItem
              onSelect={() => {
                handleOpenOnboarding()
              }}
            >
              <FolderOpen className="mr-2 h-4 w-4" />
              <span>Configure Media Folders</span>
            </CommandItem>
            <CommandItem onSelect={() => void handleConnectResolve()}>
              <Film className="mr-2 h-4 w-4" />
              <span>Attach to DaVinci</span>
            </CommandItem>
            <CommandItem>
              <Wand2 className="mr-2 h-4 w-4" />
              <span>Generate Rough Cut</span>
              <CommandShortcut>⌘G</CommandShortcut>
            </CommandItem>
          </CommandGroup>
        </CommandList>
      </CommandDialog>

      <div className="flex flex-1 overflow-hidden">
        <aside className="flex w-80 flex-col border-r border-border bg-card/30">
          <MediaBrowser
            bootstrapStatus={bootstrapStatus}
            storageHealth={storageHealth}
            configState={configState}
            startupIndexRun={startupIndexRun}
            onStartupIndexProcessed={handleStartupIndexProcessed}
            onConfigStateChange={handleConfigStateChange}
          />
        </aside>

        <main className="flex flex-1 flex-col bg-background">
          <TimelineWorkspace
            resolveStatus={resolveStatus}
            onConnectResolve={() => void handleConnectResolve()}
          />
        </main>

        <aside className="flex w-72 flex-col border-l border-border bg-card/30">
          <FormatTemplates />
        </aside>
      </div>
    </div>
  )
}

export default App
