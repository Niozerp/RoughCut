import path from 'path'

import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('electron', () => ({
  app: {
    getAppPath: () => '/tmp/roughcut',
    getPath: () => '/tmp/roughcut-userdata',
  },
}))

vi.mock('../../electron/pythonBridge', () => ({
  executePythonCommand: vi.fn(),
}))

import {
  SpacetimeManager,
  computeFingerprintFromStats,
  shouldPublishModule,
} from '../../electron/spacetimeManager'

describe('spacetimeManager helpers', () => {
  it('computes the latest fingerprint from candidate mtimes', () => {
    expect(computeFingerprintFromStats([10, 25, 5])).toBe('25')
    expect(computeFingerprintFromStats([])).toBeNull()
  })

  it('forces publish when the published fingerprint does not match module sources', () => {
    expect(
      shouldPublishModule(
        true,
        {
          module_published: true,
          published_fingerprint: '100',
        },
        '200',
        false
      )
    ).toBe(true)
  })

  it('skips publish when the module is already published with the current fingerprint', () => {
    expect(
      shouldPublishModule(
        true,
        {
          module_published: true,
          published_fingerprint: '200',
        },
        '200',
        false
      )
    ).toBe(false)
  })
})

describe('SpacetimeManager single-flight', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('reuses the in-flight bootstrap promise for concurrent ensureReady calls', async () => {
    const manager = new SpacetimeManager()
    const readyStatus = {
      status: 'ready' as const,
      message: 'Local SpacetimeDB is ready.',
      spacetime: {
        host: 'localhost',
        port: 3000,
        database_name: 'roughcut',
        module_path: null,
        data_dir: null,
        binary_path: null,
        binary_version: null,
        module_published: false,
        module_fingerprint: null,
        published_fingerprint: null,
        last_ready_at: null,
        last_health_check_at: null,
      },
    }

    const bootstrapSpy = vi
      .spyOn(manager as any, 'bootstrap')
      .mockImplementation(
        () =>
          new Promise((resolve) => {
            setTimeout(() => resolve(readyStatus), 20)
          })
      )

    const [first, second] = await Promise.all([manager.ensureReady(), manager.ensureReady()])

    expect(first).toEqual(readyStatus)
    expect(second).toEqual(readyStatus)
    expect(bootstrapSpy).toHaveBeenCalledTimes(1)
  })
})

describe('SpacetimeManager runtime decisions', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('treats IPv6 or wildcard listeners as occupied local ports', async () => {
    const manager = new SpacetimeManager()
    const portOpenSpy = vi.spyOn(manager as any, 'isPortOpen')

    portOpenSpy.mockImplementation(async (...args: unknown[]) => args[0] === '::1')

    await expect((manager as any).isLocalPortOccupied(3000)).resolves.toBe(true)
    expect(portOpenSpy).toHaveBeenCalledWith('127.0.0.1', 3000)
    expect(portOpenSpy).toHaveBeenCalledWith('::1', 3000)
    expect(portOpenSpy).toHaveBeenCalledWith('localhost', 3000)
  })

  it('skips an occupied preferred port when the listener is not a reusable managed runtime', async () => {
    const manager = new SpacetimeManager()

    vi.spyOn(manager as any, 'isLocalPortOccupied').mockImplementation(async (...args: unknown[]) => args[0] === 3000)
    vi.spyOn(manager as any, 'canReuseManagedServer').mockResolvedValue(false)

    const resolvedPort = await (manager as any).resolveRuntimePort(
      'spacetime',
      'C:/SpacetimeDB',
      {
        host: 'localhost',
        port: 3000,
        database_name: 'roughcut',
        data_dir: '/tmp/roughcut-userdata/spacetimedb/data',
      },
      '/tmp/roughcut-userdata/spacetimedb/data'
    )

    expect(resolvedPort).toBe(3001)
  })

  it('reuses only a healthy managed runtime on the canonical data dir', async () => {
    const manager = new SpacetimeManager()

    vi.spyOn(manager as any, 'isLocalPortOccupied').mockResolvedValue(true)
    vi.spyOn(manager as any, 'isSpacetimeServer').mockReturnValue(true)
    vi.spyOn(manager as any, 'isModulePublished').mockResolvedValue(true)

    await expect(
      (manager as any).canReuseManagedServer(
        'spacetime',
        'C:/SpacetimeDB',
        {
          host: 'localhost',
          port: 3001,
          database_name: 'roughcut',
          data_dir: '/tmp/roughcut-userdata/spacetimedb/data',
        },
        '/tmp/roughcut-userdata/spacetimedb/data'
      )
    ).resolves.toBe(true)

    await expect(
      (manager as any).canReuseManagedServer(
        'spacetime',
        'C:/SpacetimeDB',
        {
          host: 'localhost',
          port: 3001,
          database_name: 'roughcut',
          data_dir: '/tmp/legacy/roughcut-electron/spacetimedb/data',
        },
        '/tmp/roughcut-userdata/spacetimedb/data'
      )
    ).resolves.toBe(false)
  })

  it('normalizes legacy data dirs to the canonical managed data dir', () => {
    const manager = new SpacetimeManager()

    const normalized = (manager as any).normalizeManagedRuntimeState(
      {
        host: 'localhost',
        port: 3002,
        database_name: 'roughcut',
        data_dir: 'C:/Users/niozerp/AppData/Roaming/RoughCut Electron/spacetimedb/data',
        module_path: '/tmp/roughcut/src/roughcut/backend/database/rust_modules',
        module_published: true,
      },
      '/tmp/roughcut/src/roughcut/backend/database/rust_modules',
      {
        binaryPath: 'spacetime',
        binaryVersion: '2.1.0',
        rootDir: 'C:/Users/niozerp/AppData/Local/SpacetimeDB',
      }
    )

    expect(normalized.dataDir).toBe(path.join('/tmp/roughcut-userdata', 'spacetimedb', 'data'))
    expect(normalized.canonicalDataDir).toBe(
      path.join('/tmp/roughcut-userdata', 'spacetimedb', 'data')
    )
  })

  it('returns captured startup details for port and lock failures', () => {
    const manager = new SpacetimeManager()

    expect((manager as any).toStartupFailureDetails('Error: Port 3000 is already in use.')).toEqual({
      errorCode: 'PORT_IN_USE',
      message: 'Error: Port 3000 is already in use.',
    })

    expect(
      (manager as any).toStartupFailureDetails(
        'Error: error while taking database lock on spacetime.pid'
      )
    ).toEqual({
      errorCode: 'DATA_DIR_LOCKED',
      message: 'Error: error while taking database lock on spacetime.pid',
    })
  })

  it('includes captured child process output in startup failures', () => {
    const manager = new SpacetimeManager()

    const message = (manager as any).formatServerStartupFailure(
      'SpacetimeDB exited before becoming ready (exit code 1).',
      'Error: Port 3000 is already in use.'
    )

    expect(message).toContain('exit code 1')
    expect(message).toContain('Port 3000 is already in use')
  })

  it('rolls over to a fresh managed data dir when the configured dir is locked', async () => {
    const manager = new SpacetimeManager()
    const runtime = {
      host: 'localhost',
      port: 3002,
      database_name: 'roughcut',
      data_dir: path.join('/tmp/roughcut-userdata', 'spacetimedb', 'data'),
      module_published: true,
      published_fingerprint: '123',
      last_ready_at: 'now',
      last_health_check_at: 'now',
    }
    const resolvedRuntime = {
      binaryPath: 'spacetime',
      binaryVersion: '2.1.0',
      rootDir: 'C:/SpacetimeDB',
    }

    const ensureServerRunning = vi.spyOn(manager as any, 'ensureServerRunning')
    ensureServerRunning
      .mockRejectedValueOnce(new Error('Error: error while taking database lock on spacetime.pid'))
      .mockResolvedValueOnce(undefined)

    vi.spyOn(manager as any, 'findAvailablePort').mockResolvedValue(3003)
    const persistSpy = vi.spyOn(manager as any, 'persistRuntimeState').mockResolvedValue(undefined)

    await (manager as any).ensureDedicatedServerRunning(resolvedRuntime, runtime)

    expect(runtime.port).toBe(3003)
    expect(runtime.data_dir).toContain(path.join('spacetimedb', 'runtime-'))
    expect(runtime.data_dir).toContain(path.join('data'))
    expect(runtime.module_published).toBe(false)
    expect(runtime.published_fingerprint).toBeNull()
    expect(persistSpy).toHaveBeenCalled()
    expect(ensureServerRunning).toHaveBeenCalledTimes(2)
  })
})
