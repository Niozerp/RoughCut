/**
 * Python Backend Bridge for Electron
 *
 * Handles spawning Python processes and communicating with the RoughCut backend.
 * Used for indexing operations, asset queries, and other backend tasks.
 */

import { spawn, execSync, spawnSync } from 'child_process'
import path from 'path'
import { fileURLToPath } from 'url'
import fs from 'fs'
import os from 'os'
import { app } from 'electron'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)

// Track active Python processes
const activeProcesses = new Map<string, { proc: any; tmpFile: string; command: string }>()
const poetryBootstrapPromises = new Map<string, Promise<{ poetryPythonPath: string | null; error?: string }>>()
const pythonRuntimePromises = new Map<string, Promise<PythonRuntimeState>>()
const pythonRuntimeCache = new Map<string, PythonRuntimeState>()

type PythonEnvironment = {
  roughcutPath: string | null
  pythonPath: string
  projectRoot: string | null
  usePoetry: boolean
}

type PoetryCommand = {
  command: string
  args: string[]
  description: string
}

type PythonDependency = {
  installName: string
  importName: string
}

type PythonRuntimeState = {
  roughcutPath: string
  pythonPath: string
  projectRoot: string | null
  usePoetry: boolean
}

// Required Python dependencies
const REQUIRED_DEPENDENCIES: PythonDependency[] = [
  { installName: 'aiofiles', importName: 'aiofiles' },
  { installName: 'pydantic', importName: 'pydantic' },
  { installName: 'pyyaml', importName: 'yaml' },
  { installName: 'cryptography', importName: 'cryptography' },
  { installName: 'openai', importName: 'openai' },
  { installName: 'notion-client', importName: 'notion_client' },
  { installName: 'websockets', importName: 'websockets' },
]

const REQUIRED_DEPENDENCY_NAMES = REQUIRED_DEPENDENCIES.map(({ installName }) => installName)

const POETRY_STALE_LOCK_MESSAGE = 'pyproject.toml changed significantly since poetry.lock was last generated'
let cachedPythonEnvironment: PythonEnvironment | null = null

// Mapping of commands to their Python script files
const COMMAND_SCRIPT_MAP: Record<string, string> = {
  'index': 'indexing.py',
  'reindex': 'indexing.py',
  'query': 'query.py',
  'purge_category': 'config.py',
  'status': 'config.py',
  'config_state': 'config.py',
  'save_media_folders': 'config.py',
  'set_onboarding_complete': 'config.py',
  'save_spacetime_runtime': 'config.py',
  'resolve_status': 'resolve.py',
  'resolve_connect': 'resolve.py',
  'resolve_disconnect': 'resolve.py',
  'resolve_send_timeline': 'resolve.py',
}

export function resolveOperationId(operationId?: string): string {
  return operationId || `index_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
}

/**
 * Get the path to the Python scripts directory
 */
function getPythonScriptsPath(): string {
  // Check multiple locations for the scripts
  const possiblePaths = [
    // Packaged app locations
    path.join(app.getAppPath(), '..', 'python'),
    path.join(app.getAppPath(), '..', '..', 'python'),
    path.join(app.getAppPath(), 'python'),
    path.join(process.resourcesPath || '', 'python'),
    // Development locations
    path.join(__dirname, '..', 'python'),
    path.join(__dirname, 'python'),
    path.join(process.cwd(), 'python'),
  ]

  for (const testPath of possiblePaths) {
    if (fs.existsSync(testPath)) {
      const commonPath = path.join(testPath, 'common.py')
      if (fs.existsSync(commonPath)) {
        return testPath
      }
    }
  }

  // Fallback: return the most likely location
  return path.join(__dirname, '..', 'python')
}

/**
 * Find the Python executable, roughcut module, and project root
 */
function findPythonEnvironment(): PythonEnvironment {
  // Get Python command based on platform
  const pythonPath = process.platform === 'win32' ? 'python' : 'python3'

  // Possible roughcut module locations (relative to electron folder)
  const roughcutPaths = [
    // Packaged app locations
    path.join(app.getAppPath(), '..', 'roughcut', 'src'),
    path.join(app.getAppPath(), '..', '..', 'roughcut', 'src'),
    path.join(app.getAppPath(), 'roughcut', 'src'),
    path.join(process.resourcesPath || '', 'roughcut', 'src'),
    // Development locations
    path.join(__dirname, '..', '..', 'src'),
    path.join(__dirname, '..', '..', '..', 'src'),
    path.join(process.cwd(), 'src'),
    path.join(app.getAppPath(), 'src'),
  ]

  // Also find project root for Poetry
  const projectRoots = [
    path.join(app.getAppPath(), '..', 'roughcut'),
    path.join(app.getAppPath(), '..', '..', 'roughcut'),
    path.join(app.getAppPath(), 'roughcut'),
    path.join(__dirname, '..', '..', '..'),
    path.join(__dirname, '..', '..'),
    path.join(process.cwd()),
    app.getAppPath(),
  ]

  console.log('[PythonBridge] Searching for roughcut module in locations:')
  roughcutPaths.forEach(p => console.log('  -', p))

  // Find existing roughcut path
  let roughcutPath: string | null = null
  for (const testPath of roughcutPaths) {
    const initFile = path.join(testPath, 'roughcut', '__init__.py')
    const packageDir = path.join(testPath, 'roughcut')

    if (fs.existsSync(initFile)) {
      roughcutPath = testPath
      console.log('[PythonBridge] Found roughcut at:', roughcutPath)
      break
    } else if (fs.existsSync(packageDir) && fs.statSync(packageDir).isDirectory()) {
      roughcutPath = testPath
      console.log('[PythonBridge] Found roughcut package at:', roughcutPath)
      break
    }
  }

  // Find project root and check for Poetry
  let projectRoot: string | null = null
  let usePoetry = false

  for (const testPath of projectRoots) {
    const pyprojectPath = path.join(testPath, 'pyproject.toml')
    const poetryLockPath = path.join(testPath, 'poetry.lock')

    if (fs.existsSync(pyprojectPath)) {
      projectRoot = testPath
      console.log('[PythonBridge] Found project root at:', projectRoot)

      // Check if Poetry is managing this project
      if (fs.existsSync(poetryLockPath)) {
        usePoetry = true
        console.log('[PythonBridge] Poetry lock file found, using Poetry')
      }
      break
    }
  }

  if (!roughcutPath) {
    console.error('[PythonBridge] Could not find roughcut module')
  }

  return { roughcutPath, pythonPath, projectRoot, usePoetry }
}

function getPythonEnvironment(): PythonEnvironment {
  if (!cachedPythonEnvironment) {
    cachedPythonEnvironment = findPythonEnvironment()
  }

  return cachedPythonEnvironment
}

function getPythonRuntimeKey(environment: PythonEnvironment): string {
  return environment.projectRoot
    ? `poetry:${environment.projectRoot}`
    : `python:${environment.pythonPath}:${environment.roughcutPath ?? 'missing'}`
}

/**
 * Get the Poetry virtual environment Python path
 */
function getPoetryVenvPython(projectRoot: string, pythonCommand: string): string | null {
  try {
    console.log('[PythonBridge] Searching for Poetry venv in project:', projectRoot)

    // Common Poetry venv locations (in project)
    const venvPaths = [
      path.join(projectRoot, '.venv', 'Scripts', 'python.exe'),  // Windows
      path.join(projectRoot, '.venv', 'bin', 'python'),  // Unix
      path.join(projectRoot, '.venv', 'bin', 'python3'),
    ]

    // Check common venv locations first
    for (const venvPath of venvPaths) {
      console.log('[PythonBridge] Checking venv path:', venvPath)
      if (fs.existsSync(venvPath)) {
        console.log('[PythonBridge] Found Poetry venv at:', venvPath)
        return venvPath
      }
    }

    // Try to get venv path from poetry env info
    const poetryCommand = findPoetry(pythonCommand)
    if (poetryCommand) {
      try {
        console.log(`[PythonBridge] Trying to get venv path from ${poetryCommand.description} env info...`)
        const result = spawnSync(poetryCommand.command, [...poetryCommand.args, 'env', 'info', '--path'], {
          cwd: projectRoot,
          encoding: 'utf-8',
          timeout: 5000,
          windowsHide: true,
        })

        if (result.status === 0) {
          const venvRoot = result.stdout.trim()

          if (venvRoot) {
            console.log('[PythonBridge] Poetry env info returned:', venvRoot)
            const poetryVenvPython = process.platform === 'win32'
              ? path.join(venvRoot, 'Scripts', 'python.exe')
              : path.join(venvRoot, 'bin', 'python')

            if (fs.existsSync(poetryVenvPython)) {
              console.log('[PythonBridge] Poetry venv from poetry env info:', poetryVenvPython)
              return poetryVenvPython
            } else {
              console.log('[PythonBridge] Poetry env info path exists but Python not found at:', poetryVenvPython)
            }
          }
        } else {
          console.log('[PythonBridge] poetry env info command failed (venv may not exist yet)')
        }
      } catch (e) {
        console.log('[PythonBridge] poetry env info command failed (venv may not exist yet)')
      }
    } else {
      console.log('[PythonBridge] Poetry command unavailable for env info lookup')
    }

    // Check standard poetry cache locations - look for roughcut-named venvs
    const homeDir = os.homedir()
    const poetryCacheBase = process.platform === 'win32'
      ? path.join(homeDir, 'AppData', 'Local', 'pypoetry', 'Cache', 'virtualenvs')
      : process.platform === 'darwin'
        ? path.join(homeDir, 'Library', 'Caches', 'pypoetry', 'virtualenvs')
        : path.join(homeDir, '.cache', 'pypoetry', 'virtualenvs')

    console.log('[PythonBridge] Checking Poetry cache at:', poetryCacheBase)

    if (fs.existsSync(poetryCacheBase)) {
      try {
        const entries = fs.readdirSync(poetryCacheBase)
        // Look for roughcut-related venvs
        const roughcutVenvs = entries.filter(e =>
          e.toLowerCase().includes('roughcut') ||
          e.toLowerCase().includes('rough-cut')
        )

        for (const venvName of roughcutVenvs) {
          const venvPath = process.platform === 'win32'
            ? path.join(poetryCacheBase, venvName, 'Scripts', 'python.exe')
            : path.join(poetryCacheBase, venvName, 'bin', 'python')

          if (fs.existsSync(venvPath)) {
            console.log('[PythonBridge] Found Poetry venv in cache:', venvPath)
            return venvPath
          }
        }

        // If no roughcut venv found, try the most recent venv
        if (entries.length > 0) {
          // Get most recently modified
          let newestVenv = entries[0]
          let newestTime = 0

          for (const entry of entries) {
            const fullPath = path.join(poetryCacheBase, entry)
            try {
              const stats = fs.statSync(fullPath)
              if (stats.mtimeMs > newestTime) {
                newestTime = stats.mtimeMs
                newestVenv = entry
              }
            } catch (e) {}
          }

          const venvPath = process.platform === 'win32'
            ? path.join(poetryCacheBase, newestVenv, 'Scripts', 'python.exe')
            : path.join(poetryCacheBase, newestVenv, 'bin', 'python')

          if (fs.existsSync(venvPath)) {
            console.log('[PythonBridge] Using most recent Poetry venv:', venvPath)
            return venvPath
          }
        }
      } catch (e) {
        console.log('[PythonBridge] Error reading Poetry cache:', e)
      }
    }

    return null
  } catch (e) {
    return null
  }
}

/**
 * Find the poetry executable
 */
function getPoetryExecutableCandidates(): string[] {
  const homeDir = os.homedir()
  const possiblePaths: string[] = [
    'poetry',  // In PATH
    path.join(homeDir, '.local', 'bin', 'poetry'),  // Linux
    path.join(homeDir, '.poetry', 'bin', 'poetry'),  // Old poetry install
  ]

  // Windows-specific paths - pip --user installs
  if (process.platform === 'win32') {
    const appData = process.env.APPDATA || path.join(homeDir, 'AppData', 'Roaming')
    const localAppData = process.env.LOCALAPPDATA || path.join(homeDir, 'AppData', 'Local')

    const scriptDirs = new Set<string>([
      path.join(appData, 'Python', 'Scripts'),
      path.join(homeDir, 'AppData', 'Roaming', 'Python', 'Scripts'),
    ])

    const pythonInstallRoots = [
      path.join(appData, 'Python'),
      path.join(localAppData, 'Programs', 'Python'),
    ]

    for (const root of pythonInstallRoots) {
      if (!fs.existsSync(root)) {
        continue
      }

      try {
        for (const entry of fs.readdirSync(root, { withFileTypes: true })) {
          if (entry.isDirectory()) {
            scriptDirs.add(path.join(root, entry.name, 'Scripts'))
          }
        }
      } catch (e) {
        console.log('[PythonBridge] Error enumerating Poetry script directory candidates:', root, e)
      }
    }

    for (const scriptDir of scriptDirs) {
      possiblePaths.push(path.join(scriptDir, 'poetry.exe'))
      possiblePaths.push(path.join(scriptDir, 'poetry'))
    }

    possiblePaths.push(path.join(localAppData, 'Microsoft', 'WindowsApps', 'poetry.exe'))
  }

  return Array.from(new Set(possiblePaths))
}

function findPoetry(pythonCommand: string): PoetryCommand | null {
  try {
    const poetryModuleCheck = spawnSync(pythonCommand, ['-m', 'poetry', '--version'], {
      encoding: 'utf-8',
      timeout: 5000,
      windowsHide: true,
    })

    if (poetryModuleCheck.status === 0) {
      console.log('[PythonBridge] Found poetry via Python module:', `${pythonCommand} -m poetry`)
      return {
        command: pythonCommand,
        args: ['-m', 'poetry'],
        description: `${pythonCommand} -m poetry`,
      }
    }
  } catch (e) {
    console.log('[PythonBridge] python -m poetry check failed')
  }

  const possiblePaths = getPoetryExecutableCandidates()
  for (const poetryPath of possiblePaths) {
    console.log('[PythonBridge] Checking for poetry at:', poetryPath)

    if (poetryPath === 'poetry') {
      // Try to spawn just 'poetry' to check if it's in PATH
      try {
        execSync('poetry --version', { timeout: 5000 })
        console.log('[PythonBridge] Found poetry in PATH')
        return {
          command: 'poetry',
          args: [],
          description: 'poetry',
        }
      } catch (e) {
        continue
      }
    } else if (fs.existsSync(poetryPath)) {
      console.log('[PythonBridge] Found poetry at:', poetryPath)
      return {
        command: poetryPath,
        args: [],
        description: poetryPath,
      }
    }
  }

  console.log('[PythonBridge] Poetry not found')
  return null
}

/**
 * Install Poetry using pip
 */
async function installPoetry(pythonCommand: string): Promise<{ success: boolean; poetryCommand: PoetryCommand | null; error?: string }> {
  return new Promise((resolve) => {
    console.log('[PythonBridge] ============================================')
    console.log('[PythonBridge] Installing Poetry using pip...')
    console.log('[PythonBridge] ============================================')

    const shellOption = process.platform === 'win32' ? true : false
    const proc = spawn(pythonCommand, ['-m', 'pip', 'install', 'poetry', '--user'], {
      shell: shellOption,
      windowsHide: true,
      timeout: 5 * 60 * 1000  // 5 minutes
    })

    let stdout = ''
    let stderr = ''

    proc.stdout.on('data', (data: Buffer) => {
      const line = data.toString()
      stdout += line
      console.log('[Poetry install]', line.substring(0, 200))
    })

    proc.stderr.on('data', (data: Buffer) => {
      const line = data.toString()
      stderr += line
      console.error('[Poetry install stderr]', line.substring(0, 200))
    })

    proc.on('close', (code: number | null) => {
      console.log('[PythonBridge] Poetry pip install completed with code:', code)

      if (code === 0) {
        const poetryCommand = findPoetry(pythonCommand)

        if (poetryCommand) {
          console.log('[PythonBridge] Poetry installed successfully at:', poetryCommand.description)
          resolve({ success: true, poetryCommand })
          return
        }

        console.error('[PythonBridge] ERROR: Poetry was installed but could not be found')
        resolve({
          success: false,
          poetryCommand: null,
          error: `Poetry was installed for ${pythonCommand} but could not be invoked afterward from DaVinci Resolve.`
        })
      } else {
        resolve({
          success: false,
          poetryCommand: null,
          error: `Failed to install Poetry (exit code ${code}). Error: ${stderr || stdout || 'Unknown error'}`
        })
      }
    })

    proc.on('error', (err: Error) => {
      console.error('[PythonBridge] Failed to install Poetry:', err)
      resolve({
        success: false,
        poetryCommand: null,
        error: `Failed to install Poetry: ${err.message}`
      })
    })
  })
}

async function executePoetryCommand(
  poetryCommand: PoetryCommand,
  projectRoot: string,
  args: string[],
  label: string
): Promise<{ success: boolean; code: number | null; stdout: string; stderr: string; hasOutput: boolean; error?: string }> {
  return new Promise((resolve) => {
    const shellOption = process.platform === 'win32' ? true : false
    const proc = spawn(poetryCommand.command, [...poetryCommand.args, ...args], {
      cwd: projectRoot,
      shell: shellOption,
      windowsHide: true,
      timeout: 15 * 60 * 1000,
    })

    let stdout = ''
    let stderr = ''
    let hasOutput = false

    proc.stdout.on('data', (data: Buffer) => {
      hasOutput = true
      const line = data.toString()
      stdout += line
      console.log(`[${label}]`, line.substring(0, 200))
    })

    proc.stderr.on('data', (data: Buffer) => {
      hasOutput = true
      const line = data.toString()
      stderr += line
      console.error(`[${label} stderr]`, line.substring(0, 200))
    })

    proc.on('close', (code: number | null) => {
      resolve({
        success: code === 0,
        code,
        stdout,
        stderr,
        hasOutput,
      })
    })

    proc.on('error', (err: Error) => {
      console.error(`[PythonBridge] Failed to spawn ${label.toLowerCase()} command:`, err)
      resolve({
        success: false,
        code: null,
        stdout,
        stderr,
        hasOutput,
        error: err.message,
      })
    })
  })
}

async function runPoetryInstall(projectRoot: string, pythonCommand: string): Promise<{ success: boolean; error?: string }> {
  return new Promise(async (resolve) => {
    console.log('[PythonBridge] ============================================')
    console.log('[PythonBridge] Starting poetry install')
    console.log('[PythonBridge] Project root:', projectRoot)
    console.log('[PythonBridge] Checking if pyproject.toml exists...')

    // Verify project root exists and has pyproject.toml
    const pyprojectPath = path.join(projectRoot, 'pyproject.toml')
    if (!fs.existsSync(pyprojectPath)) {
      console.error('[PythonBridge] ERROR: pyproject.toml not found at:', pyprojectPath)
      resolve({
        success: false,
        error: `pyproject.toml not found in ${projectRoot}. Cannot run poetry install.`
      })
      return
    }

    // Find poetry executable - install if not found
    let poetryCommand = findPoetry(pythonCommand)

    if (!poetryCommand) {
      console.log('[PythonBridge] Poetry not found. Attempting to install Poetry automatically...')
      const poetryInstallResult = await installPoetry(pythonCommand)

      if (!poetryInstallResult.success) {
        console.error('[PythonBridge] ERROR: Failed to install Poetry')
        resolve({
          success: false,
          error: poetryInstallResult.error || `Failed to install Poetry automatically. Please install Poetry manually with: pip install poetry`
        })
        return
      }

      poetryCommand = poetryInstallResult.poetryCommand
      console.log('[PythonBridge] Poetry installed successfully at:', poetryCommand?.description)
    }

    if (!poetryCommand) {
      resolve({
        success: false,
        error: 'Poetry command is unavailable after installation. This should not happen.'
      })
      return
    }

    console.log('[PythonBridge] Found poetry at:', poetryCommand.description)
    console.log('[PythonBridge] Spawning poetry install...')
    console.log('[PythonBridge] Working directory:', projectRoot)

    const formatPoetryFailure = (operation: string, result: { code: number | null; stdout: string; stderr: string; hasOutput: boolean; error?: string }): string => {
      if (result.error) {
        return `Cannot run ${operation}: ${result.error}. Try: ${pythonCommand} -m pip install poetry --user`
      }

      let errorMsg = `${operation} failed (code ${result.code})`
      if (!result.hasOutput) {
        errorMsg += ': No output from poetry command. Is Poetry installed and in PATH?'
      } else if (result.stderr) {
        errorMsg += `: ${result.stderr.substring(0, 300)}`
      } else if (result.stdout) {
        errorMsg += `: ${result.stdout.substring(0, 300)}`
      }

      return errorMsg
    }

    let installResult = await executePoetryCommand(
      poetryCommand,
      projectRoot,
      ['install', '--no-interaction'],
      'Poetry install'
    )
    console.log('[PythonBridge] Poetry install process closed with code:', installResult.code)

    if (!installResult.success) {
      console.error('[PythonBridge] Poetry install failed with code:', installResult.code)
      console.error('[PythonBridge] stdout:', installResult.stdout.substring(0, 500))
      console.error('[PythonBridge] stderr:', installResult.stderr.substring(0, 500))

      const combinedOutput = `${installResult.stdout}\n${installResult.stderr}`
      if (combinedOutput.includes(POETRY_STALE_LOCK_MESSAGE)) {
        console.log('[PythonBridge] poetry.lock is out of date, refreshing lock file before retrying install...')

        const lockResult = await executePoetryCommand(
          poetryCommand,
          projectRoot,
          ['lock', '--no-interaction'],
          'Poetry lock'
        )
        console.log('[PythonBridge] Poetry lock process closed with code:', lockResult.code)

        if (!lockResult.success) {
          console.error('[PythonBridge] Poetry lock refresh failed with code:', lockResult.code)
          console.error('[PythonBridge] lock stdout:', lockResult.stdout.substring(0, 500))
          console.error('[PythonBridge] lock stderr:', lockResult.stderr.substring(0, 500))
          resolve({ success: false, error: formatPoetryFailure('Poetry lock refresh', lockResult) })
          return
        }

        console.log('[PythonBridge] Poetry lock refresh completed successfully, retrying install...')
        installResult = await executePoetryCommand(
          poetryCommand,
          projectRoot,
          ['install', '--no-interaction'],
          'Poetry install'
        )
        console.log('[PythonBridge] Poetry install retry closed with code:', installResult.code)
      }
    }

    if (installResult.success) {
      console.log('[PythonBridge] Poetry install completed successfully')
      resolve({ success: true })
      return
    }

    console.error('[PythonBridge] Poetry install failed with code:', installResult.code)
    console.error('[PythonBridge] stdout:', installResult.stdout.substring(0, 500))
    console.error('[PythonBridge] stderr:', installResult.stderr.substring(0, 500))
    resolve({ success: false, error: formatPoetryFailure('Poetry install', installResult) })
  })
}

async function bootstrapPoetryEnvironment(
  projectRoot: string,
  pythonCommand: string,
  forceInstall = false
): Promise<{ poetryPythonPath: string | null; error?: string }> {
  const existingPromise = poetryBootstrapPromises.get(projectRoot)
  if (existingPromise) {
    console.log('[PythonBridge] Awaiting active Poetry bootstrap for project:', projectRoot)
    return existingPromise
  }

  const bootstrapPromise = (async () => {
    const existingVenvPython = getPoetryVenvPython(projectRoot, pythonCommand)
    if (existingVenvPython && !forceInstall) {
      return { poetryPythonPath: existingVenvPython }
    }

    if (existingVenvPython && forceInstall) {
      console.log('[PythonBridge] Poetry venv exists but dependencies are missing, will attempt to repair it')
    } else {
      console.log('[PythonBridge] Poetry project detected but venv not found, will attempt to create it')
    }
    console.log('[PythonBridge] ============================================')
    console.log('[PythonBridge] Running Poetry install to ensure dependencies are available...')
    console.log('[PythonBridge] Project root:', projectRoot)
    console.log('[PythonBridge] ============================================')

    const installResult = await runPoetryInstall(projectRoot, pythonCommand)
    if (!installResult.success) {
      return {
        poetryPythonPath: null,
        error: installResult.error || 'Poetry install failed for an unknown reason.',
      }
    }

    console.log('[PythonBridge] Poetry install completed, locating virtual environment...')
    const installedVenvPython = getPoetryVenvPython(projectRoot, pythonCommand)

    if (!installedVenvPython) {
      return {
        poetryPythonPath: null,
        error: 'Poetry install succeeded but the virtual environment Python executable could not be found afterward.',
      }
    }

    return { poetryPythonPath: installedVenvPython }
  })()

  poetryBootstrapPromises.set(projectRoot, bootstrapPromise)

  try {
    return await bootstrapPromise
  } finally {
    poetryBootstrapPromises.delete(projectRoot)
  }
}

/**
 * Check if Python dependencies are installed
 */
async function checkDependencies(pythonPath: string): Promise<{ allInstalled: boolean; missing: string[] }> {
  return new Promise((resolve) => {
    const dependencyPairs = REQUIRED_DEPENDENCIES.map(
      ({ installName, importName }) => `('${installName}', '${importName}')`
    ).join(', ')

    const checkScript = `
import sys
missing = []
for install_name, import_name in [${dependencyPairs}]:
    try:
        __import__(import_name)
    except ImportError:
        missing.append(install_name)
if missing:
    print(f"MISSING:{','.join(missing)}")
else:
    print("OK:All dependencies installed")
`
    const tmpFile = path.join(os.tmpdir(), `roughcut_deps_${Date.now()}.py`)
    fs.writeFileSync(tmpFile, checkScript)

    const proc = spawn(pythonPath, [tmpFile], {
      timeout: 10000,
      windowsHide: true,
    })
    let output = ''

    proc.stdout.on('data', (data: Buffer) => {
      output += data.toString()
    })

    proc.on('close', () => {
      try { fs.unlinkSync(tmpFile) } catch {}

      const lines = output.split(/\r?\n/)
      for (const line of lines) {
        if (line.startsWith('MISSING:')) {
          const missing = line.substring(8).split(',').map(dep => dep.trim()).filter(Boolean)
          resolve({ allInstalled: false, missing })
          return
        } else if (line.startsWith('OK:')) {
          resolve({ allInstalled: true, missing: [] })
          return
        }
      }
      resolve({ allInstalled: false, missing: REQUIRED_DEPENDENCY_NAMES })
    })

    proc.on('error', () => {
      resolve({ allInstalled: false, missing: REQUIRED_DEPENDENCY_NAMES })
    })
  })
}

function buildDependencyErrorMessage(
  missing: string[],
  projectRoot: string | null,
  usePoetry: boolean,
  actualPythonPath: string,
  pythonPath: string,
  poetryBootstrapError?: string
): string {
  const missingList = missing.join(', ')

  let diagInfo = `\n\nDIAGNOSTIC INFO:\n`
  diagInfo += `Project root: ${projectRoot || 'NOT FOUND'}\n`
  diagInfo += `Using Poetry: ${usePoetry}\n`
  diagInfo += `Python path: ${actualPythonPath}\n`

  if (projectRoot) {
    const pyprojectExists = fs.existsSync(path.join(projectRoot, 'pyproject.toml'))
    diagInfo += `pyproject.toml exists: ${pyprojectExists}\n`
  }

  if (usePoetry && projectRoot) {
    const repoRoot = path.dirname(projectRoot)
    const installCommand = process.platform === 'win32'
      ? `  cd "${repoRoot}"\n  .\\install.bat`
      : `  cd "${repoRoot}"\n  ./install.sh`

    let errorMsg = `Missing required Python dependencies: ${missingList}\n\n`
    errorMsg += poetryBootstrapError
      ? `Poetry install or repair failed: ${poetryBootstrapError}\n\n`
      : `Poetry install or repair failed or is not available.\n\n`
    errorMsg += `To fix this, try one of the following:\n\n`
    errorMsg += `Option 1 - Re-run the standalone installer:\n`
    errorMsg += `${installCommand}\n\n`
    errorMsg += `Option 2 - Run manually in terminal:\n`
    errorMsg += `  cd "${projectRoot}"\n`
    errorMsg += `  ${pythonPath} -m poetry install\n\n`
    errorMsg += `Option 3 - Install with pip:\n`
    errorMsg += `  pip install ${missingList}`
    errorMsg += diagInfo
    return errorMsg
  }

  let errorMsg = `Missing required Python dependencies: ${missingList}\n\n`
  errorMsg += `Install with:\n`
  errorMsg += `pip install ${missingList}`
  errorMsg += diagInfo
  return errorMsg
}

async function ensurePythonRuntime(environment: PythonEnvironment): Promise<PythonRuntimeState> {
  const runtimeKey = getPythonRuntimeKey(environment)
  const cachedRuntime = pythonRuntimeCache.get(runtimeKey)
  if (cachedRuntime) {
    return cachedRuntime
  }

  const existingPromise = pythonRuntimePromises.get(runtimeKey)
  if (existingPromise) {
    console.log('[PythonBridge] Awaiting active Python runtime validation:', runtimeKey)
    return existingPromise
  }

  const runtimePromise = (async () => {
    const { roughcutPath, pythonPath, projectRoot, usePoetry } = environment

    if (!roughcutPath) {
      throw new Error('Could not find RoughCut Python module.')
    }

    let actualPythonPath = pythonPath
    let poetryPythonPath: string | null = null
    let poetryBootstrapError: string | undefined

    if (usePoetry && projectRoot) {
      const bootstrapResult = await bootstrapPoetryEnvironment(projectRoot, pythonPath)
      poetryPythonPath = bootstrapResult.poetryPythonPath
      poetryBootstrapError = bootstrapResult.error

      if (poetryPythonPath) {
        actualPythonPath = poetryPythonPath
        console.log('[PythonBridge] Using Poetry virtual environment Python:', actualPythonPath)
      } else {
        console.error('[PythonBridge] Poetry bootstrap failed:', poetryBootstrapError)
      }
    }

    console.log('[PythonBridge] Checking Python dependencies...')
    console.log('[PythonBridge] Using Python:', actualPythonPath)
    console.log('[PythonBridge] Project root:', projectRoot)
    console.log('[PythonBridge] Use Poetry:', usePoetry)
    if (poetryPythonPath) {
      console.log('[PythonBridge] Poetry venv Python:', poetryPythonPath)
    }

    let depsCheck = await checkDependencies(actualPythonPath)
    console.log('[PythonBridge] Dependency check result:', depsCheck)

    if (!depsCheck.allInstalled && usePoetry && projectRoot) {
      console.log('[PythonBridge] Poetry project has missing dependencies, attempting repair with poetry install...')
      console.log('[PythonBridge] Missing:', depsCheck.missing.join(', '))

      const repairResult = await bootstrapPoetryEnvironment(projectRoot, pythonPath, true)
      poetryPythonPath = repairResult.poetryPythonPath
      poetryBootstrapError = repairResult.error

      if (poetryPythonPath) {
        actualPythonPath = poetryPythonPath
        console.log('[PythonBridge] Repaired Poetry environment Python:', actualPythonPath)
        depsCheck = await checkDependencies(actualPythonPath)
        console.log('[PythonBridge] Dependency check after Poetry repair:', depsCheck)
      } else if (poetryBootstrapError) {
        console.error('[PythonBridge] Poetry repair failed:', poetryBootstrapError)
      }
    }

    if (!depsCheck.allInstalled && usePoetry && projectRoot && poetryPythonPath) {
      console.error('[PythonBridge] Dependencies still missing after Poetry install')
      console.error('[PythonBridge] This may indicate a corrupted Poetry environment')
    } else if (!depsCheck.allInstalled && !usePoetry) {
      console.log('[PythonBridge] Not a Poetry project, skipping auto-install')
    } else if (!depsCheck.allInstalled && !projectRoot) {
      console.log('[PythonBridge] No project root found, cannot auto-install')
    }

    if (!depsCheck.allInstalled) {
      const errorMsg = buildDependencyErrorMessage(
        depsCheck.missing,
        projectRoot,
        usePoetry,
        actualPythonPath,
        pythonPath,
        poetryBootstrapError
      )

      console.error('[PythonBridge]', errorMsg)
      throw new Error(errorMsg)
    }

    console.log('[PythonBridge] All dependencies are installed')
    return {
      roughcutPath,
      pythonPath: actualPythonPath,
      projectRoot,
      usePoetry,
    }
  })()

  pythonRuntimePromises.set(runtimeKey, runtimePromise)

  try {
    const runtime = await runtimePromise
    pythonRuntimeCache.set(runtimeKey, runtime)
    return runtime
  } finally {
    pythonRuntimePromises.delete(runtimeKey)
  }
}

/**
 * Get the path to the Python script for a given command
 */
function getScriptPathForCommand(command: string): string {
  const scriptName = COMMAND_SCRIPT_MAP[command]
  if (!scriptName) {
    throw new Error(`Unknown command: ${command}. Available commands: ${Object.keys(COMMAND_SCRIPT_MAP).join(', ')}`)
  }

  const scriptsPath = getPythonScriptsPath()
  const scriptPath = path.join(scriptsPath, scriptName)

  if (!fs.existsSync(scriptPath)) {
    throw new Error(`Python script not found: ${scriptPath}. Please ensure the scripts are properly installed.`)
  }

  return scriptPath
}

/**
 * Execute a Python command
 */
export async function executePythonCommand(
  command: string,
  params: Record<string, any> = {},
  onProgress: ((progress: any) => void) | null = null,
  onLog: ((log: { type: 'stdout' | 'stderr', message: string }) => void) | null = null,
  onStreamingAsset: ((asset: any) => void) | null = null,
  operationId?: string
): Promise<any> {
  const environment = getPythonEnvironment()
  const runtime = await ensurePythonRuntime(environment)
  const { roughcutPath, pythonPath: actualPythonPath } = runtime

  // Get the script path for this command
  let scriptPath: string
  try {
    scriptPath = getScriptPathForCommand(command)
  } catch (error: any) {
    console.error(`[PythonBridge] Script path error: ${error.message}`)
    throw error
  }

  // Build command arguments
  const scriptArgs = [
    '--roughcut-path', roughcutPath,
    '--params', JSON.stringify(params),
  ]

  // For multi-command scripts, pass the specific command
  if (['purge_category', 'status', 'config_state', 'save_media_folders',
       'set_onboarding_complete', 'save_spacetime_runtime'].includes(command)) {
    scriptArgs.push('--command', command)
  }

  // For resolve commands
  if (['resolve_status', 'resolve_connect', 'resolve_disconnect',
       'resolve_send_timeline'].includes(command)) {
    scriptArgs.push('--command', command)
  }

  // For reindex, add the reindex flag to params
  if (command === 'reindex') {
    const reindexParams = { ...params, reindex: true }
    // Replace the params argument
    const paramsIndex = scriptArgs.indexOf('--params')
    if (paramsIndex !== -1 && paramsIndex + 1 < scriptArgs.length) {
      scriptArgs[paramsIndex + 1] = JSON.stringify(reindexParams)
    }
  }

  return new Promise((resolve, reject) => {
    console.log(`[PythonBridge] ============================================`)
    console.log(`[PythonBridge] Spawning Python: ${actualPythonPath}`)
    console.log(`[PythonBridge] Command: ${command}`)
    console.log(`[PythonBridge] Script: ${scriptPath}`)
    console.log(`[PythonBridge] Roughcut path: ${roughcutPath}`)
    console.log(`[PythonBridge] ============================================`)

    const proc = spawn(actualPythonPath, [scriptPath, ...scriptArgs], {
      env: {
        ...process.env,
        PYTHONPATH: roughcutPath
      }
    })

    const processId = resolveOperationId(operationId)
    // Note: We don't have a temp file anymore, but we need to track the process
    // Use the script path as a placeholder for tmpFile in the tracking structure
    activeProcesses.set(processId, { proc, tmpFile: scriptPath, command })

    let result: any = null
    let errorOutput = ''
    let hasOutput = false
    let lastIndexingLog = ''  // Track last [INDEXING_LOG] for crash diagnostics

    proc.stdout.on('data', (data: Buffer) => {
      hasOutput = true
      const lines = data.toString().split('\n')
      for (const line of lines) {
        const trimmed = line.trim()
        if (trimmed.startsWith('PROGRESS:')) {
          try {
            const progress = JSON.parse(trimmed.substring(9))
            console.log('[PythonBridge] Progress:', progress.message || progress.operation)
            if (onProgress) {
              onProgress(progress)
            }
          } catch (e: any) {
            console.log('[PythonBridge] Progress parse error:', e.message)
          }
        } else if (trimmed.startsWith('STREAM_ASSET:')) {
          // Real-time asset streaming for immediate GUI display
          try {
            const asset = JSON.parse(trimmed.substring(13))
            console.log('[PythonBridge] Streaming asset:', asset.file_name || asset.id)
            if (onStreamingAsset) {
              onStreamingAsset(asset)
            }
          } catch (e: any) {
            console.log('[PythonBridge] Streaming asset parse error:', e.message)
          }
        } else if (trimmed.startsWith('RESULT:')) {
          try {
            result = JSON.parse(trimmed.substring(7))
            console.log('[PythonBridge] Got result with', result.indexed_count !== undefined ? result.indexed_count : result.total_count, 'items')
          } catch (e: any) {
            console.log('[PythonBridge] Result parse error:', e.message)
          }
        } else if (trimmed.startsWith('ERROR:')) {
          errorOutput = trimmed.substring(6)
          console.error('[PythonBridge] Python error:', errorOutput.substring(0, 500))
        } else if (trimmed.startsWith('[INDEXING_LOG]')) {
          // Capture indexing log messages
          console.log('[Indexing]', trimmed)
          // Forward to web console via IPC
          if (onLog) {
            onLog({ type: 'stdout', message: trimmed })
          }
          // Store last log for crash diagnostics
          lastIndexingLog = trimmed
        } else if (trimmed && trimmed.includes('[Python]')) {
          console.log(trimmed)
          // Forward to web console via IPC
          if (onLog) {
            onLog({ type: 'stdout', message: trimmed })
          }
        } else if (trimmed) {
          console.log('[Python stdout]', trimmed.substring(0, 200))
          // Forward to web console via IPC
          if (onLog) {
            onLog({ type: 'stdout', message: trimmed.substring(0, 500) })
          }
        }
      }
    })

    proc.stderr.on('data', (data: Buffer) => {
      const line = data.toString().trim()
      if (line) {
        console.error('[Python stderr]', line)
        errorOutput += line + '\n'
        // Forward to web console via IPC
        if (onLog) {
          onLog({ type: 'stderr', message: line.substring(0, 500) })
        }
        // Also capture indexing log messages from stderr
        if (line.includes('[INDEXING_LOG]')) {
          console.log('[Indexing-Stderr]', line)
          // Store last log for crash diagnostics
          lastIndexingLog = line
        }
      }
    })

    // Timeout after 5 minutes
    const timeout = setTimeout(() => {
      console.error('[PythonBridge] Operation timed out after 5 minutes')
      console.error(`[PythonBridge] Last indexing log before timeout: ${lastIndexingLog || 'None captured'}`)
      proc.kill('SIGTERM')
    }, 5 * 60 * 1000)

    proc.on('close', (code: number | null) => {
      clearTimeout(timeout)
      console.log(`[PythonBridge] Process closed with code: ${code}`)
      console.log(`[PythonBridge] Process had output: ${hasOutput}`)
      console.log(`[PythonBridge] Error output length: ${errorOutput.length}`)

      // Clean up
      activeProcesses.delete(processId)

      if (code !== 0 && !result) {
        // Process failed - provide detailed error information
        let errorMessage: string
        
        if (code === null) {
          // Code null means process was killed or crashed
          const lastLogContext = lastIndexingLog ? `\nLast log before crash: ${lastIndexingLog}` : ''
          errorMessage = `Indexing failed: Out of memory or process crashed (exit code null). ` +
            `This typically happens when indexing large folders or when the system is low on memory. ` +
            `Try:\n` +
            `1. Close other applications to free memory\n` +
            `2. Index smaller folders at a time\n` +
            `3. Restart the application and try again${lastLogContext}`
        } else if (!hasOutput) {
          errorMessage = `Python process failed (code ${code}) with no output. ` +
            `Python may not be installed or roughcut module not found.`
        } else {
          errorMessage = `Python process failed (code ${code})` +
            (errorOutput ? `: ${errorOutput.substring(0, 500)}` : ': No error output captured')
        }
        
        console.error('[PythonBridge] Rejecting with error:', errorMessage.substring(0, 200))
        reject(new Error(errorMessage))
      } else if (result) {
        console.log('[PythonBridge] Resolving with result')
        resolve(result)
      } else {
        reject(new Error('No result from Python process - process may have crashed before producing output'))
      }
    })

    proc.on('error', (err: Error) => {
      clearTimeout(timeout)
      console.error('[PythonBridge] Process error:', err)
      activeProcesses.delete(processId)
      reject(new Error(`Failed to spawn Python: ${err.message}. Is Python installed?`))
    })
  })
}

/**
 * Cancel an active indexing operation
 */
export function cancelIndexing(processId: string): boolean {
  const procInfo = activeProcesses.get(processId)
  if (procInfo && procInfo.proc) {
    console.log(`[PythonBridge] Cancelling process: ${processId}`)
    procInfo.proc.kill('SIGTERM')

    // Force kill after 5 seconds if still running
    setTimeout(() => {
      try {
        if (!procInfo.proc.killed) {
          procInfo.proc.kill('SIGKILL')
        }
      } catch (e) {
        // Ignore errors
      }
    }, 5000)

    activeProcesses.delete(processId)
    return true
  }
  return false
}

/**
 * Get list of active indexing operations
 */
export function getActiveIndexingOperations(): Array<{ id: string; command: string; pid: number }> {
  return Array.from(activeProcesses.entries()).map(([id, info]) => ({
    id,
    command: info.command,
    pid: info.proc.pid as number
  }))
}

/**
 * Clean up all active processes
 */
export function cleanupAllProcesses(): void {
  console.log(`[PythonBridge] Cleaning up ${activeProcesses.size} active processes`)
  for (const [, procInfo] of activeProcesses) {
    try {
      procInfo.proc.kill('SIGTERM')
    } catch (e) {
      // Ignore errors during cleanup
    }
  }
  activeProcesses.clear()
}
