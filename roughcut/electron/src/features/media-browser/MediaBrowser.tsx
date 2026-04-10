import { useState, useEffect } from 'react'
import { Search, Music, Zap, Clapperboard, Filter, Heart, Clock, Star, FolderOpen, Plus, X, Loader2 } from 'lucide-react'
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

export function MediaBrowser() {
  const [activeFilter, setActiveFilter] = useState<FilterType>('all')
  const [searchQuery, setSearchQuery] = useState('')
  const [isManageModalOpen, setIsManageModalOpen] = useState(false)
  const [folders, setFolders] = useState<MediaFolder[]>([])
  const [assets, setAssets] = useState<Asset[]>([])
  const [indexingStatus, setIndexingStatus] = useState<{ [key: string]: 'idle' | 'indexing' | 'complete' | 'error' }>({})
  const [selectedManageTab, setSelectedManageTab] = useState<Category>('music')
  const [isElectronAvailable, setIsElectronAvailable] = useState(true)

  // Check if electronAPI is available on mount
  useEffect(() => {
    if (!window.electronAPI) {
      console.error('[MediaBrowser] window.electronAPI is not available on mount')
      setIsElectronAvailable(false)
    } else {
      console.log('[MediaBrowser] window.electronAPI is available:', Object.keys(window.electronAPI))
      setIsElectronAvailable(true)
    }
  }, [])

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
        console.error('[MediaBrowser] window.electronAPI is not available. Preload script may not be loaded.')
        console.error('[MediaBrowser] window keys:', Object.keys(window))
        alert('Error: Electron API not available. The preload script failed to load. Please check console for details and restart the application.')
        return
      }
      
      if (!window.electronAPI.selectFolder) {
        console.error('[MediaBrowser] window.electronAPI.selectFolder is not available')
        console.error('[MediaBrowser] Available electronAPI methods:', Object.keys(window.electronAPI))
        alert('Error: Folder selection not available. The API method is missing. Please restart the application.')
        return
      }
      
      console.log(`[MediaBrowser] Calling selectFolder for category: ${category}...`)
      const result = await window.electronAPI.selectFolder()
      console.log('[MediaBrowser] selectFolder result:', result)
      
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
      
      // Trigger indexing (mock for now)
      setIndexingStatus(prev => ({ ...prev, [newFolder.id]: 'indexing' }))
      
      // Simulate indexing delay
      setTimeout(() => {
        setIndexingStatus(prev => ({ ...prev, [newFolder.id]: 'complete' }))
        
        // Mock: Add some fake assets from this folder
        const mockAssets: Asset[] = [
          { id: `${newFolder.id}-1`, name: `Track from ${result.filePath.split('/').pop()}`, tags: ['Imported'], duration: '2:34', used: false, folderId: newFolder.id },
        ]
        setAssets(prev => [...prev, ...mockAssets])
      }, 1500)
      
    } catch (error) {
      console.error('[MediaBrowser] Failed to select folder:', error)
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

        {/* Electron API Warning */}
        {!isElectronAvailable && (
          <div className="p-2 bg-destructive/10 border-b border-destructive/20">
            <p className="text-xs text-destructive text-center">
              ⚠️ Electron API not available. Folder selection disabled.
            </p>
          </div>
        )}

        {/* Category Tabs */}
        <Tabs defaultValue="music" className="flex-1 flex flex-col">
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

                  <Button 
                    variant="outline" 
                    className="w-full"
                    onClick={() => handleSelectFolder(cat)}
                  >
                    <Plus className="h-4 w-4 mr-2" />
                    Add {categoryLabels[cat]} Folder
                  </Button>
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
