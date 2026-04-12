import path from 'path'

const CLI_PATH_PREFIX = 'spacetime Path:'
const LEGACY_APP_DATA_SEGMENTS = [
  path.join('roughcut-electron', 'spacetimedb').toLowerCase(),
  path.join('roughcut electron', 'spacetimedb').toLowerCase(),
]

function isBareCommand(candidate: string): boolean {
  return !candidate.includes(path.sep) && !candidate.includes('/') && !candidate.includes('\\')
}

function isWrapperBinary(fileName: string): boolean {
  return /^spacetime(?:\.exe)?$/i.test(fileName)
}

function isCliBinary(fileName: string): boolean {
  return /^spacetimedb-cli(?:\.exe)?$/i.test(fileName)
}

export function parseInstalledCliPath(versionOutput: string | null | undefined): string | null {
  if (!versionOutput) {
    return null
  }

  for (const line of versionOutput.split(/\r?\n/)) {
    if (!line.startsWith(CLI_PATH_PREFIX)) {
      continue
    }

    const cliPath = line.slice(CLI_PATH_PREFIX.length).trim()
    return cliPath || null
  }

  return null
}

export function inferRootDirFromPath(candidate: string | null | undefined): string | null {
  if (!candidate || isBareCommand(candidate)) {
    return null
  }

  const resolved = path.resolve(candidate)
  const fileName = path.basename(resolved)

  if (isWrapperBinary(fileName)) {
    const parentDir = path.dirname(resolved)
    if (path.basename(parentDir).toLowerCase() === 'bin') {
      return path.dirname(parentDir)
    }

    return parentDir
  }

  if (isCliBinary(fileName)) {
    const currentDir = path.dirname(resolved)
    const binDir = path.dirname(currentDir)
    if (
      path.basename(currentDir).toLowerCase() === 'current' &&
      path.basename(binDir).toLowerCase() === 'bin'
    ) {
      return path.dirname(binDir)
    }
  }

  return null
}

export function inferRootDir(
  binaryPath: string,
  versionOutput: string | null | undefined
): string | null {
  const reportedCliPath = parseInstalledCliPath(versionOutput)
  return inferRootDirFromPath(reportedCliPath) ?? inferRootDirFromPath(binaryPath)
}

export function isLegacyAppDataDir(dataDir: string | null | undefined): boolean {
  if (!dataDir) {
    return false
  }

  const normalized = path.normalize(dataDir).toLowerCase()
  return LEGACY_APP_DATA_SEGMENTS.some((segment) => normalized.includes(segment))
}

export function resolveDataDir(
  rootDir: string | null,
  configuredDataDir: string | null | undefined
): string | null {
  if (configuredDataDir && !isLegacyAppDataDir(configuredDataDir)) {
    return path.resolve(configuredDataDir)
  }

  if (rootDir) {
    return path.join(path.resolve(rootDir), 'data')
  }

  return null
}
