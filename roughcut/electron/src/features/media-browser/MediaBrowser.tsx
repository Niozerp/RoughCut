import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import {
  Clapperboard,
  Database,
  Filter,
  FolderOpen,
  Heart,
  Loader2,
  Music,
  Plus,
  RefreshCw,
  Search,
  Star,
  X,
  Zap,
} from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip'
import type {
  BootstrapStatus,
  Category,
  ConfigState,
  IndexJob,
  IndexProgressData,
  IndexResult,
  MediaFolders,
  StorageHealthStatus,
  StartupIndexRun,
} from '@/lib/roughcut-types'

type FilterType = 'all' | 'used' | 'unused' | 'favorites'
type IndexingState = 'idle' | 'indexing' | 'complete' | 'error'

interface MediaBrowserProps {
  bootstrapStatus: BootstrapStatus
  storageHealth: StorageHealthStatus
  configState: ConfigState
  startupIndexRun: StartupIndexRun | null
  onStartupIndexProcessed: (signature: string) => void
  onConfigStateChange: (next: ConfigState) => void
}

interface BrowserAsset {
  id: string
  name: string
  tags: string[]
  duration: string
  used: boolean
}

const CATEGORY_LABELS: Record<Category, string> = {
  music: 'Music',
  sfx: 'Sound Effects',
  vfx: 'Visual Effects',
}

const CATEGORY_ICONS = {
  music: Music,
  sfx: Zap,
  vfx: Clapperboard,
}

const EMPTY_ASSETS: Record<Category, BrowserAsset[]> = {
  music: [],
  sfx: [],
  vfx: [],
}

const EMPTY_PROGRESS: Record<Category, IndexProgressData | null> = {
  music: null,
  sfx: null,
  vfx: null,
}

const EMPTY_INDEXING_STATE: Record<Category, IndexingState> = {
  music: 'idle',
  sfx: 'idle',
  vfx: 'idle',
}

function getFolderPath(folders: MediaFolders, category: Category): string | null {
  return folders[`${category}_folder` as keyof MediaFolders]
}

function setFolderPath(folders: MediaFolders, category: Category, value: string | null): MediaFolders {
  return {
    ...folders,
    [`${category}_folder`]: value,
  } as MediaFolders
}

export function MediaBrowser({
  bootstrapStatus,
  storageHealth,
  configState,
  startupIndexRun,
  onStartupIndexProcessed,
  onConfigStateChange,
}: MediaBrowserProps) {
  const [activeFilter, setActiveFilter] = useState<FilterType>('all')
  const [searchQuery, setSearchQuery] = useState('')
  const [activeCategory, setActiveCategory] = useState<Category>('music')
  const [isManageModalOpen, setIsManageModalOpen] = useState(false)
  const [selectedManageTab, setSelectedManageTab] = useState<Category>('music')
  const [assetsByCategory, setAssetsByCategory] = useState<Record<Category, BrowserAsset[]>>(EMPTY_ASSETS)
  const [indexingState, setIndexingState] = useState<Record<Category, IndexingState>>(EMPTY_INDEXING_STATE)
  const [indexingProgress, setIndexingProgress] = useState<Record<Category, IndexProgressData | null>>(EMPTY_PROGRESS)
  const [databaseStatus, setDatabaseStatus] = useState<{ connected: boolean; totalCount: number }>({
    connected: false,
    totalCount: 0,
  })

  const processedStartupIndexRun = useRef<number | null>(null)

  const filters = [
    { id: 'all' as FilterType, label: 'All', icon: Filter },
    { id: 'used' as FilterType, label: 'Used', icon: Star },
    { id: 'unused' as FilterType, label: 'Unused', icon: RefreshCw },
    { id: 'favorites' as FilterType, label: 'Favorites', icon: Heart },
  ]

  const updateCategoryAssets = useCallback((category: Category, assets: BrowserAsset[]) => {
    setAssetsByCategory((current) => ({
      ...current,
      [category]: assets,
    }))
  }, [])

  const storageReady = storageHealth.status === 'ready' && bootstrapStatus.status === 'ready'

  const checkDatabaseStatus = useCallback(async () => {
    if (!storageReady) {
      setDatabaseStatus({ connected: false, totalCount: 0 })
      return
    }

    try {
      const activeCategories = (['music', 'sfx', 'vfx'] as Category[]).filter((category) =>
        Boolean(getFolderPath(configState.media_folders, category))
      )

      const queryResults = await Promise.all(
        activeCategories.map((category) =>
          window.electronAPI.queryAssets({
            category,
            folderPath: getFolderPath(configState.media_folders, category) || undefined,
            limit: 1000,
            verifyOnDisk: true,
          })
        )
      )

      const totalCount = queryResults.reduce(
        (sum, result) => sum + (result.success ? result.total_count : 0),
        0
      )

      setDatabaseStatus({
        connected: true,
        totalCount,
      })
    } catch (error) {
      console.error('[MediaBrowser] Failed to get database status:', error)
      setDatabaseStatus({ connected: false, totalCount: 0 })
    }
  }, [configState.media_folders, storageReady])

  const loadAssetsForCategory = useCallback(
    async (category: Category) => {
      const folderPath = getFolderPath(configState.media_folders, category)
      if (!folderPath || !storageReady) {
        updateCategoryAssets(category, [])
        return
      }

      try {
        const result = await window.electronAPI.queryAssets({
          category,
          folderPath,
          limit: 1000,
          verifyOnDisk: true,
        })
        if (!result.success) {
          updateCategoryAssets(category, [])
          return
        }

        const assets = result.assets.map((asset) => ({
          id: asset.id,
          name: asset.file_name || 'Unknown asset',
          tags: asset.ai_tags || [],
          duration: asset.duration || '0:00',
          used: asset.used || false,
        }))

        updateCategoryAssets(category, assets)
      } catch (error) {
        console.error(`[MediaBrowser] Failed to load ${category} assets:`, error)
      }
    },
    [configState.media_folders, storageReady, updateCategoryAssets]
  )

  const persistFolders = useCallback(
    async (nextFolders: MediaFolders) => {
      const result = await window.electronAPI.saveMediaFolders(nextFolders)
      onConfigStateChange({
        ...configState,
        media_folders: result.media_folders,
        onboarding: result.onboarding,
      })

      return result.media_folders
    },
    [configState, onConfigStateChange]
  )

  const runIndexJob = useCallback(
    async (job: IndexJob): Promise<IndexResult> => {
      if (bootstrapStatus.status !== 'ready') {
        throw new Error('Storage is not ready for indexing.')
      }

      if (!storageReady) {
        throw new Error('Storage health is not ready.')
      }

      setIndexingState((current) => ({ ...current, [job.category]: 'indexing' }))
      setIndexingProgress((current) => ({ ...current, [job.category]: null }))

      const result = job.incremental
        ? await window.electronAPI.indexFolders({
            folders: [
              {
                id: job.id,
                path: job.path,
                category: job.category,
              },
            ],
            incremental: true,
            operationId: job.id,
          })
        : await window.electronAPI.reindexFolders({
            folders: [
              {
                id: job.id,
                path: job.path,
                category: job.category,
              },
            ],
            operationId: job.id,
          })

      if (!result.success) {
        setIndexingState((current) => ({ ...current, [job.category]: 'error' }))
        throw new Error(result.error || `Indexing failed for ${job.category}.`)
      }

      setIndexingState((current) => ({ ...current, [job.category]: 'complete' }))
      await loadAssetsForCategory(job.category)
      await checkDatabaseStatus()

      return result
    },
    [bootstrapStatus.status, checkDatabaseStatus, loadAssetsForCategory, storageReady]
  )

  const runIndexing = useCallback(
    async (jobs: IndexJob[]) => {
      if (jobs.length === 0) {
        return
      }

      const results = await Promise.allSettled(jobs.map((job) => runIndexJob(job)))
      const failures = results.filter((result) => result.status === 'rejected')
      if (failures.length > 0) {
        throw new Error(
          failures
            .map((result) => (result.status === 'rejected' ? String(result.reason) : ''))
            .filter(Boolean)
            .join('; ')
        )
      }
    },
    [runIndexJob]
  )

  const handleSelectFolder = useCallback(
    async (category: Category) => {
      const selection = await window.electronAPI.selectFolder()
      if (selection.error) {
        throw new Error(selection.error)
      }

      if (selection.canceled || !selection.filePath) {
        return
      }

      const nextFolders = setFolderPath(configState.media_folders, category, selection.filePath)
      const persistedFolders = await persistFolders(nextFolders)

      await runIndexing([
        {
          id: `${category}-manual-${Date.now()}`,
          path: getFolderPath(persistedFolders, category) || selection.filePath,
          category,
          incremental: true,
          source: 'manual',
        },
      ])
    },
    [configState.media_folders, persistFolders, runIndexing]
  )

  const handleRemoveFolder = useCallback(
    async (category: Category) => {
      const nextFolders = setFolderPath(configState.media_folders, category, null)
      await persistFolders(nextFolders)
      updateCategoryAssets(category, [])
      setIndexingState((current) => ({ ...current, [category]: 'idle' }))
      setIndexingProgress((current) => ({ ...current, [category]: null }))
      const purgeResult = await window.electronAPI.purgeCategoryAssets(category)
      if (!purgeResult.success) {
        throw new Error(purgeResult.error || `Failed to purge ${category} assets.`)
      }
      await checkDatabaseStatus()
    },
    [checkDatabaseStatus, configState.media_folders, persistFolders, updateCategoryAssets]
  )

  const handleReindexCategory = useCallback(
    async (category: Category) => {
      const folderPath = getFolderPath(configState.media_folders, category)
      if (!folderPath) {
        return
      }

      await runIndexing(
        [
          {
            id: `${category}-manual-${Date.now()}`,
            path: folderPath,
            category,
            incremental: false,
            source: 'manual',
          },
        ]
      )
    },
    [configState.media_folders, runIndexing]
  )

  useEffect(() => {
    const handleProgress = (_event: unknown, data: IndexProgressData) => {
      setIndexingProgress((current) => ({
        ...current,
        [data.category]: data,
      }))
      if (data.phase !== 'complete') {
        setIndexingState((current) => ({ ...current, [data.category]: 'indexing' }))
      }
    }

    window.electronAPI.onIndexProgress(handleProgress)
    return () => {
      window.electronAPI.removeIndexProgressListener(handleProgress)
    }
  }, [])

  useEffect(() => {
    if (!storageReady) {
      setDatabaseStatus({ connected: false, totalCount: 0 })
      return
    }

    void checkDatabaseStatus()
    void Promise.all((['music', 'sfx', 'vfx'] as Category[]).map(loadAssetsForCategory))
  }, [checkDatabaseStatus, configState.media_folders, loadAssetsForCategory, storageReady])

  useEffect(() => {
    if (!startupIndexRun || !storageReady) {
      return
    }

    if (processedStartupIndexRun.current === startupIndexRun.id) {
      return
    }

    processedStartupIndexRun.current = startupIndexRun.id
    onStartupIndexProcessed(startupIndexRun.signature)
    void runIndexing(startupIndexRun.jobs).catch((error) => {
      console.error('[MediaBrowser] Startup indexing failed:', error)
    })
  }, [onStartupIndexProcessed, runIndexing, startupIndexRun, storageReady])

  const activeStoreCategories = useMemo(
    () =>
      (['music', 'sfx', 'vfx'] as Category[]).filter(
        (category) => indexingProgress[category]?.databaseWriting === true
      ),
    [indexingProgress]
  )

  const currentAssets = useMemo(() => {
    const baseAssets = assetsByCategory[activeCategory]
    const normalizedSearch = searchQuery.trim().toLowerCase()

    return baseAssets.filter((asset) => {
      if (activeFilter === 'used' && !asset.used) {
        return false
      }

      if (activeFilter === 'unused' && asset.used) {
        return false
      }

      if (activeFilter === 'favorites') {
        return false
      }

      if (!normalizedSearch) {
        return true
      }

      return (
        asset.name.toLowerCase().includes(normalizedSearch) ||
        asset.tags.some((tag) => tag.toLowerCase().includes(normalizedSearch))
      )
    })
  }, [activeCategory, activeFilter, assetsByCategory, searchQuery])

  return (
    <TooltipProvider>
      <div className="flex h-full flex-col">
        <div className="border-b border-border p-3">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              className="pl-9"
              placeholder="Search indexed assets..."
              value={searchQuery}
              onChange={(event) => setSearchQuery(event.target.value)}
            />
          </div>
        </div>

        <div className="flex items-center justify-between border-b border-border bg-muted/30 px-3 py-2">
          <div className="flex items-center gap-2">
            <Database className="h-3.5 w-3.5 text-muted-foreground" />
            <span className="text-xs text-muted-foreground">
              {storageReady
                ? databaseStatus.connected
                  ? `SpacetimeDB ready (${databaseStatus.totalCount} indexed assets)`
                  : 'SpacetimeDB connected but database status is unavailable.'
                : storageHealth.message}
            </span>
            {activeStoreCategories.length > 0 && (
              <Badge variant="secondary" className="ml-1 text-[10px] uppercase tracking-wide">
                Writing to SpacetimeDB
                {activeStoreCategories.length > 1 ? ` (${activeStoreCategories.length})` : ''}
              </Badge>
            )}
          </div>
          <Button
            variant="ghost"
            size="sm"
            className="h-7 text-xs"
            onClick={() => {
              void checkDatabaseStatus()
            }}
            disabled={!storageReady}
          >
            <RefreshCw className="mr-1 h-3 w-3" />
            Refresh
          </Button>
        </div>

        <Tabs
          value={activeCategory}
          className="flex flex-1 flex-col"
          onValueChange={(value) => setActiveCategory(value as Category)}
        >
          <TabsList className="grid h-10 w-full grid-cols-3 rounded-none border-b border-border bg-transparent p-0">
            {(['music', 'sfx', 'vfx'] as Category[]).map((category) => {
              const Icon = CATEGORY_ICONS[category]
              return (
                <TabsTrigger
                  key={category}
                  value={category}
                  className="rounded-none data-[state=active]:border-b-2 data-[state=active]:border-primary data-[state=active]:bg-background"
                >
                  <Icon className="mr-1 h-4 w-4" />
                  {category === 'sfx' ? 'SFX' : CATEGORY_LABELS[category]}
                  {indexingState[category] === 'indexing' && (
                    <span
                      className={`ml-2 h-2 w-2 rounded-full ${
                        indexingProgress[category]?.databaseWriting ? 'bg-sky-500' : 'bg-primary animate-pulse'
                      }`}
                    />
                  )}
                </TabsTrigger>
              )
            })}
          </TabsList>

          {(['music', 'sfx', 'vfx'] as Category[]).map((category) => (
            <TabsContent key={category} value={category} className="m-0 flex-1">
              <AssetList
                category={category}
                assets={category === activeCategory ? currentAssets : assetsByCategory[category]}
                folderPath={getFolderPath(configState.media_folders, category)}
                indexingState={indexingState[category]}
                indexingProgress={indexingProgress[category]}
                onManageMedia={() => {
                  setSelectedManageTab(category)
                  setIsManageModalOpen(true)
                }}
              />
            </TabsContent>
          ))}
        </Tabs>

        <div className="border-t border-border p-2">
          <div className="flex gap-1">
            {filters.map((filter) => (
              <Tooltip key={filter.id}>
                <TooltipTrigger asChild>
                  <Button
                    variant={activeFilter === filter.id ? 'secondary' : 'ghost'}
                    size="sm"
                    className="flex-1"
                    onClick={() => setActiveFilter(filter.id)}
                  >
                    <filter.icon className="mr-1 h-3 w-3" />
                    {filter.label}
                  </Button>
                </TooltipTrigger>
                <TooltipContent>
                  <p>Show {filter.label.toLowerCase()} assets</p>
                </TooltipContent>
              </Tooltip>
            ))}
          </div>
        </div>
      </div>

      <Dialog open={isManageModalOpen} onOpenChange={setIsManageModalOpen}>
        <DialogContent className="max-w-xl">
          <DialogHeader>
            <DialogTitle>Manage Media Folders</DialogTitle>
            <DialogDescription>
              RoughCut stores one persistent folder per category and indexes it into the local
              SpacetimeDB.
            </DialogDescription>
          </DialogHeader>

          <Tabs value={selectedManageTab} onValueChange={(value) => setSelectedManageTab(value as Category)}>
            <TabsList className="grid w-full grid-cols-3">
              {(['music', 'sfx', 'vfx'] as Category[]).map((category) => {
                const Icon = CATEGORY_ICONS[category]
                return (
                  <TabsTrigger key={category} value={category}>
                    <Icon className="mr-1 h-4 w-4" />
                    {category === 'sfx' ? 'SFX' : CATEGORY_LABELS[category]}
                  </TabsTrigger>
                )
              })}
            </TabsList>

            {(['music', 'sfx', 'vfx'] as Category[]).map((category) => {
              const Icon = CATEGORY_ICONS[category]
              const folderPath = getFolderPath(configState.media_folders, category)
              const isBusy = indexingState[category] === 'indexing'
              const progress = indexingProgress[category]

              return (
                <TabsContent key={category} value={category} className="mt-4">
                  <div className="space-y-4">
                    <div className="rounded-xl border border-border/60 bg-muted/30 p-4">
                      <div className="flex items-start gap-3">
                        <div className="rounded-lg bg-background p-2">
                          <Icon className="h-4 w-4" />
                        </div>
                        <div className="min-w-0 flex-1">
                          <p className="text-sm font-medium">{CATEGORY_LABELS[category]}</p>
                          {folderPath ? (
                            <>
                              <p className="mt-2 text-sm">{folderPath.split(/[/\\]/).pop()}</p>
                              <p className="mt-1 break-all text-xs text-muted-foreground">
                                {folderPath}
                              </p>
                            </>
                          ) : (
                            <p className="mt-2 text-sm text-muted-foreground">
                              No folder configured yet.
                            </p>
                          )}
                        </div>
                      </div>
                      {progress && (
                        <p className="mt-3 text-xs text-muted-foreground">
                          {progress.message} ({progress.current}/{progress.total || '?'})
                        </p>
                      )}
                    </div>

                    <div className="flex flex-wrap gap-2">
                      <Button
                        onClick={() => {
                          void handleSelectFolder(category).catch((error) => {
                            console.error('[MediaBrowser] Failed to select folder:', error)
                          })
                        }}
                        disabled={!storageReady || isBusy}
                      >
                        <Plus className="mr-2 h-4 w-4" />
                        {folderPath ? 'Replace Folder' : 'Choose Folder'}
                      </Button>
                      <Button
                        variant="outline"
                        onClick={() => {
                          void handleReindexCategory(category).catch((error) => {
                            console.error('[MediaBrowser] Reindex failed:', error)
                          })
                        }}
                        disabled={!folderPath || !storageReady || isBusy}
                      >
                        <RefreshCw className="mr-2 h-4 w-4" />
                        Reindex
                      </Button>
                      <Button
                        variant="ghost"
                        onClick={() => {
                          void handleRemoveFolder(category).catch((error) => {
                            console.error('[MediaBrowser] Failed to remove folder:', error)
                          })
                        }}
                        disabled={!folderPath || isBusy}
                      >
                        <X className="mr-2 h-4 w-4" />
                        Remove
                      </Button>
                    </div>
                  </div>
                </TabsContent>
              )
            })}
          </Tabs>
        </DialogContent>
      </Dialog>
    </TooltipProvider>
  )
}

interface AssetListProps {
  category: Category
  assets: BrowserAsset[]
  folderPath: string | null
  indexingState: IndexingState
  indexingProgress: IndexProgressData | null
  onManageMedia: () => void
}

function AssetList({
  category,
  assets,
  folderPath,
  indexingState,
  indexingProgress,
  onManageMedia,
}: AssetListProps) {
  const Icon = CATEGORY_ICONS[category]
  const label = CATEGORY_LABELS[category]

  if (!folderPath) {
    return (
      <div className="flex h-full flex-col items-center justify-center p-6 text-center">
        <Icon className="mb-4 h-12 w-12 text-muted-foreground/60" />
        <h3 className="text-sm font-medium">No {label} Library</h3>
        <p className="mt-2 text-xs text-muted-foreground">
          Choose a {label.toLowerCase()} folder to start indexing this category.
        </p>
        <Button onClick={onManageMedia} size="sm" className="mt-4">
          <FolderOpen className="mr-2 h-4 w-4" />
          Manage Media
        </Button>
      </div>
    )
  }

  if (indexingState === 'indexing' && assets.length === 0) {
    return (
      <div className="flex h-full flex-col items-center justify-center p-6 text-center">
        <Loader2 className="mb-4 h-8 w-8 animate-spin text-primary" />
        <h3 className="text-sm font-medium">Indexing {label}...</h3>
        <p className="mt-2 text-xs text-muted-foreground">
          {indexingProgress?.message || 'Scanning the selected folder.'}
        </p>
      </div>
    )
  }

  if (assets.length === 0) {
    return (
      <div className="flex h-full flex-col items-center justify-center p-6 text-center">
        <Icon className="mb-4 h-12 w-12 text-muted-foreground/60" />
        <h3 className="text-sm font-medium">No Indexed Assets Yet</h3>
        <p className="mt-2 text-xs text-muted-foreground">
          RoughCut has a folder configured, but there are no indexed {label.toLowerCase()} assets
          to show yet.
        </p>
        <Button onClick={onManageMedia} variant="outline" size="sm" className="mt-4">
          Manage Media
        </Button>
      </div>
    )
  }

  return (
    <ScrollArea className="h-full">
      <div className="space-y-2 p-2">
        {indexingProgress && (
          <div className="rounded-md border border-border/60 bg-muted/40 p-3">
            <div className="flex items-center gap-2">
              {indexingProgress.databaseWriting ? (
                <Database className="h-4 w-4 text-sky-500" />
              ) : (
                <Loader2 className="h-4 w-4 animate-spin text-primary" />
              )}
              <p className="text-xs font-medium">
                {indexingProgress.databaseWriting ? 'Writing to SpacetimeDB' : 'Indexing in progress'}
              </p>
            </div>
            <p className="mt-2 text-xs text-muted-foreground">
              {indexingProgress.message} ({indexingProgress.current}/{indexingProgress.total || '?'})
            </p>
            {indexingProgress.databaseWriting && indexingProgress.batchTotal ? (
              <p className="mt-1 text-[11px] text-muted-foreground">
                Batch {indexingProgress.batchCurrent || 0}/{indexingProgress.batchTotal}
              </p>
            ) : null}
          </div>
        )}
        {assets.map((asset) => (
          <div
            key={asset.id}
            className="group flex items-center gap-3 rounded-md p-2 transition-colors hover:bg-accent"
          >
            <div className="flex h-10 w-10 items-center justify-center rounded bg-muted">
              <Icon className="h-5 w-5 text-muted-foreground" />
            </div>
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium">{asset.name}</p>
              {asset.tags.length > 0 && (
                <div className="mt-1 flex flex-wrap gap-1">
                  {asset.tags.slice(0, 4).map((tag) => (
                    <Badge key={tag} variant="outline" className="px-1 py-0 text-xs">
                      {tag}
                    </Badge>
                  ))}
                </div>
              )}
            </div>
            <span className="text-xs text-muted-foreground">{asset.duration}</span>
          </div>
        ))}
      </div>
    </ScrollArea>
  )
}
