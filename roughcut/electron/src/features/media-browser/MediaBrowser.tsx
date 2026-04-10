import { useState, useEffect, useCallback } from 'react'
import { Search, Music, Zap, Clapperboard, Filter, Heart, Clock, Star, FolderOpen, Plus, X, Loader2, RefreshCw, Database } from 'lucide-react'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog'

type FilterType = 'all' | 'used' | 'unused' | 'favorites'
type Category = 'music' | 'sfx' | 'vfx'

interface MediaFolder {
  id: string
  path: string
  category: Category
}

interface Asset {
  id: string
  name: string
  tags: string[]
  duration: string
  used: boolean
  folderId: string
}

interface IndexProgress {
  operationId: string
  type: string
  operation: string
  current: number
  total: number
  message: string
}

export function MediaBrowser() {
  const [activeFilter, setActiveFilter] = useState<FilterType>('all')
  const [searchQuery, setSearchQuery] = useState('')
  const [isManageModalOpen, setIsManageModalOpen] = useState(false)
  const [folders, setFolders] = useState<MediaFolder[]>([])
  const [assets, setAssets] = useState<Asset[]>([])
  const [indexingStatus, setIndexingStatus] = useState<{ [key: string]: 'idle' | 'indexing' | 'complete' | 'error' }>({})
  const [indexingProgress, setIndexingProgress] = useState<{ [key: string]: IndexProgress }>({})
  const [selectedManageTab, setSelectedManageTab] = useState<Category>('music')
  const [isElectronAvailable, setIsElectronAvailable] = useState(true)
  const [databaseStatus, setDatabaseStatus] = useState<{ connected: boolean; totalCount: number } | null>(null)

  // Check if electronAPI is available on mount and load initial data
  useEffect(() => {
    if (!window.electronAPI) {
      console.error('[MediaBrowser] CRITICAL: window.electronAPI is not available on mount')
      setIsElectronAvailable(false)
      alert('CRITICAL ERROR: Electron API not available. Indexing will not work.')
    } else {
      const apiMethods = Object.keys(window.electronAPI)
      console.log('[MediaBrowser] window.electronAPI is available with methods:', apiMethods)
      
      // Check for required methods
      const requiredMethods = ['selectFolder', 'indexFolders', 'queryAssets', 'getDatabaseStatus']
      const missingMethods = requiredMethods.filter(m => !apiMethods.includes(m))
      
      if (missingMethods.length > 0) {
        console.error('[MediaBrowser] CRITICAL: Missing required API methods:', missingMethods)
        alert(`CRITICAL ERROR: Missing API methods: ${missingMethods.join(', ')}. Indexing will not work.`)
        setIsElectronAvailable(false)
      } else {
        setIsElectronAvailable(true)
      }
      
      // Set up progress listener
      const handleProgress = (_event: unknown, data: IndexProgress) => {
        console.log('[MediaBrowser] Index progress:', data)
        // Update progress for the operation
        setIndexingProgress(prev => ({
          ...prev,
          [data.operationId]: data
        }))
        
        // If this is a complete operation, refresh assets
        if (data.operation === 'complete') {
          loadAssetsForCategory(selectedManageTab)
        }
      }
      
      window.electronAPI.onIndexProgress(handleProgress)
      
      // Check database status
      checkDatabaseStatus()
      
      // Cleanup
      return () => {
        window.electronAPI.removeIndexProgressListener(handleProgress)
      }
    }
  }, [selectedManageTab])
  
  // Check database connection status
  const checkDatabaseStatus = useCallback(async () => {
    try {
      const status = await window.electronAPI.getDatabaseStatus()
      console.log('[MediaBrowser] Database status:', status)
      setDatabaseStatus({
        connected: status.connected,
        totalCount: status.total_count
      })
    } catch (error) {
      console.error('[MediaBrowser] Failed to check database status:', error)
      setDatabaseStatus({ connected: false, totalCount: 0 })
    }
  }, [])
  
  // Load assets for a category from SpacetimeDB
  const loadAssetsForCategory = useCallback(async (category: Category) => {
    try {
      console.log(`[MediaBrowser] Loading assets for ${category}...`)
      const result = await window.electronAPI.queryAssets({ category, limit: 1000 })
      
      if (result.success && result.assets) {
        const transformedAssets: Asset[] = result.assets.map(asset => ({
          id: asset.id,
          name: asset.file_name || asset.name || 'Unknown',
          tags: asset.ai_tags || asset.tags || [],
          duration: asset.duration || '0:00',
          used: asset.used || false,
          folderId: `folder-${category}`
        }))
        
        setAssets(prev => {
          // Remove old assets for this category
          const filtered = prev.filter(a => {
            const folder = folders.find(f => f.id === a.folderId)
            return folder?.category !== category
          })
          return [...filtered, ...transformedAssets]
        })
        
        console.log(`[MediaBrowser] Loaded ${transformedAssets.length} assets for ${category}`)
      }
    } catch (error) {
      console.error(`[MediaBrowser] Failed to load assets for ${category}:`, error)
    }
  }, [folders])

  const filters = [
    { id: 'all' as FilterType, label: 'All', icon: Filter },
    { id: 'used' as FilterType, label: 'Used', icon: Clock },
    { id: 'unused' as FilterType, label: 'Unused', icon: Star },
    { id: 'favorites' as FilterType, label: 'Favorites', icon: Heart },
  ]

  const handleSelectFolder = async (category: Category) => {
    try {
      // Debug: Check if electronAPI is available
      if (!window.electronAPI) {
        console.error('[MediaBrowser] CRITICAL: window.electronAPI is not available')
        console.error('[MediaBrowser] window keys:', Object.keys(window))
        alert('Error: Electron API not available. Please restart the application.')
        return
      }
      
      // Log all available methods
      console.log('[MediaBrowser] Available electronAPI methods:', Object.keys(window.electronAPI))
      
      if (!window.electronAPI.selectFolder) {
        console.error('[MediaBrowser] ERROR: window.electronAPI.selectFolder is not available')
        alert('Error: Folder selection not available. Please restart the application.')
        return
      }
      
      if (!window.electronAPI.indexFolders) {
        console.error('[MediaBrowser] ERROR: window.electronAPI.indexFolders is not available')
        alert('Error: Indexing API not available. Please restart the application.')
        return
      }
      
      console.log(`[MediaBrowser] Calling selectFolder for category: ${category}...`)
      const result = await window.electronAPI.selectFolder()
      console.log('[MediaBrowser] selectFolder result:', JSON.stringify(result))
      
      if (result.error) {
        console.error('[MediaBrowser] Folder selection error:', result.error)
        alert(`Error selecting folder: ${result.error}`)
        return
      }
      
      if (result.canceled || !result.filePath) {
        console.log('[MediaBrowser] Folder selection was canceled')
        return
      }

      // Check for duplicates
      const isDuplicate = folders.some(
        f => f.path === result.filePath && f.category === category
      )
      
      if (isDuplicate) {
        console.warn('[MediaBrowser] Folder already added:', result.filePath)
        return
      }

      const newFolder: MediaFolder = {
        id: `${category}-${Date.now()}`,
        path: result.filePath,
        category
      }

      setFolders(prev => [...prev, newFolder])
      
      // Trigger REAL indexing via Python backend
      setIndexingStatus(prev => ({ ...prev, [newFolder.id]: 'indexing' }))
      
      try {
        console.log('[MediaBrowser] ============================================')
        console.log('[MediaBrowser] STARTING REAL INDEXING')
        console.log('[MediaBrowser] Folder:', JSON.stringify(newFolder))
        console.log('[MediaBrowser] ============================================')
        
        // Call the real indexing API
        console.log('[MediaBrowser] Calling window.electronAPI.indexFolders...')
        const indexResult = await window.electronAPI.indexFolders({
          folders: [{
            id: newFolder.id,
            path: newFolder.path,
            category: newFolder.category
          }],
          incremental: true
        })
        
        console.log('[MediaBrowser] Indexing API returned:', JSON.stringify(indexResult))
        
        if (indexResult.success) {
          setIndexingStatus(prev => ({ ...prev, [newFolder.id]: 'complete' }))
          
          // Load real assets from database
          console.log('[MediaBrowser] Loading assets for category:', category)
          await loadAssetsForCategory(category)
          
          // Show success info
          const msg = `Indexed ${indexResult.indexed_count} assets in ${indexResult.duration_ms}ms`
          console.log('[MediaBrowser] SUCCESS:', msg)
          
          // Refresh database status
          await checkDatabaseStatus()
        } else {
          setIndexingStatus(prev => ({ ...prev, [newFolder.id]: 'error' }))
          console.error('[MediaBrowser] Indexing failed:', indexResult.error)
          alert(`Indexing failed: ${indexResult.error}`)
        }
      } catch (indexError: any) {
        setIndexingStatus(prev => ({ ...prev, [newFolder.id]: 'error' }))
        console.error('[MediaBrowser] ============================================')
        console.error('[MediaBrowser] INDEXING ERROR CAUGHT')
        console.error('[MediaBrowser] Error type:', typeof indexError)
        console.error('[MediaBrowser] Error message:', indexError?.message || 'No message')
        console.error('[MediaBrowser] Error object:', indexError)
        console.error('[MediaBrowser] Error stack:', indexError?.stack || 'No stack')
        console.error('[MediaBrowser] ============================================')
        alert(`Indexing error: ${indexError?.message || String(indexError)}`)
      }
      
    } catch (error) {
      console.error('[MediaBrowser] Failed to select folder:', error)
    }
  }
  
  // Handle reindexing all folders for a category
  const handleReindexCategory = async (category: Category) => {
    const categoryFolders = folders.filter(f => f.category === category)
    if (categoryFolders.length === 0) {
      console.log(`[MediaBrowser] No folders to reindex for ${category}`)
      return
    }
    
    try {
      // Mark all folders as indexing
      categoryFolders.forEach(folder => {
        setIndexingStatus(prev => ({ ...prev, [folder.id]: 'indexing' }))
      })
      
      console.log(`[MediaBrowser] Starting reindexing for ${category}...`)
      
      const result = await window.electronAPI.reindexFolders({
        folders: categoryFolders.map(f => ({
          id: f.id,
          path: f.path,
          category: f.category
        }))
      })
      
      console.log('[MediaBrowser] Reindexing result:', result)
      
      // Mark all folders as complete
      categoryFolders.forEach(folder => {
        setIndexingStatus(prev => ({ 
          ...prev, 
          [folder.id]: result.success ? 'complete' : 'error' 
        }))
      })
      
      if (result.success) {
        // Reload assets
        await loadAssetsForCategory(category)
        await checkDatabaseStatus()
        
        const msg = `Reindexed ${result.new_count} new, ${result.modified_count} modified, ${result.deleted_count} deleted`
        console.log('[MediaBrowser]', msg)
      } else {
        alert(`Reindexing failed: ${result.error}`)
      }
      
    } catch (error) {
      console.error('[MediaBrowser] Reindexing error:', error)
      categoryFolders.forEach(folder => {
        setIndexingStatus(prev => ({ ...prev, [folder.id]: 'error' }))
      })
      alert(`Reindexing error: ${error}`)
    }
  }

  const handleRemoveFolder = (folderId: string) => {
    setFolders(prev => prev.filter(f => f.id !== folderId))
    setAssets(prev => prev.filter(a => a.folderId !== folderId))
    setIndexingStatus(prev => {
      const newStatus = { ...prev }
      delete newStatus[folderId]
      return newStatus
    })
  }

  const getFoldersByCategory = (category: Category) => 
    folders.filter(f => f.category === category)

  const getAssetsByCategory = (category: Category) =>
    assets.filter(a => {
      const folder = folders.find(f => f.id === a.folderId)
      return folder?.category === category
    })

  const categoryIcons = {
    music: Music,
    sfx: Zap,
    vfx: Clapperboard
  }

  const categoryLabels = {
    music: 'Music',
    sfx: 'Sound Effects',
    vfx: 'Visual Effects'
  }
  
  // Load assets when active tab changes
  const handleTabChange = (value: string) => {
    const category = value as Category
    loadAssetsForCategory(category)
  }
  
  // Load initial assets on mount
  useEffect(() => {
    loadAssetsForCategory('music')
  }, [loadAssetsForCategory])

  return (
    <TooltipProvider>
      <div className="flex flex-col h-full">
        {/* Search Header */}
        <div className="p-3 border-b border-border">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search assets..."
              className="pl-9"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>
        </div>

        {/* Status Bar */}
        <div className="px-3 py-1 border-b border-border bg-muted/30 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Database className="h-3 w-3 text-muted-foreground" />
            <span className="text-xs text-muted-foreground">
              {databaseStatus?.connected 
                ? `DB Connected (${databaseStatus.totalCount} assets)` 
                : 'DB Disconnected'}
            </span>
          </div>
          {databaseStatus?.connected && (
            <Button 
              variant="ghost" 
              size="sm" 
              className="h-6 text-xs"
              onClick={checkDatabaseStatus}
            >
              <RefreshCw className="h-3 w-3 mr-1" />
              Refresh
            </Button>
          )}
        </div>

        {/* Electron API Warning */}
        {!isElectronAvailable && (
          <div className="p-2 bg-destructive/10 border-b border-destructive/20">
            <p className="text-xs text-destructive text-center">
              ⚠️ Electron API not available. Folder selection disabled.
            </p>
          </div>
        )}

        {/* Category Tabs */}
        <Tabs defaultValue="music" className="flex-1 flex flex-col" onValueChange={handleTabChange}>
          <TabsList className="grid w-full grid-cols-3 rounded-none border-b border-border bg-transparent p-0 h-10">
            <TabsTrigger 
              value="music" 
              className="rounded-none data-[state=active]:bg-background data-[state=active]:border-b-2 data-[state=active]:border-primary"
            >
              <Music className="h-4 w-4 mr-1" />
              Music
            </TabsTrigger>
            <TabsTrigger 
              value="sfx"
              className="rounded-none data-[state=active]:bg-background data-[state=active]:border-b-2 data-[state=active]:border-primary"
            >
              <Zap className="h-4 w-4 mr-1" />
              SFX
            </TabsTrigger>
            <TabsTrigger 
              value="vfx"
              className="rounded-none data-[state=active]:bg-background data-[state=active]:border-b-2 data-[state=active]:border-primary"
            >
              <Clapperboard className="h-4 w-4 mr-1" />
              VFX
            </TabsTrigger>
          </TabsList>

          <TabsContent value="music" className="flex-1 m-0">
            <AssetList 
              category="music" 
              filter={activeFilter}
              folders={getFoldersByCategory('music')}
              assets={getAssetsByCategory('music')}
              indexingStatus={indexingStatus}
              onManageMedia={() => {
                setSelectedManageTab('music')
                setIsManageModalOpen(true)
              }}
            />
          </TabsContent>
          <TabsContent value="sfx" className="flex-1 m-0">
            <AssetList 
              category="sfx" 
              filter={activeFilter}
              folders={getFoldersByCategory('sfx')}
              assets={getAssetsByCategory('sfx')}
              indexingStatus={indexingStatus}
              onManageMedia={() => {
                setSelectedManageTab('sfx')
                setIsManageModalOpen(true)
              }}
            />
          </TabsContent>
          <TabsContent value="vfx" className="flex-1 m-0">
            <AssetList 
              category="vfx" 
              filter={activeFilter}
              folders={getFoldersByCategory('vfx')}
              assets={getAssetsByCategory('vfx')}
              indexingStatus={indexingStatus}
              onManageMedia={() => {
                setSelectedManageTab('vfx')
                setIsManageModalOpen(true)
              }}
            />
          </TabsContent>
        </Tabs>

        {/* Filter Footer */}
        <div className="p-2 border-t border-border">
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
                    <filter.icon className="h-3 w-3 mr-1" />
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

      {/* Media Management Modal */}
      <Dialog open={isManageModalOpen} onOpenChange={setIsManageModalOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>Manage Media Folders</DialogTitle>
            <DialogDescription>
              Select folders to index for each media category
            </DialogDescription>
          </DialogHeader>

          <Tabs value={selectedManageTab} onValueChange={(v) => setSelectedManageTab(v as Category)}>
            <TabsList className="grid w-full grid-cols-3">
              <TabsTrigger value="music">
                <Music className="h-4 w-4 mr-1" />
                Music
              </TabsTrigger>
              <TabsTrigger value="sfx">
                <Zap className="h-4 w-4 mr-1" />
                SFX
              </TabsTrigger>
              <TabsTrigger value="vfx">
                <Clapperboard className="h-4 w-4 mr-1" />
                VFX
              </TabsTrigger>
            </TabsList>

            {(['music', 'sfx', 'vfx'] as Category[]).map((cat) => (
              <TabsContent key={cat} value={cat} className="mt-4">
                <div className="space-y-3">
                  {getFoldersByCategory(cat).length === 0 ? (
                    <div className="text-center py-8 text-muted-foreground">
                      <FolderOpen className="h-12 w-12 mx-auto mb-3 opacity-50" />
                      <p>No {categoryLabels[cat].toLowerCase()} folders configured</p>
                      <p className="text-sm mt-1">Add a folder to start indexing</p>
                    </div>
                  ) : (
                    <ScrollArea className="h-[200px]">
                      <div className="space-y-2">
                        {getFoldersByCategory(cat).map((folder) => (
                          <div 
                            key={folder.id} 
                            className="flex items-center justify-between p-2 rounded-md bg-muted"
                          >
                            <div className="flex-1 min-w-0 mr-2">
                              <p className="text-sm truncate" title={folder.path}>
                                {folder.path.split(/[/\\]/).pop()}
                              </p>
                              <p className="text-xs text-muted-foreground truncate">
                                {folder.path}
                              </p>
                            </div>
                            <div className="flex items-center gap-2">
                              {indexingStatus[folder.id] === 'indexing' && (
                                <Loader2 className="h-4 w-4 animate-spin text-primary" />
                              )}
                              {indexingStatus[folder.id] === 'complete' && (
                                <Badge variant="outline" className="text-xs">Indexed</Badge>
                              )}
                              <Button
                                variant="ghost"
                                size="icon"
                                className="h-7 w-7"
                                onClick={() => handleRemoveFolder(folder.id)}
                              >
                                <X className="h-4 w-4" />
                              </Button>
                            </div>
                          </div>
                        ))}
                      </div>
                    </ScrollArea>
                  )}

                  <div className="flex gap-2">
                    <Button 
                      variant="outline" 
                      className="flex-1"
                      onClick={() => handleSelectFolder(cat)}
                    >
                      <Plus className="h-4 w-4 mr-2" />
                      Add {categoryLabels[cat]} Folder
                    </Button>
                    
                    {getFoldersByCategory(cat).length > 0 && (
                      <Button 
                        variant="secondary"
                        size="icon"
                        onClick={() => handleReindexCategory(cat)}
                        title={`Reindex all ${categoryLabels[cat]} folders`}
                      >
                        <RefreshCw className="h-4 w-4" />
                      </Button>
                    )}
                  </div>
                </div>
              </TabsContent>
            ))}
          </Tabs>
        </DialogContent>
      </Dialog>
    </TooltipProvider>
  )
}

interface AssetListProps {
  category: Category
  filter: FilterType
  folders: MediaFolder[]
  assets: Asset[]
  indexingStatus: { [key: string]: 'idle' | 'indexing' | 'complete' | 'error' }
  onManageMedia: () => void
}

function AssetList({ category, filter, folders, assets, indexingStatus, onManageMedia }: AssetListProps) {
  const isIndexing = folders.some(f => indexingStatus[f.id] === 'indexing')
  
  const filteredAssets = assets.filter((asset) => {
    if (filter === 'used') return asset.used
    if (filter === 'unused') return !asset.used
    return true
  })

  const categoryIcons = {
    music: Music,
    sfx: Zap,
    vfx: Clapperboard
  }

  const categoryLabels = {
    music: 'Music',
    sfx: 'Sound Effects', 
    vfx: 'Visual Effects'
  }

  const Icon = categoryIcons[category]

  // Empty state - no folders configured
  if (folders.length === 0) {
    return (
      <div className="h-full flex flex-col items-center justify-center p-6 text-center">
        <Icon className="h-12 w-12 text-muted-foreground mb-4 opacity-50" />
        <h3 className="text-sm font-medium mb-2">
          No {categoryLabels[category]} Library
        </h3>
        <p className="text-xs text-muted-foreground mb-4">
          Configure folders to index your {categoryLabels[category].toLowerCase()} collection
        </p>
        <Button onClick={onManageMedia} size="sm">
          <FolderOpen className="h-4 w-4 mr-2" />
          Manage Media
        </Button>
      </div>
    )
  }

  // Loading state - indexing in progress
  if (isIndexing && assets.length === 0) {
    return (
      <div className="h-full flex flex-col items-center justify-center p-6 text-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary mb-4" />
        <h3 className="text-sm font-medium mb-2">Indexing {categoryLabels[category]}...</h3>
        <p className="text-xs text-muted-foreground">
          Scanning folders for media files
        </p>
      </div>
    )
  }

  // No assets found (after indexing)
  if (assets.length === 0) {
    return (
      <div className="h-full flex flex-col items-center justify-center p-6 text-center">
        <Icon className="h-12 w-12 text-muted-foreground mb-4 opacity-50" />
        <h3 className="text-sm font-medium mb-2">No Assets Found</h3>
        <p className="text-xs text-muted-foreground mb-4">
          Folders indexed but no {categoryLabels[category].toLowerCase()} files detected
        </p>
        <Button onClick={onManageMedia} variant="outline" size="sm">
          Manage Folders
        </Button>
      </div>
    )
  }

  // Assets list
  return (
    <ScrollArea className="h-full">
      <div className="p-2 space-y-2">
        {filteredAssets.map((asset) => (
          <div
            key={asset.id}
            className="group flex items-center gap-3 p-2 rounded-md hover:bg-accent cursor-pointer transition-colors"
          >
            <div className="h-10 w-10 rounded bg-muted flex items-center justify-center">
              <Icon className="h-5 w-5 text-muted-foreground" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium truncate">{asset.name}</p>
              <div className="flex items-center gap-2 mt-1">
                {asset.tags.map((tag) => (
                  <Badge key={tag} variant="outline" className="text-xs px-1 py-0">
                    {tag}
                  </Badge>
                ))}
              </div>
            </div>
            <span className="text-xs text-muted-foreground">{asset.duration}</span>
          </div>
        ))}
      </div>
    </ScrollArea>
  )
}
