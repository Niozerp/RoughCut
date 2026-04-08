import { useState } from 'react'
import { Smartphone, Monitor, Square, Film, Wand2 } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Skeleton } from '@/components/ui/skeleton'

interface Template {
  id: string
  name: string
  aspectRatio: string
  resolution: string
  duration: string
  icon: React.ElementType
  description: string
  segments: { name: string; duration: string }[]
}

const templates: Template[] = [
  {
    id: '9-16-social',
    name: '9:16 Social Vertical',
    aspectRatio: '9:16',
    resolution: '1080x1920',
    duration: '0:15-0:60',
    icon: Smartphone,
    description: 'Optimized for TikTok, Reels, and Shorts',
    segments: [
      { name: 'Hook', duration: '0:03' },
      { name: 'Content', duration: '0:10' },
      { name: 'CTA', duration: '0:05' },
    ],
  },
  {
    id: '16-9-story',
    name: '16:9 Story Cut',
    aspectRatio: '16:9',
    resolution: '1920x1080',
    duration: '2:00-5:00',
    icon: Monitor,
    description: 'Traditional YouTube and broadcast format',
    segments: [
      { name: 'Intro', duration: '0:15' },
      { name: 'Setup', duration: '0:30' },
      { name: 'Main Content', duration: '2:00' },
      { name: 'Outro', duration: '0:15' },
    ],
  },
  {
    id: '1-1-highlight',
    name: '1:1 Highlight',
    aspectRatio: '1:1',
    resolution: '1080x1080',
    duration: '0:30-2:00',
    icon: Square,
    description: 'Instagram feed and social posts',
    segments: [
      { name: 'Attention Grabber', duration: '0:05' },
      { name: 'Best Moments', duration: '0:45' },
      { name: 'Branding', duration: '0:10' },
    ],
  },
]

export function FormatTemplates() {
  const [selectedTemplate, setSelectedTemplate] = useState<string>('16-9-story')
  const [isGenerating, setIsGenerating] = useState(false)

  const selectedTemplateData = templates.find((t) => t.id === selectedTemplate)

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="p-3 border-b border-border">
        <h2 className="text-sm font-semibold flex items-center gap-2">
          <Film className="h-4 w-4 text-primary" />
          Format Templates
        </h2>
      </div>

      {/* Template List */}
      <ScrollArea className="flex-1">
        <div className="p-2 space-y-2">
          {templates.map((template) => (
            <Card
              key={template.id}
              className={`cursor-pointer transition-all ${
                selectedTemplate === template.id
                  ? 'border-primary ring-1 ring-primary'
                  : 'hover:border-primary/50'
              }`}
              onClick={() => setSelectedTemplate(template.id)}
            >
              <CardHeader className="p-3 pb-2">
                <div className="flex items-start gap-3">
                  <div className="h-10 w-10 rounded bg-primary/10 flex items-center justify-center">
                    <template.icon className="h-5 w-5 text-primary" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <CardTitle className="text-sm">{template.name}</CardTitle>
                    <CardDescription className="text-xs line-clamp-1">
                      {template.description}
                    </CardDescription>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="p-3 pt-0">
                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                  <Badge variant="outline" className="text-xs">
                    {template.aspectRatio}
                  </Badge>
                  <span>{template.resolution}</span>
                  <span>•</span>
                  <span>{template.duration}</span>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </ScrollArea>

      {/* Selected Template Details */}
      {selectedTemplateData && (
        <div className="border-t border-border p-3 bg-card/50">
          <h3 className="text-xs font-semibold uppercase text-muted-foreground mb-2">
            Template Structure
          </h3>
          <div className="space-y-1 mb-3">
            {selectedTemplateData.segments.map((segment, index) => (
              <div
                key={index}
                className="flex items-center justify-between text-sm py-1"
              >
                <span className="text-muted-foreground">{segment.name}</span>
                <span className="text-xs font-mono">{segment.duration}</span>
              </div>
            ))}
          </div>

          {/* Generate Button */}
          <Button
            className="w-full"
            size="lg"
            disabled={isGenerating}
            onClick={() => setIsGenerating(true)}
          >
            {isGenerating ? (
              <>
                <Skeleton className="h-4 w-4 mr-2 rounded-full" />
                Generating...
              </>
            ) : (
              <>
                <Wand2 className="h-4 w-4 mr-2" />
                Generate Rough Cut
              </>
            )}
          </Button>
        </div>
      )}
    </div>
  )
}
