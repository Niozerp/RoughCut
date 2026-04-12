import { app } from 'electron'
import { spawn, spawnSync, type ChildProcess } from 'child_process'
import { EventEmitter } from 'events'
import fs from 'fs'
import net from 'net'
import os from 'os'
import path from 'path'

import { executePythonCommand } from './pythonBridge.js'
import { buildStartArgs, withRootDir } from './spacetimeCli.js'
import {
  formatRustToolchainError,
  isMissingWasmTargetError,
  prependPathEntries,
  type RustToolchainStatus,
} from './spacetimeDependency.js'
import { inferRootDir, isLegacyAppDataDir } from './spacetimeInstall.js'

type BootstrapLifecycle = 'idle' | 'starting' | 'ready' | 'error'
export type StorageHealthLifecycle = 'idle' | 'starting' | 'ready' | 'degraded' | 'recovering' | 'error'
type StartupErrorCode =
  | 'PORT_IN_USE'
  | 'DATA_DIR_LOCKED'
  | 'SERVER_START_FAILED'
  | 'MODULE_PUBLISH_FAILED'

export interface SpacetimeRuntimeState {
  host: string
  port: number
  database_name: string
  module_path: string | null
  data_dir: string | null
  binary_path: string | null
  binary_version: string | null
  module_published: boolean
  module_fingerprint: string | null
  published_fingerprint: string | null
  last_ready_at: string | null
  last_health_check_at: string | null
}

export interface BootstrapStatus {
  status: BootstrapLifecycle
  message: string
  error?: string
  error_code?: StartupErrorCode
  spacetime: SpacetimeRuntimeState
}

export interface StorageHealthStatus {
  status: StorageHealthLifecycle
  message: string
  error?: string
  error_code?: StartupErrorCode
  lastHealthyAt?: string | null
  lastCheckAt?: string | null
  recoveryAttemptCount?: number
  spacetime: SpacetimeRuntimeState
}

export interface DatabaseStatusResult {
  success: boolean
  connected: boolean
  music_count: number
  sfx_count: number
  vfx_count: number
  total_count: number
  error?: string
}

const DEFAULT_RUNTIME: SpacetimeRuntimeState = {
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
}

const BOOT_TIMEOUT_MS = 15000
const HEALTH_POLL_INTERVAL_MS = 5000
const RECOVERY_FAILURE_THRESHOLD = 2
const WASM_TARGET = 'wasm32-unknown-unknown'

interface ResolvedSpacetimeRuntime {
  binaryPath: string
  binaryVersion: string | null
  rootDir: string | null
}

interface RuntimeHealthCheck {
  ok: boolean
  message: string
  error?: string
  rootDir?: string | null
}

interface StartupFailureDetails {
  errorCode: StartupErrorCode
  message: string
}

export function computeFingerprintFromStats(values: number[]): string | null {
  const validValues = values.filter((value) => Number.isFinite(value))
  if (validValues.length === 0) {
    return null
  }

  return String(Math.max(...validValues))
}

export function shouldPublishModule(
  alreadyPublished: boolean,
  runtime: Pick<SpacetimeRuntimeState, 'module_published' | 'published_fingerprint'>,
  moduleFingerprint: string | null,
  forcePublish: boolean
): boolean {
  if (forcePublish) {
    return true
  }

  if (!alreadyPublished || !runtime.module_published) {
    return true
  }

  if (!moduleFingerprint) {
    return true
  }

  return runtime.published_fingerprint !== moduleFingerprint
}

export class SpacetimeManager {
  private serverProcess: ChildProcess | null = null
  private bootstrapPromise: Promise<BootstrapStatus> | null = null
  private recoveryPromise: Promise<StorageHealthStatus> | null = null
  private status: BootstrapStatus = {
    status: 'idle',
    message: 'SpacetimeDB has not been started yet.',
    spacetime: { ...DEFAULT_RUNTIME },
  }
  private healthStatus: StorageHealthStatus = {
    status: 'idle',
    message: 'SpacetimeDB has not been started yet.',
    error: undefined,
    lastHealthyAt: null,
    lastCheckAt: null,
    recoveryAttemptCount: 0,
    spacetime: { ...DEFAULT_RUNTIME },
  }
  private readonly events = new EventEmitter()
  private healthMonitor: NodeJS.Timeout | null = null
  private consecutiveHealthFailures = 0

  getStatus(): BootstrapStatus {
    return {
      ...this.status,
      spacetime: { ...this.status.spacetime },
    }
  }

  getStorageHealth(): StorageHealthStatus {
    return {
      ...this.healthStatus,
      spacetime: { ...this.healthStatus.spacetime },
    }
  }

  getDatabaseStatus(): DatabaseStatusResult {
    const runtime = this.getStatus().spacetime
    if (
      this.status.status !== 'ready' ||
      !runtime.binary_path ||
      !runtime.database_name
    ) {
      return {
        success: false,
        connected: false,
        music_count: 0,
        sfx_count: 0,
        vfx_count: 0,
        total_count: 0,
        error: this.status.error || this.status.message,
      }
    }

    try {
      const counts = {
        music_count: this.queryCount(runtime.binary_path, runtime, 'music'),
        sfx_count: this.queryCount(runtime.binary_path, runtime, 'sfx'),
        vfx_count: this.queryCount(runtime.binary_path, runtime, 'vfx'),
        total_count: this.queryCount(runtime.binary_path, runtime),
      }

      return {
        success: true,
        connected: true,
        ...counts,
      }
    } catch (error) {
      return {
        success: false,
        connected: false,
        music_count: 0,
        sfx_count: 0,
        vfx_count: 0,
        total_count: 0,
        error: error instanceof Error ? error.message : String(error),
      }
    }
  }

  onHealthChanged(listener: (status: StorageHealthStatus) => void): () => void {
    this.events.on('health-changed', listener)
    return () => {
      this.events.off('health-changed', listener)
    }
  }

  async ensureReady(forcePublish = false): Promise<BootstrapStatus> {
    if (!forcePublish && this.status.status === 'ready') {
      return this.getStatus()
    }

    if (this.bootstrapPromise) {
      return this.bootstrapPromise
    }

    this.bootstrapPromise = this.bootstrap(forcePublish, false).finally(() => {
      this.bootstrapPromise = null
    })

    return this.bootstrapPromise
  }

  async retry(): Promise<BootstrapStatus> {
    return this.ensureReady(true)
  }

  async retryRecovery(): Promise<StorageHealthStatus> {
    if (this.recoveryPromise) {
      return this.recoveryPromise
    }

    if (this.bootstrapPromise) {
      await this.bootstrapPromise
      return this.getStorageHealth()
    }

    this.recoveryPromise = this.bootstrap(true, true)
      .then(() => this.getStorageHealth())
      .finally(() => {
        this.recoveryPromise = null
      })

    return this.recoveryPromise
  }

  stop(): void {
    this.stopHealthMonitor()

    if (!this.serverProcess) {
      return
    }

    try {
      this.serverProcess.kill()
    } catch (error) {
      console.warn('[SpacetimeManager] Failed to stop local SpacetimeDB process:', error)
    } finally {
      this.serverProcess = null
    }
  }

  private async bootstrap(forcePublish: boolean, recovery: boolean): Promise<BootstrapStatus> {
    const runtime = { ...this.status.spacetime }
    const bootstrapMessage = recovery
      ? 'Recovering local SpacetimeDB...'
      : 'Starting local SpacetimeDB...'

    this.status = {
      status: 'starting',
      message: bootstrapMessage,
      error: undefined,
      error_code: undefined,
      spacetime: runtime,
    }
    this.setHealthStatus({
      ...this.healthStatus,
      status: recovery ? 'recovering' : 'starting',
      message: bootstrapMessage,
      error: undefined,
      error_code: undefined,
      spacetime: runtime,
      recoveryAttemptCount: recovery
        ? (this.healthStatus.recoveryAttemptCount ?? 0) + 1
        : this.healthStatus.recoveryAttemptCount ?? 0,
    })

    try {
      const configState = await executePythonCommand('config_state', {})
      const existingRuntime = configState?.spacetime ?? {}

      const modulePath = this.resolveModulePath(existingRuntime.module_path)
      if (!modulePath) {
        throw new Error('Could not locate the shipped RoughCut SpacetimeDB module.')
      }

      const moduleFingerprint = this.computeModuleFingerprint(modulePath)
      const resolvedRuntime = this.resolveRuntimeInstallation(
        existingRuntime.binary_path,
        existingRuntime.data_dir
      )
      if (!resolvedRuntime) {
        throw new Error(
          'SpacetimeDB CLI was not found in the runtime environment after prelaunch bootstrap.'
        )
      }

      const normalizedRuntime = this.normalizeManagedRuntimeState(
        existingRuntime,
        modulePath,
        resolvedRuntime
      )

      const nextRuntime: SpacetimeRuntimeState = {
        host: normalizedRuntime.host,
        port: normalizedRuntime.port,
        database_name: normalizedRuntime.databaseName,
        module_path: modulePath,
        data_dir: normalizedRuntime.dataDir,
        binary_path: resolvedRuntime.binaryPath,
        binary_version: resolvedRuntime.binaryVersion,
        module_published: normalizedRuntime.modulePublished,
        module_fingerprint: moduleFingerprint,
        published_fingerprint: normalizedRuntime.publishedFingerprint,
        last_ready_at: normalizedRuntime.lastReadyAt,
        last_health_check_at: normalizedRuntime.lastHealthCheckAt,
      }
      nextRuntime.port = await this.resolveRuntimePort(
        resolvedRuntime.binaryPath,
        resolvedRuntime.rootDir,
        nextRuntime,
        normalizedRuntime.canonicalDataDir
      )
      nextRuntime.data_dir = this.resolveRuntimeDataDir(
        resolvedRuntime.rootDir,
        nextRuntime.data_dir,
        normalizedRuntime.canonicalDataDir
      )
      fs.mkdirSync(nextRuntime.data_dir, { recursive: true })

      await this.persistRuntimeState(nextRuntime)

      console.log(
        `[SpacetimeManager] Runtime resolved: binary=${resolvedRuntime.binaryPath}, root=${resolvedRuntime.rootDir ?? 'none'}, data=${nextRuntime.data_dir}, port=${nextRuntime.port}`
      )

      console.log('[SpacetimeManager] Ensuring local SpacetimeDB server is running...')
      await this.ensureDedicatedServerRunning(resolvedRuntime, nextRuntime)

      nextRuntime.last_health_check_at = this.nowIso()
      await this.persistRuntimeState(nextRuntime)

      const alreadyPublished = await this.isModulePublished(
        resolvedRuntime.binaryPath,
        resolvedRuntime.rootDir,
        nextRuntime.host,
        nextRuntime.port,
        nextRuntime.database_name
      )
      const moduleBuildCurrent = this.isModuleBuildCurrent(modulePath)
      const publishRequired =
        !moduleBuildCurrent ||
        shouldPublishModule(alreadyPublished, nextRuntime, moduleFingerprint, forcePublish)

      if (publishRequired) {
        this.ensureRustToolchain()
        console.log(
          `[SpacetimeManager] Publishing bundled module (fingerprint=${moduleFingerprint ?? 'unknown'})...`
        )

        try {
          await this.publishModule(
            resolvedRuntime.binaryPath,
            resolvedRuntime.rootDir,
            modulePath,
            nextRuntime.host,
            nextRuntime.port,
            nextRuntime.database_name
          )
        } catch (error) {
          if (this.isLocalAuthorizationError(error, nextRuntime.host)) {
            const recoveredDatabaseName = this.createRecoveryDatabaseName(nextRuntime.database_name)
            console.warn(
              `[SpacetimeManager] Publish authorization failed for local database ${nextRuntime.database_name}. Retrying with fresh local database ${recoveredDatabaseName}.`
            )
            nextRuntime.database_name = recoveredDatabaseName
            nextRuntime.module_published = false
            nextRuntime.published_fingerprint = null
            await this.persistRuntimeState(nextRuntime)
            await this.publishModule(
              resolvedRuntime.binaryPath,
              resolvedRuntime.rootDir,
              modulePath,
              nextRuntime.host,
              nextRuntime.port,
              nextRuntime.database_name
            )
          } else {
            throw this.normalizePublishError(error)
          }
        }
      }

      const readyAt = this.nowIso()
      nextRuntime.module_published = true
      nextRuntime.module_fingerprint = moduleFingerprint
      nextRuntime.published_fingerprint = moduleFingerprint
      nextRuntime.last_ready_at = readyAt
      nextRuntime.last_health_check_at = readyAt
      await this.persistRuntimeState(nextRuntime)

      this.status = {
        status: 'ready',
        message: 'Local SpacetimeDB is ready.',
        error_code: undefined,
        spacetime: nextRuntime,
      }

      this.consecutiveHealthFailures = 0
      this.setHealthStatus({
        status: 'ready',
        message: 'Local SpacetimeDB is ready.',
        error: undefined,
        error_code: undefined,
        lastHealthyAt: readyAt,
        lastCheckAt: readyAt,
        recoveryAttemptCount: recovery ? this.healthStatus.recoveryAttemptCount ?? 1 : 0,
        spacetime: nextRuntime,
      })
      this.startHealthMonitor()
    } catch (error) {
      const failure = this.toStartupFailureDetails(error)

      this.status = {
        status: 'error',
        message: 'Local media storage could not be started.',
        error: failure.message,
        error_code: failure.errorCode,
        spacetime: { ...this.status.spacetime },
      }
      this.setHealthStatus({
        ...this.healthStatus,
        status: 'error',
        message: recovery
          ? 'Local media storage could not be recovered.'
          : 'Local media storage could not be started.',
        error: failure.message,
        error_code: failure.errorCode,
        spacetime: { ...this.status.spacetime },
      })
    }

    return this.getStatus()
  }

  private setHealthStatus(nextStatus: StorageHealthStatus): void {
    this.healthStatus = {
      ...nextStatus,
      spacetime: { ...nextStatus.spacetime },
    }
    this.events.emit('health-changed', this.getStorageHealth())
  }

  private startHealthMonitor(): void {
    if (this.healthMonitor) {
      return
    }

    this.healthMonitor = setInterval(() => {
      void this.performHealthCheck()
    }, HEALTH_POLL_INTERVAL_MS)
    this.healthMonitor.unref?.()
  }

  private stopHealthMonitor(): void {
    if (!this.healthMonitor) {
      return
    }

    clearInterval(this.healthMonitor)
    this.healthMonitor = null
  }

  private async performHealthCheck(): Promise<void> {
    if (this.bootstrapPromise || this.recoveryPromise) {
      return
    }

    const runtime = this.healthStatus.spacetime
    if (!runtime.binary_path || !runtime.module_path || !runtime.data_dir) {
      return
    }

    const checkedAt = this.nowIso()
    const health = await this.checkRuntimeHealth(runtime)

    if (health.ok) {
      this.consecutiveHealthFailures = 0
      runtime.last_health_check_at = checkedAt
      await this.persistRuntimeState(runtime)

      if (this.healthStatus.status !== 'ready' || this.healthStatus.error) {
        this.setHealthStatus({
          status: 'ready',
          message: 'Local SpacetimeDB is healthy.',
          error: undefined,
          lastHealthyAt: checkedAt,
          lastCheckAt: checkedAt,
          recoveryAttemptCount: 0,
          spacetime: runtime,
        })
      } else {
        this.setHealthStatus({
          ...this.healthStatus,
          message: 'Local SpacetimeDB is healthy.',
          lastHealthyAt: checkedAt,
          lastCheckAt: checkedAt,
          spacetime: runtime,
        })
      }
      return
    }

    this.consecutiveHealthFailures += 1
    runtime.last_health_check_at = checkedAt
    await this.persistRuntimeState(runtime)

    if (this.healthStatus.status !== 'recovering') {
      console.warn('[SpacetimeManager] Health check failed:', health.error ?? health.message)
      this.setHealthStatus({
        ...this.healthStatus,
        status: 'degraded',
        message: health.message,
        error: health.error,
        lastCheckAt: checkedAt,
        spacetime: runtime,
      })
    }

    if (this.consecutiveHealthFailures >= RECOVERY_FAILURE_THRESHOLD) {
      void this.retryRecovery()
    }
  }

  private async checkRuntimeHealth(runtime: SpacetimeRuntimeState): Promise<RuntimeHealthCheck> {
    if (!runtime.binary_path) {
      return {
        ok: false,
        message: 'SpacetimeDB binary is no longer configured.',
        error: 'Missing binary path.',
      }
    }

    const inspection = this.inspectBinary(runtime.binary_path)
    const rootDir = inspection.rootDir
    const connectHost = runtime.host === 'localhost' ? '127.0.0.1' : runtime.host

    if (!(await this.isPortOpen(connectHost, runtime.port))) {
      return {
        ok: false,
        message: 'Local SpacetimeDB is not listening on the configured port.',
        error: `Port ${runtime.port} is unavailable.`,
        rootDir,
      }
    }

    if (!this.isSpacetimeServer(runtime.binary_path, rootDir, runtime.host, runtime.port)) {
      return {
        ok: false,
        message: 'The configured port is reachable, but SpacetimeDB did not answer health checks.',
        error: 'SpacetimeDB server ping failed.',
        rootDir,
      }
    }

    const modulePublished = await this.isModulePublished(
      runtime.binary_path,
      rootDir,
      runtime.host,
      runtime.port,
      runtime.database_name
    )
    if (!modulePublished) {
      return {
        ok: false,
        message: 'The local SpacetimeDB server is up, but the RoughCut module is not published.',
        error: 'Database describe check failed.',
        rootDir,
      }
    }

    return {
      ok: true,
      message: 'Local SpacetimeDB is healthy.',
      rootDir,
    }
  }

  private getCanonicalManagedDataDir(): string {
    return path.join(app.getPath('userData'), 'spacetimedb', 'data')
  }

  private getManagedRuntimeBaseDir(): string {
    return path.dirname(this.getCanonicalManagedDataDir())
  }

  private allocateFreshManagedDataDir(): string {
    const runtimeDir = path.join(
      this.getManagedRuntimeBaseDir(),
      `runtime-${Date.now().toString(36)}`
    )
    return path.join(runtimeDir, 'data')
  }

  private async ensureDedicatedServerRunning(
    resolvedRuntime: ResolvedSpacetimeRuntime,
    runtime: SpacetimeRuntimeState
  ): Promise<void> {
    try {
      await this.ensureServerRunning(
        resolvedRuntime.binaryPath,
        resolvedRuntime.rootDir,
        runtime,
        runtime.data_dir,
        runtime.host,
        runtime.port
      )
      return
    } catch (error) {
      const failure = this.toStartupFailureDetails(error)
      if (failure.errorCode !== 'DATA_DIR_LOCKED') {
        throw error
      }

      const replacementDataDir = this.allocateFreshManagedDataDir()
      const replacementPort = await this.findAvailablePort(runtime.host, runtime.port + 1)
      console.warn(
        `[SpacetimeManager] Managed data dir is locked (${runtime.data_dir}). Retrying with fresh managed dir ${replacementDataDir} on port ${replacementPort}.`
      )

      runtime.data_dir = replacementDataDir
      runtime.port = replacementPort
      runtime.module_published = false
      runtime.published_fingerprint = null
      runtime.last_ready_at = null
      runtime.last_health_check_at = null
      await this.persistRuntimeState(runtime)

      await this.ensureServerRunning(
        resolvedRuntime.binaryPath,
        resolvedRuntime.rootDir,
        runtime,
        runtime.data_dir,
        runtime.host,
        runtime.port
      )
    }
  }

  private normalizeManagedRuntimeState(
    existingRuntime: Record<string, unknown>,
    modulePath: string,
    resolvedRuntime: ResolvedSpacetimeRuntime
  ): {
    host: string
    port: number
    databaseName: string
    dataDir: string
    canonicalDataDir: string
    modulePublished: boolean
    publishedFingerprint: string | null
    lastReadyAt: string | null
    lastHealthCheckAt: string | null
  } {
    const canonicalDataDir = this.getCanonicalManagedDataDir()
    const configuredDataDir =
      typeof existingRuntime.data_dir === 'string' ? existingRuntime.data_dir : null
    const normalizedModulePath =
      typeof existingRuntime.module_path === 'string' ? existingRuntime.module_path : null
    const normalizedDataDir = this.resolveRuntimeDataDir(
      resolvedRuntime.rootDir,
      configuredDataDir,
      canonicalDataDir
    )
    const moduleMatches =
      normalizedModulePath !== null &&
      path.resolve(normalizedModulePath).toLowerCase() === path.resolve(modulePath).toLowerCase()

    return {
      host: String(existingRuntime.host ?? DEFAULT_RUNTIME.host),
      port: Number(existingRuntime.port ?? DEFAULT_RUNTIME.port),
      databaseName: String(existingRuntime.database_name ?? DEFAULT_RUNTIME.database_name),
      dataDir: normalizedDataDir,
      canonicalDataDir,
      modulePublished: Boolean(existingRuntime.module_published) && moduleMatches,
      publishedFingerprint:
        typeof existingRuntime.published_fingerprint === 'string'
          ? existingRuntime.published_fingerprint
          : null,
      lastReadyAt:
        typeof existingRuntime.last_ready_at === 'string' ? existingRuntime.last_ready_at : null,
      lastHealthCheckAt:
        typeof existingRuntime.last_health_check_at === 'string'
          ? existingRuntime.last_health_check_at
          : null,
    }
  }

  private resolveModulePath(configuredPath: string | null | undefined): string | null {
    const candidates = [
      configuredPath,
      path.join(app.getAppPath(), '..', 'src', 'roughcut', 'backend', 'database', 'rust_modules'),
      path.join(app.getAppPath(), 'src', 'roughcut', 'backend', 'database', 'rust_modules'),
      path.join(
        app.getAppPath(),
        '..',
        '..',
        'roughcut',
        'src',
        'roughcut',
        'backend',
        'database',
        'rust_modules'
      ),
      path.join(process.cwd(), '..', 'src', 'roughcut', 'backend', 'database', 'rust_modules'),
      path.join(process.cwd(), 'src', 'roughcut', 'backend', 'database', 'rust_modules'),
    ]

    for (const candidate of candidates) {
      if (!candidate) {
        continue
      }

      const cargoToml = path.join(candidate, 'Cargo.toml')
      const libFile = path.join(candidate, 'src', 'lib.rs')
      if (fs.existsSync(cargoToml) && fs.existsSync(libFile)) {
        return path.resolve(candidate)
      }
    }

    return null
  }

  private computeModuleFingerprint(modulePath: string): string | null {
    const sourceMtime = this.computeLatestMtime([
      path.join(modulePath, 'Cargo.toml'),
      path.join(modulePath, 'src'),
    ])
    return sourceMtime ? String(sourceMtime) : null
  }

  private isModuleBuildCurrent(modulePath: string): boolean {
    const sourceMtime = this.computeLatestMtime([
      path.join(modulePath, 'Cargo.toml'),
      path.join(modulePath, 'src'),
    ])
    const wasmPath = this.resolveWasmArtifactPath(modulePath)
    if (!wasmPath || !fs.existsSync(wasmPath)) {
      return false
    }

    const wasmMtime = fs.statSync(wasmPath).mtimeMs
    return wasmMtime >= sourceMtime
  }

  private resolveWasmArtifactPath(modulePath: string): string | null {
    const cargoTomlPath = path.join(modulePath, 'Cargo.toml')
    let crateName = 'roughcut_spacetimedb'

    if (fs.existsSync(cargoTomlPath)) {
      const cargoToml = fs.readFileSync(cargoTomlPath, 'utf-8')
      const match = cargoToml.match(/^name\s*=\s*"([^"]+)"/m)
      if (match) {
        crateName = match[1].replace(/-/g, '_')
      }
    }

    return path.join(
      modulePath,
      'target',
      'wasm32-unknown-unknown',
      'release',
      `${crateName}.wasm`
    )
  }

  private computeLatestMtime(pathsToInspect: string[]): number {
    const visit = (candidatePath: string): number => {
      if (!fs.existsSync(candidatePath)) {
        return 0
      }

      const stats = fs.statSync(candidatePath)
      if (stats.isFile()) {
        return stats.mtimeMs
      }

      let latestMtime = stats.mtimeMs
      for (const entry of fs.readdirSync(candidatePath)) {
        latestMtime = Math.max(latestMtime, visit(path.join(candidatePath, entry)))
      }
      return latestMtime
    }

    return Math.max(...pathsToInspect.map((candidatePath) => visit(candidatePath)))
  }

  private resolveBinaryPath(configuredPath: string | null | undefined): string | null {
    const executableName = process.platform === 'win32' ? 'spacetime.exe' : 'spacetime'
    const homeDir = process.env.USERPROFILE || process.env.HOME || ''
    const localAppData = process.env.LOCALAPPDATA || ''
    const appData = process.env.APPDATA || ''
    const explicitCandidates = [
      configuredPath,
      process.env.SPACETIME_BIN,
      localAppData ? path.join(localAppData, 'SpacetimeDB', executableName) : null,
      homeDir ? path.join(homeDir, '.local', 'bin', executableName) : null,
      localAppData ? path.join(localAppData, 'SpacetimeDB', 'bin', executableName) : null,
      appData ? path.join(appData, 'SpacetimeDB', executableName) : null,
      appData ? path.join(appData, 'SpacetimeDB', 'bin', executableName) : null,
      path.join(app.getAppPath(), '..', 'bin', executableName),
      path.join(app.getAppPath(), 'bin', executableName),
      path.join(process.cwd(), '..', 'bin', executableName),
      path.join(process.cwd(), 'bin', executableName),
    ]

    for (const candidate of explicitCandidates) {
      if (!candidate || !fs.existsSync(candidate)) {
        continue
      }

      if (this.canExecute(candidate)) {
        return path.resolve(candidate)
      }
    }

    for (const commandCandidate of ['spacetime', executableName]) {
      if (this.canExecute(commandCandidate)) {
        return commandCandidate
      }
    }

    return null
  }

  private getRuntimeEnv(): NodeJS.ProcessEnv {
    const env = { ...process.env }
    const homeDir = process.env.USERPROFILE || process.env.HOME || ''
    const localAppData = process.env.LOCALAPPDATA || ''
    const appData = process.env.APPDATA || ''

    env.PATH = prependPathEntries(env.PATH, [
      homeDir ? path.join(homeDir, '.cargo', 'bin') : '',
      homeDir ? path.join(homeDir, '.local', 'bin') : '',
      localAppData ? path.join(localAppData, 'SpacetimeDB') : '',
      localAppData ? path.join(localAppData, 'SpacetimeDB', 'bin') : '',
      appData ? path.join(appData, 'SpacetimeDB') : '',
      appData ? path.join(appData, 'SpacetimeDB', 'bin') : '',
    ])

    return env
  }

  private canExecute(command: string): boolean {
    const result = spawnSync(command, ['--version'], {
      encoding: 'utf-8',
      env: this.getRuntimeEnv(),
      timeout: 5000,
      windowsHide: true,
    })

    return result.status === 0
  }

  private getRustToolchainStatus(): RustToolchainStatus {
    const cargoAvailable = this.canExecute('cargo')
    const rustupAvailable = this.canExecute('rustup')
    let wasmTargetInstalled = false

    if (rustupAvailable) {
      const result = spawnSync('rustup', ['target', 'list', '--installed'], {
        encoding: 'utf-8',
        env: this.getRuntimeEnv(),
        timeout: 10000,
        windowsHide: true,
      })

      const output = `${result.stdout ?? ''}${result.stderr ?? ''}`
      wasmTargetInstalled =
        result.status === 0 &&
        output
          .split(/\r?\n/)
          .some((line) => line.trim() === WASM_TARGET)
    }

    return {
      cargoAvailable,
      rustupAvailable,
      wasmTargetInstalled,
    }
  }

  private ensureRustToolchain(): void {
    const toolchainStatus = this.getRustToolchainStatus()
    if (
      toolchainStatus.cargoAvailable &&
      toolchainStatus.rustupAvailable &&
      toolchainStatus.wasmTargetInstalled
    ) {
      return
    }

    throw new Error(formatRustToolchainError(toolchainStatus, process.platform))
  }

  private normalizePublishError(error: unknown): Error {
    const message = error instanceof Error ? error.message : String(error)
    if (!isMissingWasmTargetError(message)) {
      return error instanceof Error ? error : new Error(message)
    }

    const toolchainStatus = this.getRustToolchainStatus()
    return new Error(formatRustToolchainError(toolchainStatus, process.platform))
  }

  private isLocalAuthorizationError(error: unknown, host: string): boolean {
    const message = error instanceof Error ? error.message : String(error)
    const isLocalHost = host === 'localhost' || host === '127.0.0.1'
    return (
      isLocalHost &&
      /403\s+forbidden/i.test(message) &&
      /not authorized to perform action on database/i.test(message)
    )
  }

  private createRecoveryDatabaseName(currentName: string): string {
    const username = (process.env.USERNAME || process.env.USER || os.userInfo().username || 'local')
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/^-+|-+$/g, '')
    const baseName = (currentName || 'roughcut')
      .toLowerCase()
      .replace(/[^a-z0-9-]+/g, '-')
      .replace(/^-+|-+$/g, '')
    const suffix = `${username || 'local'}-${Date.now().toString(36)}`
      .replace(/[^a-z0-9-]+/g, '-')
      .replace(/^-+|-+$/g, '')

    return `${baseName || 'roughcut'}-${suffix}`.slice(0, 63)
  }

  private inspectBinary(binaryPath: string): { version: string | null; rootDir: string | null } {
    const result = spawnSync(binaryPath, ['--version'], {
      encoding: 'utf-8',
      env: this.getRuntimeEnv(),
      timeout: 5000,
      windowsHide: true,
    })

    const output = `${result.stdout ?? ''}${result.stderr ?? ''}`.trim()
    if (result.status !== 0 || !output) {
      return {
        version: null,
        rootDir: inferRootDir(binaryPath, null),
      }
    }

    return {
      version: output,
      rootDir: inferRootDir(binaryPath, output),
    }
  }

  private resolveRuntimeInstallation(
    configuredBinaryPath: string | null | undefined,
    _configuredDataDir: string | null | undefined
  ): ResolvedSpacetimeRuntime | null {
    const binaryPath = this.resolveBinaryPath(configuredBinaryPath)
    if (!binaryPath) {
      return null
    }

    const inspection = this.inspectBinary(binaryPath)
    return {
      binaryPath,
      binaryVersion: inspection.version,
      rootDir: inspection.rootDir,
    }
  }

  private resolveRuntimeDataDir(
    rootDir: string | null,
    configuredDataDir: string | null | undefined,
    canonicalDataDir = this.getCanonicalManagedDataDir()
  ): string {
    const defaultDataDir = canonicalDataDir
    if (!configuredDataDir) {
      return defaultDataDir
    }

    const resolvedConfigured = path.resolve(configuredDataDir)
    const sharedInstallDataDir = rootDir ? path.join(path.resolve(rootDir), 'data') : null
    if (
      isLegacyAppDataDir(resolvedConfigured) ||
      (sharedInstallDataDir !== null &&
        path.resolve(sharedInstallDataDir).toLowerCase() === resolvedConfigured.toLowerCase())
    ) {
      return defaultDataDir
    }

    return resolvedConfigured
  }

  private resolveServerUrl(host: string, port: number): string {
    const connectHost = host === 'localhost' ? '127.0.0.1' : host
    return `http://${connectHost}:${port}`
  }

  private queryCount(
    binaryPath: string,
    runtime: Pick<SpacetimeRuntimeState, 'host' | 'port' | 'database_name'>,
    category?: 'music' | 'sfx' | 'vfx'
  ): number {
    const query = category
      ? `SELECT COUNT(*) AS total FROM media_assets WHERE category = '${category}'`
      : 'SELECT COUNT(*) AS total FROM media_assets'

    const result = spawnSync(
      binaryPath,
      withRootDir(this.resolveRuntimeInstallation(binaryPath, null)?.rootDir ?? null, [
        'sql',
        '--anonymous',
        '--server',
        this.resolveServerUrl(runtime.host, runtime.port),
        '--yes',
        runtime.database_name,
        query,
      ]),
      {
        encoding: 'utf-8',
        env: this.getRuntimeEnv(),
        timeout: 10000,
        windowsHide: true,
      }
    )

    if (result.status !== 0) {
      const output = `${result.stdout ?? ''}${result.stderr ?? ''}`.trim()
      throw new Error(output || `Failed to query ${category ?? 'total'} asset count.`)
    }

    return this.parseCountOutput(`${result.stdout ?? ''}${result.stderr ?? ''}`)
  }

  private parseCountOutput(output: string): number {
    const lines = output
      .split(/\r?\n/)
      .map((line) => line.trim())
      .filter((line) => line && !line.startsWith('WARNING:'))

    for (const line of lines) {
      if (/^\d+$/.test(line)) {
        return Number(line)
      }
    }

    throw new Error(`Could not parse count from SpacetimeDB SQL output.\n${output}`)
  }

  private isSpacetimeServer(
    binaryPath: string,
    rootDir: string | null,
    host: string,
    port: number
  ): boolean {
    const result = spawnSync(
      binaryPath,
      withRootDir(rootDir, ['server', 'ping', this.resolveServerUrl(host, port)]),
      {
        encoding: 'utf-8',
        env: this.getRuntimeEnv(),
        timeout: 5000,
        windowsHide: true,
      }
    )

    const output = `${result.stdout ?? ''}${result.stderr ?? ''}`.toLowerCase()
    return result.status === 0 && output.includes('server is online')
  }

  private async findAvailablePort(_host: string, startingPort: number): Promise<number> {
    for (let port = startingPort; port < startingPort + 100; port += 1) {
      if (!(await this.isLocalPortOccupied(port))) {
        return port
      }
    }

    throw new Error('Could not find an available local port for SpacetimeDB.')
  }

  private async resolveRuntimePort(
    binaryPath: string,
    rootDir: string | null,
    runtime: SpacetimeRuntimeState,
    canonicalDataDir: string
  ): Promise<number> {
    if (!(await this.isLocalPortOccupied(runtime.port))) {
      return runtime.port
    }

    if (await this.canReuseManagedServer(binaryPath, rootDir, runtime, canonicalDataDir)) {
      return runtime.port
    }

    return this.findAvailablePort(runtime.host, runtime.port + 1)
  }

  private async ensureServerRunning(
    binaryPath: string,
    rootDir: string | null,
    runtime: Pick<SpacetimeRuntimeState, 'host' | 'port' | 'database_name' | 'data_dir'>,
    dataDir: string | null,
    host: string,
    port: number
  ): Promise<void> {
    if (!dataDir) {
      throw new Error('SpacetimeDB data directory is not configured.')
    }

    fs.mkdirSync(dataDir, { recursive: true })

    if (this.serverProcess && this.isSpacetimeServer(binaryPath, rootDir, host, port)) {
      return
    }

    if (await this.canReuseManagedServer(binaryPath, rootDir, runtime, dataDir)) {
      return
    }

    if (await this.isLocalPortOccupied(port)) {
      throw new Error(`Port ${port} is already in use by another local process.`)
    }

    const args = buildStartArgs(rootDir, dataDir, host, port)

    const proc = spawn(binaryPath, args, {
      cwd: rootDir ?? undefined,
      env: this.getRuntimeEnv(),
      stdio: ['ignore', 'pipe', 'pipe'],
      windowsHide: true,
    })

    this.serverProcess = proc
    const startupLogs = this.captureProcessFailureDetails(proc)

    await new Promise<void>((resolve, reject) => {
      let finished = false

      const cleanup = () => {
        proc.removeListener('error', handleError)
        proc.removeListener('exit', handleExit)
      }

      const handleError = (error: Error) => {
        if (finished) {
          return
        }

        finished = true
        cleanup()
        reject(error)
      }

      const handleExit = (code: number | null) => {
        if (finished) {
          return
        }

        finished = true
        cleanup()
        reject(
          new Error(
            this.formatServerStartupFailure(
              `SpacetimeDB exited before becoming ready (exit code ${code ?? 'unknown'}).`,
              startupLogs()
            )
          )
        )
      }

      proc.once('error', handleError)
      proc.once('exit', handleExit)

      void this.waitForPort(host, port, BOOT_TIMEOUT_MS)
        .then(() => {
          if (finished) {
            return
          }

          finished = true
          cleanup()
          resolve()
        })
        .catch((error) => {
          if (finished) {
            return
          }

          finished = true
          cleanup()
          reject(
            new Error(
              this.formatServerStartupFailure(
                error instanceof Error ? error.message : String(error),
                startupLogs()
              )
            )
          )
        })
    })
  }

  private async waitForPort(_host: string, port: number, timeoutMs: number): Promise<void> {
    const deadline = Date.now() + timeoutMs

    while (Date.now() < deadline) {
      if (await this.isLocalPortOccupied(port)) {
        return
      }

      await new Promise((resolve) => setTimeout(resolve, 400))
    }

    throw new Error('Timed out waiting for the local SpacetimeDB server to start.')
  }

  private async isPortOpen(host: string, port: number): Promise<boolean> {
    return new Promise((resolve) => {
      const socket = net.connect({ host, port })

      const finish = (result: boolean) => {
        socket.removeAllListeners()
        socket.destroy()
        resolve(result)
      }

      socket.once('connect', () => finish(true))
      socket.once('error', () => finish(false))
      socket.setTimeout(1000, () => finish(false))
    })
  }

  private async isLocalPortOccupied(port: number): Promise<boolean> {
    const checks = await Promise.all([
      this.isPortOpen('127.0.0.1', port),
      this.isPortOpen('::1', port),
      this.isPortOpen('localhost', port),
    ])

    return checks.some(Boolean)
  }

  private async canReuseManagedServer(
    binaryPath: string,
    rootDir: string | null,
    runtime: Pick<SpacetimeRuntimeState, 'host' | 'port' | 'database_name' | 'data_dir'>,
    canonicalDataDir: string
  ): Promise<boolean> {
    const runtimeDataDir = runtime.data_dir ? path.resolve(runtime.data_dir) : null
    if (!runtimeDataDir || runtimeDataDir.toLowerCase() !== path.resolve(canonicalDataDir).toLowerCase()) {
      return false
    }

    if (!(await this.isLocalPortOccupied(runtime.port))) {
      return false
    }

    if (!this.isSpacetimeServer(binaryPath, rootDir, runtime.host, runtime.port)) {
      return false
    }

    return this.isModulePublished(
      binaryPath,
      rootDir,
      runtime.host,
      runtime.port,
      runtime.database_name
    )
  }

  private captureProcessFailureDetails(proc: ChildProcess): () => string {
    const lines: string[] = []
    const appendChunk = (chunk: Buffer | string) => {
      const text = chunk.toString()
      for (const rawLine of text.split(/\r?\n/)) {
        const line = rawLine.trim()
        if (!line) {
          continue
        }

        lines.push(line)
        if (lines.length > 12) {
          lines.shift()
        }
      }
    }

    proc.stdout?.on('data', appendChunk)
    proc.stderr?.on('data', appendChunk)

    return () => lines.join('\n')
  }

  private formatServerStartupFailure(baseMessage: string, capturedOutput: string): string {
    if (!capturedOutput) {
      return baseMessage
    }

    return `${baseMessage}\n${capturedOutput}`
  }

  private toStartupFailureDetails(error: unknown): StartupFailureDetails {
    const message = error instanceof Error ? error.message : String(error)
    const normalized = message.toLowerCase()

    if (
      normalized.includes('port ') &&
      (normalized.includes('already in use') || normalized.includes('address already in use'))
    ) {
      return { errorCode: 'PORT_IN_USE', message }
    }

    if (
      normalized.includes('database lock') ||
      normalized.includes('spacetime.pid') ||
      normalized.includes('locked a portion of the file')
    ) {
      return { errorCode: 'DATA_DIR_LOCKED', message }
    }

    if (normalized.includes('publish')) {
      return { errorCode: 'MODULE_PUBLISH_FAILED', message }
    }

    return { errorCode: 'SERVER_START_FAILED', message }
  }

  private async isModulePublished(
    binaryPath: string,
    rootDir: string | null,
    host: string,
    port: number,
    databaseName: string
  ): Promise<boolean> {
    const result = spawnSync(
      binaryPath,
      withRootDir(rootDir, [
        'describe',
        '--json',
        '--server',
        this.resolveServerUrl(host, port),
        '--yes',
        databaseName,
      ]),
      {
        encoding: 'utf-8',
        env: this.getRuntimeEnv(),
        timeout: 10000,
        windowsHide: true,
      }
    )

    return result.status === 0
  }

  private async publishModule(
    binaryPath: string,
    rootDir: string | null,
    modulePath: string,
    host: string,
    port: number,
    databaseName: string
  ): Promise<void> {
    await this.runCommand(
      binaryPath,
      withRootDir(rootDir, [
        'publish',
        '--yes',
        '--server',
        this.resolveServerUrl(host, port),
        '--module-path',
        modulePath,
        databaseName,
      ])
    )
    console.log('[SpacetimeManager] Module publish completed successfully.')
  }

  private async runCommand(binaryPath: string, args: string[]): Promise<void> {
    await new Promise<void>((resolve, reject) => {
      const proc = spawn(binaryPath, args, {
        env: this.getRuntimeEnv(),
        windowsHide: true,
      })

      let stdout = ''
      let stderr = ''

      proc.stdout?.on('data', (chunk: Buffer | string) => {
        stdout += chunk.toString()
      })

      proc.stderr?.on('data', (chunk: Buffer | string) => {
        stderr += chunk.toString()
      })

      proc.once('error', (error) => {
        reject(error)
      })

      proc.once('close', (code) => {
        if (code === 0) {
          resolve()
          return
        }

        const output = `${stdout}\n${stderr}`.trim()
        reject(
          new Error(
            output || `Command failed: ${binaryPath} ${args.join(' ')} (exit code ${code ?? 'unknown'})`
          )
        )
      })
    })
  }

  private async persistRuntimeState(runtime: SpacetimeRuntimeState): Promise<void> {
    await executePythonCommand('save_spacetime_runtime', runtime)
  }

  private nowIso(): string {
    return new Date().toISOString()
  }
}

let manager: SpacetimeManager | null = null

export function getSpacetimeManager(): SpacetimeManager {
  if (!manager) {
    manager = new SpacetimeManager()
  }

  return manager
}
