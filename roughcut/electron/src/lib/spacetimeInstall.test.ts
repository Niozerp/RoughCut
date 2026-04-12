import path from 'path'

import { describe, expect, it } from 'vitest'

import { inferRootDir, isLegacyAppDataDir, resolveDataDir } from '../../electron/spacetimeInstall'

describe('spacetimeInstall helpers', () => {
  it('infers the install root from reported cli output', () => {
    const rootDir = path.join('C:', 'Users', 'niozerp', 'AppData', 'Local', 'SpacetimeDB')
    const versionOutput = [
      `spacetime Path: ${path.join(rootDir, 'bin', 'current', 'spacetimedb-cli.exe')}`,
      'Commit: abc123',
      'spacetimedb tool version 2.1.0; spacetimedb-lib version 2.1.0;',
    ].join('\n')

    expect(inferRootDir('spacetime', versionOutput)).toBe(path.resolve(rootDir))
  })

  it('falls back to the standard data dir when the saved path is from the old app-private root', () => {
    const rootDir = path.join('C:', 'Users', 'niozerp', 'AppData', 'Local', 'SpacetimeDB')
    const legacyDataDir = path.join(
      'C:',
      'Users',
      'niozerp',
      'AppData',
      'Roaming',
      'roughcut-electron',
      'spacetimedb'
    )

    expect(resolveDataDir(rootDir, legacyDataDir)).toBe(path.join(path.resolve(rootDir), 'data'))
  })

  it('treats both dashed and spaced legacy app-data roots as legacy locations', () => {
    const dashedLegacyDir = path.join(
      'C:',
      'Users',
      'niozerp',
      'AppData',
      'Roaming',
      'roughcut-electron',
      'spacetimedb',
      'data'
    )
    const spacedLegacyDir = path.join(
      'C:',
      'Users',
      'niozerp',
      'AppData',
      'Roaming',
      'RoughCut Electron',
      'spacetimedb',
      'data'
    )

    expect(isLegacyAppDataDir(dashedLegacyDir)).toBe(true)
    expect(isLegacyAppDataDir(spacedLegacyDir)).toBe(true)
  })
})
