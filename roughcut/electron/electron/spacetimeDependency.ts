import path from 'path'

export interface RustToolchainStatus {
  cargoAvailable: boolean
  rustupAvailable: boolean
  wasmTargetInstalled: boolean
}

const WASM_TARGET = 'wasm32-unknown-unknown'

function installHint(platform: NodeJS.Platform): string {
  return [
    platform === 'win32'
      ? 'Install rustup from https://rustup.rs/ or verify that RoughCut bootstrap completed successfully.'
      : 'Install rustup from https://rustup.rs/ or verify that RoughCut bootstrap completed successfully.',
    `Run: rustup target add ${WASM_TARGET}`,
  ].join('\n')
}

export function isMissingWasmTargetError(message: string | null | undefined): boolean {
  if (!message) {
    return false
  }

  const normalized = message.toLowerCase()
  return (
    normalized.includes(WASM_TARGET) ||
    normalized.includes('error checking for wasm32 target') ||
    normalized.includes('target is not installed')
  )
}

export function formatRustToolchainError(
  status: RustToolchainStatus,
  platform: NodeJS.Platform
): string {
  if (!status.cargoAvailable && !status.rustupAvailable) {
    return [
      'RoughCut could not verify the Rust toolchain required to publish its bundled SpacetimeDB module because Rust is not installed.',
      installHint(platform),
    ].join('\n')
  }

  if (!status.rustupAvailable) {
    return [
      'RoughCut found a Rust compiler, but rustup is missing from the runtime environment.',
      `rustup is required so SpacetimeDB can verify and install the ${WASM_TARGET} target during startup.`,
      installHint(platform),
    ].join('\n')
  }

  if (!status.cargoAvailable) {
    return [
      'RoughCut found rustup, but cargo is not available in the runtime environment.',
      'Make sure the default Rust toolchain is installed and that your Rust bin directory is on PATH.',
      installHint(platform),
    ].join('\n')
  }

  if (!status.wasmTargetInstalled) {
    return [
      `RoughCut can start SpacetimeDB, but the Rust WebAssembly target ${WASM_TARGET} is missing from this environment.`,
      installHint(platform),
    ].join('\n')
  }

  return [
    'RoughCut failed to build the bundled SpacetimeDB Rust module.',
    `Confirm that cargo, rustup, and the ${WASM_TARGET} target are installed, then retry.`,
  ].join('\n')
}

export function prependPathEntries(existingPath: string | undefined, entries: string[]): string {
  const normalizedEntries = entries
    .map((entry) => entry.trim())
    .filter((entry) => entry.length > 0)

  const existingSegments = (existingPath ?? '')
    .split(path.delimiter)
    .map((entry) => entry.trim())
    .filter((entry) => entry.length > 0)

  const seen = new Set<string>()
  const orderedEntries: string[] = []

  for (const entry of [...normalizedEntries, ...existingSegments]) {
    const key = process.platform === 'win32' ? entry.toLowerCase() : entry
    if (seen.has(key)) {
      continue
    }

    seen.add(key)
    orderedEntries.push(entry)
  }

  return orderedEntries.join(path.delimiter)
}
