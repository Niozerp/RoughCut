import type { BootstrapStatus } from './spacetimeManager.js'

export interface AppBootstrapDependencies {
  createWindow: () => void
  ensureReady: () => Promise<BootstrapStatus>
  logFailure: (message: string) => void
  quit: () => void
}

export async function bootstrapAndCreateWindow(
  dependencies: AppBootstrapDependencies
): Promise<boolean> {
  try {
    const status = await dependencies.ensureReady()
    if (status.status !== 'ready') {
      dependencies.logFailure(status.error || status.message)
      dependencies.quit()
      return false
    }

    dependencies.createWindow()
    return true
  } catch (error: any) {
    dependencies.logFailure(error?.message || String(error))
    dependencies.quit()
    return false
  }
}
