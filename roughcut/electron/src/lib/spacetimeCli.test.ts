import path from 'path'

import { describe, expect, it } from 'vitest'

import { buildStartArgs, withRootDir } from '../../electron/spacetimeCli'

describe('spacetimeCli helpers', () => {
  it('omits root-dir when no install root was resolved', () => {
    expect(withRootDir(null, ['publish', 'roughcut'])).toEqual(['publish', 'roughcut'])
  })

  it('passes root-dir as a single bound flag value', () => {
    expect(withRootDir('C:\\Users\\test\\AppData\\Roaming\\RoughCut\\spacetimedb', ['publish', 'roughcut']))
      .toEqual([
        '--root-dir=C:\\Users\\test\\AppData\\Roaming\\RoughCut\\spacetimedb',
        'publish',
        'roughcut',
      ])
  })

  it('adds listen args only for non-default addresses', () => {
    const runtimeRoot = '/tmp/spacetimedb'
    const dataDir = '/tmp/spacetimedb/data'

    expect(buildStartArgs(runtimeRoot, dataDir, 'localhost', 3000)).toEqual([
      `--root-dir=${path.resolve(runtimeRoot)}`,
      'start',
      '--data-dir',
      path.resolve(dataDir),
    ])

    expect(buildStartArgs(runtimeRoot, dataDir, '0.0.0.0', 4000)).toEqual([
      `--root-dir=${path.resolve(runtimeRoot)}`,
      'start',
      '--data-dir',
      path.resolve(dataDir),
      '--listen-addr',
      '0.0.0.0:4000',
    ])
  })
})
