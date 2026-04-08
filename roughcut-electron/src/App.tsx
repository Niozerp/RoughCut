import { useState, useEffect } from 'react'
import { Music, Film, Sparkles, Wand2, Settings, HelpCircle, Search, FolderOpen, FileVideo, Zap } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { MediaBrowser } from '@/features/media-browser/MediaBrowser'
import { TimelineWorkspace } from '@/features/timeline/TimelineWorkspace'
import { FormatTemplates } from '@/features/format-templates/FormatTemplates'
import {
  CommandDialog,
  CommandInput,
  CommandList,
  CommandEmpty,
  CommandGroup,
  CommandItem,
  CommandShortcut,
} from '@/components/ui/command'

type ResolveStatus = 'connected' | 'connecting' | 'disconnected'

function App() {
  const [resolveStatus] = useState<ResolveStatus>('connected')
  const [commandOpen, setCommandOpen] = useState(false)

  // ⌘K keyboard shortcut
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault()
        setCommandOpen((prev) => !prev)
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [])

  const getStatusColor = (status: ResolveStatus) => {
    switch (status) {
      case 'connected':
        return 'bg-resolve-connected'
      case 'connecting':
        return 'bg-resolve-connecting'
      case 'disconnected':
        return 'bg-resolve-disconnected'
    }
  }

  const getStatusText = (status: ResolveStatus) => {
    switch (status) {
      case 'connected':
        return 'Resolve Connected'
      case 'connecting':
        return 'Connecting...'
      case 'disconnected':
        return 'Resolve Disconnected'
    }
  }

  return (
    <div className="flex flex-col h-screen bg-background text-foreground overflow-hidden">
      {/* Header */}
      <header className="flex items-center justify-between px-4 h-12 border-b border-border bg-card/50">
        <div className="flex items-center gap-2">
          <Film className="h-5 w-5 text-primary" />
          <h1 className="text-lg font-semibold">RoughCut</h1>
        </div>

        <div className="flex items-center gap-4">
          {/* Resolve Status */}
          <div className="flex items-center gap-2 text-sm">
            <span className={`h-2 w-2 rounded-full ${getStatusColor(resolveStatus)}`} />
            <span className="text-muted-foreground">{getStatusText(resolveStatus)}</span>
          </div>

          {/* Search Button */}
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

      {/* Command Palette */}
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
            <CommandItem>
              <FolderOpen className="mr-2 h-4 w-4" />
              <span>Configure Media Folders</span>
            </CommandItem>
            <CommandItem>
              <FileVideo className="mr-2 h-4 w-4" />
              <span>Generate Rough Cut</span>
              <CommandShortcut>⌘G</CommandShortcut>
            </CommandItem>
            <CommandItem>
              <Wand2 className="mr-2 h-4 w-4" />
              <span>AI Asset Matching</span>
            </CommandItem>
          </CommandGroup>
          <CommandGroup heading="Settings">
            <CommandItem>
              <Settings className="mr-2 h-4 w-4" />
              <span>Open Settings</span>
              <CommandShortcut>⌘,</CommandShortcut>
            </CommandItem>
          </CommandGroup>
        </CommandList>
      </CommandDialog>

      {/* Main Content - Three Panel Layout */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left Panel - Media Browser */}
        <aside className="w-80 border-r border-border flex flex-col bg-card/30">
          <MediaBrowser />
        </aside>

        {/* Center Panel - Timeline Workspace */}
        <main className="flex-1 flex flex-col bg-background">
          <TimelineWorkspace />
        </main>

        {/* Right Panel - Format Templates */}
        <aside className="w-72 border-l border-border flex flex-col bg-card/30">
          <FormatTemplates />
        </aside>
      </div>
    </div>
  )
}

export default App
