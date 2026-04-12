import { describe, expect, it, vi } from 'vitest'

import { bootstrapAndCreateWindow } from '../../electron/appBootstrap'

describe('appBootstrap', () => {
  it('does not create the window when prelaunch bootstrap returns an error status', async () => {
    const createWindow = vi.fn()
    const ensureReady = vi.fn().mockResolvedValue({
      status: 'error',
      message: 'Local media storage could not be started.',
      error: 'Rust toolchain missing',
    })
    const logFailure = vi.fn()
    const quit = vi.fn()

    const launched = await bootstrapAndCreateWindow({
      createWindow,
      ensureReady,
      logFailure,
      quit,
    })

    expect(launched).toBe(false)
    expect(createWindow).not.toHaveBeenCalled()
    expect(quit).toHaveBeenCalledTimes(1)
    expect(logFailure).toHaveBeenCalledWith('Rust toolchain missing')
  })

  it('creates the window only after bootstrap reports ready', async () => {
    const createWindow = vi.fn()
    const ensureReady = vi.fn().mockResolvedValue({
      status: 'ready',
      message: 'Local SpacetimeDB is ready.',
      spacetime: {},
    })
    const logFailure = vi.fn()
    const quit = vi.fn()

    const launched = await bootstrapAndCreateWindow({
      createWindow,
      ensureReady,
      logFailure,
      quit,
    })

    expect(launched).toBe(true)
    expect(createWindow).toHaveBeenCalledTimes(1)
    expect(logFailure).not.toHaveBeenCalled()
    expect(quit).not.toHaveBeenCalled()
  })

  it('quits without creating a window when bootstrap throws', async () => {
    const createWindow = vi.fn()
    const ensureReady = vi.fn().mockRejectedValue(new Error('publish failed'))
    const logFailure = vi.fn()
    const quit = vi.fn()

    const launched = await bootstrapAndCreateWindow({
      createWindow,
      ensureReady,
      logFailure,
      quit,
    })

    expect(launched).toBe(false)
    expect(createWindow).not.toHaveBeenCalled()
    expect(quit).toHaveBeenCalledTimes(1)
    expect(logFailure).toHaveBeenCalledWith('publish failed')
  })
})
