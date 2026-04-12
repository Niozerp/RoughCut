import path from 'path'

import { describe, expect, it } from 'vitest'

import {
  formatRustToolchainError,
  isMissingWasmTargetError,
  prependPathEntries,
} from '../../electron/spacetimeDependency'

describe('spacetimeDependency helpers', () => {
  it('detects wasm target failures from raw SpacetimeDB output', () => {
    expect(
      isMissingWasmTargetError(
        'Error checking for wasm32 target: program not found Error: wasm32-unknown-unknown target is not installed.'
      )
    ).toBe(true)
  })

  it('formats a missing Rust toolchain error with recovery steps', () => {
    const message = formatRustToolchainError(
      {
        cargoAvailable: false,
        rustupAvailable: false,
        wasmTargetInstalled: false,
      },
      'win32'
    )

    expect(message).toContain('Rust toolchain')
    expect(message).toContain('https://rustup.rs/')
    expect(message).toContain('rustup target add wasm32-unknown-unknown')
  })

  it('deduplicates prepended PATH entries', () => {
    const existingPath = ['/cargo/bin', '/local/bin'].join(path.delimiter)
    const result = prependPathEntries(existingPath, ['/cargo/bin', '/spacetime/bin'])

    expect(result).toBe(['/cargo/bin', '/spacetime/bin', '/local/bin'].join(path.delimiter))
  })
})
