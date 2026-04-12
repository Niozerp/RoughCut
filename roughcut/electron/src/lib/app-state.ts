import type {
  BootstrapStatus,
  Category,
  ConfigState,
  IndexJob,
  MediaFolders,
  OnboardingState,
  StartupIndexRun,
} from './roughcut-types'

export function shouldShowOnboarding(bootstrapStatus: BootstrapStatus, configState: ConfigState): boolean {
  return (
    bootstrapStatus.status === 'ready' &&
    (!configState.onboarding.completed || configState.onboarding.has_invalid_folders)
  )
}

export function needsSetupReminder(onboarding: OnboardingState): boolean {
  return onboarding.completed && onboarding.configured_count < 3 && !onboarding.has_invalid_folders
}

function buildFolderSignature(folders: IndexJob[]): string {
  return folders
    .map((folder) => `${folder.category}:${folder.path}`)
    .sort()
    .join('|')
}

export function buildStartupIndexRun(folders: MediaFolders, requestId: number): StartupIndexRun | null {
  const categories: Category[] = ['music', 'sfx', 'vfx']
  const configuredFolders: IndexJob[] = categories
    .map((category) => {
      const pathValue = folders[`${category}_folder` as keyof MediaFolders]
      if (!pathValue) {
        return null
      }

      return {
        id: `${category}-initial-${requestId}`,
        category,
        path: pathValue,
        incremental: true,
        source: 'startup' as const,
      }
    })
    .filter((folder): folder is NonNullable<typeof folder> => Boolean(folder))

  if (configuredFolders.length === 0) {
    return null
  }

  return {
    id: requestId,
    jobs: configuredFolders,
    signature: buildFolderSignature(configuredFolders),
  }
}
