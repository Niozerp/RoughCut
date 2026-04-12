import { Play, Scissors, SkipBack, SkipForward, Wand2 } from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { ScrollArea } from '@/components/ui/scroll-area'
import type { ResolveConnectionStatus } from '@/lib/roughcut-types'

interface TimelineWorkspaceProps {
  resolveStatus: ResolveConnectionStatus
  onConnectResolve: () => void
}

export function TimelineWorkspace({ resolveStatus, onConnectResolve }: TimelineWorkspaceProps) {
  const isConnected = resolveStatus.connected

  return (
    <div className="flex h-full flex-col">
      <div className="flex-1 p-4">
        <Card className="flex h-full flex-col">
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between gap-3">
              <CardTitle className="text-lg">Rough Cut Preview</CardTitle>
              {isConnected ? (
                <Badge variant="outline">Attached to DaVinci</Badge>
              ) : (
                <Badge variant="secondary">Standalone Preview</Badge>
              )}
            </div>
          </CardHeader>
          <CardContent className="flex flex-1 flex-col">
            <div className="flex min-h-[200px] flex-1 items-center justify-center rounded-md bg-black">
              <div className="text-center text-muted-foreground">
                <Play className="mx-auto mb-2 h-12 w-12 opacity-50" />
                <p className="text-sm">Timeline preview will appear here</p>
                <p className="mt-1 text-xs">
                  RoughCut stays usable without DaVinci, but timeline send requires an active attach.
                </p>
              </div>
            </div>

            <div className="mt-4 flex flex-wrap items-center justify-center gap-2">
              <Button variant="outline" size="icon">
                <SkipBack className="h-4 w-4" />
              </Button>
              <Button size="icon" className="h-10 w-10">
                <Play className="h-4 w-4" />
              </Button>
              <Button variant="outline" size="icon">
                <SkipForward className="h-4 w-4" />
              </Button>
              <div className="mx-2 h-6 w-px bg-border" />
              <Button variant="outline" size="icon">
                <Scissors className="h-4 w-4" />
              </Button>
              <Button
                variant={isConnected ? 'default' : 'outline'}
                disabled={isConnected}
                onClick={onConnectResolve}
              >
                {isConnected ? 'Ready to Push to DaVinci' : 'Connect to DaVinci'}
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="border-t border-border bg-card/30 p-4">
        <div className="mb-3 flex items-center justify-between">
          <h3 className="flex items-center gap-2 text-sm font-semibold">
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
    music: 'Music',
    sfx: 'SFX',
    vfx: 'VFX',
  }

  return (
    <div className="flex cursor-pointer items-center gap-3 rounded-md bg-card p-2 transition-colors hover:bg-accent">
      <Badge className={typeColors[type]}>{typeLabels[type]}</Badge>
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-medium">{name}</p>
        <p className="text-xs text-muted-foreground">{reason}</p>
      </div>
      <Badge variant="outline">{confidence}%</Badge>
      <Button size="sm" variant="ghost" className="h-7">
        Use
      </Button>
    </div>
  )
}
