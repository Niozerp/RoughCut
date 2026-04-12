import { useMemo, useState } from 'react'
import { Clapperboard, FolderOpen, Music, Sparkles, X, Zap } from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import type { Category, MediaFolders, OnboardingState } from '@/lib/roughcut-types'

interface OnboardingWizardProps {
  initialFolders: MediaFolders
  onboardingState: OnboardingState
  allowClose?: boolean
  isCompleting?: boolean
  completionError?: string | null
  onClose?: () => void
  onComplete: (folders: MediaFolders) => Promise<void> | void
}

const STEPS: Array<{
  category: Category
  label: string
  description: string
  icon: typeof Music
}> = [
  {
    category: 'music',
    label: 'Music',
    description: 'Choose the folder where RoughCut should index music cues.',
    icon: Music,
  },
  {
    category: 'sfx',
    label: 'Sound Effects',
    description: 'Choose the folder for one-shot effects, transitions, and impacts.',
    icon: Zap,
  },
  {
    category: 'vfx',
    label: 'Visual Effects',
    description: 'Choose the folder for motion graphics, overlays, and VFX assets.',
    icon: Clapperboard,
  },
]

function getFolderValue(folders: MediaFolders, category: Category) {
  return folders[`${category}_folder` as keyof MediaFolders]
}

function setFolderValue(folders: MediaFolders, category: Category, value: string | null): MediaFolders {
  return {
    ...folders,
    [`${category}_folder`]: value,
  } as MediaFolders
}

export function OnboardingWizard({
  initialFolders,
  onboardingState,
  allowClose = false,
  isCompleting = false,
  completionError,
  onClose,
  onComplete,
}: OnboardingWizardProps) {
  const [draftFolders, setDraftFolders] = useState<MediaFolders>(initialFolders)
  const [currentStep, setCurrentStep] = useState(0)
  const [selectionError, setSelectionError] = useState<string | null>(null)

  const step = STEPS[currentStep]
  const selectedPath = getFolderValue(draftFolders, step.category)
  const stepError = onboardingState.invalid_folders[step.category]
  const configuredCount = useMemo(
    () => Object.values(draftFolders).filter(Boolean).length,
    [draftFolders]
  )

  const handlePickFolder = async () => {
    setSelectionError(null)
    const result = await window.electronAPI.selectFolder()
    if (result.error) {
      setSelectionError(result.error)
      return
    }

    if (result.canceled || !result.filePath) {
      return
    }

    setDraftFolders((current) => setFolderValue(current, step.category, result.filePath))
  }

  const handleSkip = () => {
    setSelectionError(null)
    const nextFolders = setFolderValue(draftFolders, step.category, null)
    setDraftFolders(nextFolders)

    if (currentStep === STEPS.length - 1) {
      void onComplete(nextFolders)
      return
    }

    setCurrentStep((value) => value + 1)
  }

  const handleNext = () => {
    if (currentStep === STEPS.length - 1) {
      void onComplete(draftFolders)
      return
    }

    setCurrentStep((value) => value + 1)
  }

  const StepIcon = step.icon

  return (
    <div className="flex min-h-screen items-center justify-center bg-[radial-gradient(circle_at_top,_rgba(236,201,75,0.22),_transparent_38%),linear-gradient(135deg,_hsl(var(--background))_0%,_hsl(var(--card))_100%)] p-6">
      <Card className="w-full max-w-4xl border-border/60 bg-card/95 shadow-2xl">
        <CardHeader className="border-b border-border/50 pb-6">
          <div className="flex items-start justify-between gap-4">
            <div className="space-y-2">
              <Badge variant="outline" className="uppercase tracking-[0.2em]">
                First Launch
              </Badge>
              <CardTitle className="text-3xl">Choose Your Media Libraries</CardTitle>
              <CardDescription className="max-w-2xl text-sm leading-6">
                RoughCut indexes one source folder for each media category. You can skip any
                category for now and finish setup later from the main workspace.
              </CardDescription>
              {onboardingState.has_invalid_folders && (
                <p className="max-w-2xl text-sm text-amber-600">
                  Some previously selected media folders are no longer available. Choose new
                  folders for the affected categories before continuing.
                </p>
              )}
            </div>
            {allowClose && onClose && (
              <Button variant="ghost" size="icon" onClick={onClose}>
                <X className="h-4 w-4" />
              </Button>
            )}
          </div>
          <div className="mt-6 grid gap-3 md:grid-cols-3">
            {STEPS.map((item, index) => {
              const Icon = item.icon
              const isActive = index === currentStep
              const hasFolder = Boolean(getFolderValue(draftFolders, item.category))

              return (
                <div
                  key={item.category}
                  className={`rounded-xl border p-4 transition-colors ${
                    isActive
                      ? 'border-primary bg-primary/10'
                      : 'border-border/60 bg-background/50'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className="rounded-lg bg-background p-2">
                        <Icon className="h-4 w-4" />
                      </div>
                      <div>
                        <p className="text-sm font-medium">{item.label}</p>
                        <p className="text-xs text-muted-foreground">Step {index + 1}</p>
                      </div>
                    </div>
                    {hasFolder ? (
                      <Badge>Selected</Badge>
                    ) : (
                      <Badge variant="outline">Skipped</Badge>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        </CardHeader>

        <CardContent className="grid gap-6 p-6 md:grid-cols-[1.35fr_0.9fr]">
          <section className="rounded-2xl border border-border/60 bg-background/70 p-6">
            <div className="flex items-center gap-3">
              <div className="rounded-2xl bg-primary/10 p-3">
                <StepIcon className="h-6 w-6 text-primary" />
              </div>
              <div>
                <p className="text-xs uppercase tracking-[0.3em] text-muted-foreground">
                  Current Category
                </p>
                <h2 className="text-2xl font-semibold">{step.label}</h2>
              </div>
            </div>

            <p className="mt-4 max-w-xl text-sm leading-6 text-muted-foreground">
              {step.description}
            </p>

            <div className="mt-8 rounded-2xl border border-dashed border-border/70 bg-card/60 p-5">
              <p className="text-xs uppercase tracking-[0.3em] text-muted-foreground">
                Selected Folder
              </p>
              {selectedPath ? (
                <div className="mt-3 space-y-2">
                  <p className="text-sm font-medium">{selectedPath.split(/[/\\]/).pop()}</p>
                  <p className="break-all text-xs text-muted-foreground">{selectedPath}</p>
                </div>
              ) : (
                <p className="mt-3 text-sm text-muted-foreground">
                  Nothing selected yet. Use the folder picker or skip this category for now.
                </p>
              )}
            </div>

            {selectionError && (
              <p className="mt-4 text-sm text-destructive">{selectionError}</p>
            )}
            {stepError && (
              <p className="mt-4 text-sm text-amber-600">{stepError}</p>
            )}
            {completionError && (
              <p className="mt-4 text-sm text-destructive">{completionError}</p>
            )}

            <div className="mt-8 flex flex-wrap gap-3">
              <Button onClick={handlePickFolder} disabled={isCompleting}>
                <FolderOpen className="mr-2 h-4 w-4" />
                {selectedPath ? 'Replace Folder' : 'Choose Folder'}
              </Button>
              <Button variant="outline" onClick={handleSkip} disabled={isCompleting}>
                Skip for Now
              </Button>
              {selectedPath && (
                <Button
                  variant="ghost"
                  onClick={() => setDraftFolders((current) => setFolderValue(current, step.category, null))}
                  disabled={isCompleting}
                >
                  Clear
                </Button>
              )}
            </div>
          </section>

          <section className="flex flex-col justify-between rounded-2xl border border-border/60 bg-card/70 p-6">
            <div>
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Sparkles className="h-4 w-4 text-primary" />
                <span>Setup summary</span>
              </div>
              <p className="mt-4 text-4xl font-semibold">{configuredCount}/3</p>
              <p className="mt-2 text-sm text-muted-foreground">
                categories selected so far
              </p>

              <div className="mt-8 space-y-3">
                {STEPS.map((item) => {
                  const pathValue = getFolderValue(draftFolders, item.category)
                  return (
                    <div
                      key={item.category}
                      className="rounded-xl border border-border/60 bg-background/60 p-4"
                    >
                      <div className="flex items-center justify-between gap-3">
                        <span className="text-sm font-medium">{item.label}</span>
                        <Badge variant={pathValue ? 'default' : 'outline'}>
                          {pathValue ? 'Ready' : 'Skipped'}
                        </Badge>
                      </div>
                      <p className="mt-2 break-all text-xs text-muted-foreground">
                        {pathValue || 'No folder selected yet'}
                      </p>
                      {onboardingState.invalid_folders[item.category] && (
                        <p className="mt-2 text-xs text-amber-600">
                          {onboardingState.invalid_folders[item.category]}
                        </p>
                      )}
                    </div>
                  )
                })}
              </div>
            </div>

            <div className="mt-8 flex flex-wrap gap-3">
              <Button
                variant="outline"
                onClick={() => setCurrentStep((value) => Math.max(0, value - 1))}
                disabled={currentStep === 0 || isCompleting}
              >
                Back
              </Button>
              <Button onClick={handleNext} disabled={isCompleting}>
                {isCompleting
                  ? 'Finishing Setup...'
                  : currentStep === STEPS.length - 1
                    ? 'Finish Setup'
                    : 'Next Step'}
              </Button>
            </div>
          </section>
        </CardContent>
      </Card>
    </div>
  )
}
