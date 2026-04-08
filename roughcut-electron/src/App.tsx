import { useState } from 'react'
import { Music, Film, Sparkles, Wand2, Settings, HelpCircle } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { MediaBrowser } from '@/features/media-browser/MediaBrowser'
import { TimelineWorkspace } from '@/features/timeline/TimelineWorkspace'
import { FormatTemplates } from '@/features/format-templates/FormatTemplates'

type ResolveStatus = 'connected' | 'connecting' | 'disconnected'

function App() {
  const [resolveStatus, setResolveStatus] = useState<ResolveStatus>('connected')

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
