import { describe, expect, it } from 'vitest'

import { buildStartupIndexRun, needsSetupReminder, shouldShowOnboarding } from './app-state'
import type { BootstrapStatus, ConfigState } from './roughcut-types'

const BASE_CONFIG: ConfigState = {
  media_folders: {
    music_folder: null,
    sfx_folder: null,
    vfx_folder: null,
  },
  onboarding: {
    completed: false,
    configured_count: 0,
    folders: {
      music: false,
      sfx: false,
      vfx: false,
    },
    has_invalid_folders: false,
    invalid_folders: {},
  },
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

const READY_BOOTSTRAP: BootstrapStatus = {
  status: 'ready',
  message: 'ready',
  spacetime: BASE_CONFIG.spacetime,
}

describe('app-state helpers', () => {
  it('shows onboarding only after bootstrap is ready', () => {
    expect(shouldShowOnboarding(READY_BOOTSTRAP, BASE_CONFIG)).toBe(true)
    expect(
      shouldShowOnboarding(
        { ...READY_BOOTSTRAP, status: 'starting' },
        BASE_CONFIG
      )
    ).toBe(false)
    expect(
      shouldShowOnboarding(READY_BOOTSTRAP, {
        ...BASE_CONFIG,
        onboarding: { ...BASE_CONFIG.onboarding, completed: true },
      })
    ).toBe(false)
    expect(
      shouldShowOnboarding(READY_BOOTSTRAP, {
        ...BASE_CONFIG,
        onboarding: {
          ...BASE_CONFIG.onboarding,
          completed: true,
          has_invalid_folders: true,
          invalid_folders: { music: 'Path does not exist: /missing/music' },
        },
      })
    ).toBe(true)
  })

  it('flags setup reminder only when onboarding is complete but categories were skipped', () => {
    expect(needsSetupReminder({ ...BASE_CONFIG.onboarding, completed: true, configured_count: 2 })).toBe(true)
    expect(needsSetupReminder({ ...BASE_CONFIG.onboarding, completed: true, configured_count: 3 })).toBe(false)
    expect(
      needsSetupReminder({
        ...BASE_CONFIG.onboarding,
        completed: true,
        configured_count: 2,
        has_invalid_folders: true,
        invalid_folders: { sfx: 'Path does not exist: /missing/sfx' },
      })
    ).toBe(false)
    expect(needsSetupReminder(BASE_CONFIG.onboarding)).toBe(false)
  })

  it('builds startup indexing jobs from configured folders only', () => {
    const request = buildStartupIndexRun(
      {
        music_folder: '/media/music',
        sfx_folder: null,
        vfx_folder: '/media/vfx',
      },
      42
    )

    expect(request).not.toBeNull()
    expect(request?.id).toBe(42)
    expect(request?.signature).toBe('music:/media/music|vfx:/media/vfx')
    expect(request?.jobs).toEqual([
      {
        id: 'music-initial-42',
        path: '/media/music',
        category: 'music',
        incremental: true,
        source: 'startup',
      },
      {
        id: 'vfx-initial-42',
        path: '/media/vfx',
        category: 'vfx',
        incremental: true,
        source: 'startup',
      },
    ])
  })

  it('returns null when no startup jobs are available', () => {
    expect(
      buildStartupIndexRun(
        {
          music_folder: null,
          sfx_folder: null,
          vfx_folder: null,
        },
        7
      )
    ).toBeNull()
  })
})
