import { describe, expect, it, vi } from 'vitest'

vi.mock('electron', () => ({
  app: {
    getAppPath: () => '/tmp/roughcut',
  },
}))

import { resolveOperationId } from '../../electron/pythonBridge'

describe('pythonBridge operation IDs', () => {
  it('preserves an explicit operation ID', () => {
    expect(resolveOperationId('index_music_123')).toBe('index_music_123')
  })

  it('creates an operation ID when one is not provided', () => {
    vi.spyOn(Math, 'random').mockReturnValue(0.123456789)

    const operationId = resolveOperationId()

    expect(operationId).toMatch(/^index_\d+_/)
  })
})
