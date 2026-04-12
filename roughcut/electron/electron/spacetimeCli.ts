import path from 'path'

const DEFAULT_HOST = '127.0.0.1'
const DEFAULT_PORT = 3000

export function withRootDir(rootDir: string | null | undefined, args: string[]): string[] {
  if (!rootDir) {
    return [...args]
  }

  return [`--root-dir=${path.resolve(rootDir)}`, ...args]
}

export function buildStartArgs(
  rootDir: string | null | undefined,
  dataDir: string | null | undefined,
  host: string,
  port: number
): string[] {
  const connectHost = host === 'localhost' ? DEFAULT_HOST : host
  const args = withRootDir(rootDir, ['start'])

  if (dataDir) {
    args.push('--data-dir', path.resolve(dataDir))
  }

  if (connectHost !== DEFAULT_HOST || port !== DEFAULT_PORT) {
    args.push('--listen-addr', `${connectHost}:${port}`)
  }

  return args
}
