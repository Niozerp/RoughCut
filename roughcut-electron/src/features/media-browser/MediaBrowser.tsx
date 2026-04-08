import { useState } from 'react'
import { Search, Music, Zap, Clapperboard, Filter, Heart, Clock, Star } from 'lucide-react'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip'

type FilterType = 'all' | 'used' | 'unused' | 'favorites'

export function MediaBrowser() {
  const [activeFilter, setActiveFilter] = useState<FilterType>('all')
  const [searchQuery, setSearchQuery] = useState('')

  const filters = [
    { id: 'all' as FilterType, label: 'All', icon: Filter },
    { id: 'used' as FilterType, label: 'Used', icon: Clock },
    { id: 'unused' as FilterType, label: 'Unused', icon: Star },
    { id: 'favorites' as FilterType, label: 'Favorites', icon: Heart },
  ]

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
            <AssetList category="Music" filter={activeFilter} />
          </TabsContent>
          <TabsContent value="sfx" className="flex-1 m-0">
            <AssetList category="SFX" filter={activeFilter} />
          </TabsContent>
          <TabsContent value="vfx" className="flex-1 m-0">
            <AssetList category="VFX" filter={activeFilter} />
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
    </TooltipProvider>
  )
}

interface AssetListProps {
  category: string
  filter: FilterType
}

function AssetList({ category, filter }: AssetListProps) {
  // Placeholder assets - in real implementation, these would come from the backend
  const placeholderAssets = [
    { id: 1, name: 'Corporate Upbeat', tags: ['Upbeat', 'Corporate'], duration: '2:34', used: true },
    { id: 2, name: 'Tension Building', tags: ['Tension', 'Dramatic'], duration: '1:45', used: false },
    { id: 3, name: 'Emotional Piano', tags: ['Emotional', 'Soft'], duration: '3:12', used: false },
    { id: 4, name: 'Action Chase', tags: ['Fast', 'Intense'], duration: '1:23', used: true },
    { id: 5, name: 'Peaceful Morning', tags: ['Calm', 'Ambient'], duration: '4:05', used: false },
  ]

  return (
    <ScrollArea className="h-full">
      <div className="p-2 space-y-2">
        {placeholderAssets.map((asset) => (
          <div
            key={asset.id}
            className="group flex items-center gap-3 p-2 rounded-md hover:bg-accent cursor-pointer transition-colors"
          >
            <div className="h-10 w-10 rounded bg-muted flex items-center justify-center">
              <Music className="h-5 w-5 text-muted-foreground" />
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
