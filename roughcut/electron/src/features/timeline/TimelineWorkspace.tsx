import { Play, SkipBack, SkipForward, Scissors, Wand2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { ScrollArea } from '@/components/ui/scroll-area'

export function TimelineWorkspace() {
  return (
    <div className="flex flex-col h-full">
      {/* Timeline Preview Area */}
      <div className="flex-1 p-4">
        <Card className="h-full flex flex-col">
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <CardTitle className="text-lg">Rough Cut Preview</CardTitle>
              <Badge variant="outline">AI Generated</Badge>
            </div>
          </CardHeader>
          <CardContent className="flex-1 flex flex-col">
            {/* Video Preview Placeholder */}
            <div className="flex-1 bg-black rounded-md flex items-center justify-center min-h-[200px]">
              <div className="text-center text-muted-foreground">
                <Play className="h-12 w-12 mx-auto mb-2 opacity-50" />
                <p className="text-sm">Timeline preview will appear here</p>
                <p className="text-xs mt-1">AI is analyzing your transcript...</p>
              </div>
            </div>

            {/* Playback Controls */}
            <div className="flex items-center justify-center gap-2 mt-4">
              <Button variant="outline" size="icon">
                <SkipBack className="h-4 w-4" />
              </Button>
              <Button size="icon" className="h-10 w-10">
                <Play className="h-4 w-4" />
              </Button>
              <Button variant="outline" size="icon">
                <SkipForward className="h-4 w-4" />
              </Button>
              <div className="w-px h-6 bg-border mx-2" />
              <Button variant="outline" size="icon">
                <Scissors className="h-4 w-4" />
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* AI Suggestions Panel */}
      <div className="border-t border-border p-4 bg-card/30">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-semibold flex items-center gap-2">
            <Wand2 className="h-4 w-4 text-secondary" />
            AI Asset Suggestions
          </h3>
          <Badge variant="secondary">6 suggestions</Badge>
        </div>

        <ScrollArea className="h-32">
          <div className="space-y-2">
            <SuggestionItem
              type="music"
              name="Corporate Upbeat"
              reason="Matches upbeat tone at 00:34"
              confidence={92}
            />
            <SuggestionItem
              type="sfx"
              name="Whoosh Impact"
              reason="Transition at 01:23"
              confidence={88}
            />
            <SuggestionItem
              type="vfx"
              name="Lower Third Title"
              reason="Speaker introduction"
              confidence={85}
            />
          </div>
        </ScrollArea>
      </div>
    </div>
  )
}

interface SuggestionItemProps {
  type: 'music' | 'sfx' | 'vfx'
  name: string
  reason: string
  confidence: number
}

function SuggestionItem({ type, name, reason, confidence }: SuggestionItemProps) {
  const typeColors = {
    music: 'bg-primary/20 text-primary',
    sfx: 'bg-secondary/20 text-secondary',
    vfx: 'bg-accent text-accent-foreground',
  }

  const typeLabels = {
    music: '🎵',
    sfx: '🔊',
    vfx: '🎬',
  }

  return (
    <div className="flex items-center gap-3 p-2 rounded-md bg-card hover:bg-accent cursor-pointer transition-colors">
      <span className="text-lg">{typeLabels[type]}</span>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium truncate">{name}</p>
        <p className="text-xs text-muted-foreground">{reason}</p>
      </div>
      <Badge className={typeColors[type]}>{confidence}%</Badge>
      <Button size="sm" variant="ghost" className="h-7">
        Use
      </Button>
    </div>
  )
}
