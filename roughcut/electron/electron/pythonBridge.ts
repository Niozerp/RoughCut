/**
 * Python Backend Bridge for Electron
 * 
 * Handles spawning Python processes and communicating with the RoughCut backend.
 * Used for indexing operations, asset queries, and other backend tasks.
 */

import { spawn } from 'child_process'
import path from 'path'
import { fileURLToPath } from 'url'
import fs from 'fs'
import os from 'os'
import { app } from 'electron'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)

// Track active Python processes
const activeProcesses = new Map<string, { proc: any; tmpFile: string; command: string }>()

// Required Python dependencies
const REQUIRED_DEPENDENCIES = [
  'aiofiles',
  'pydantic',
  'pyyaml',
  'cryptography',
  'openai',
  'notion_client',  // underscore for import check
  'websockets'
]

/**
 * Find the Python executable, roughcut module, and project root
 */
function findPythonEnvironment(): { 
  roughcutPath: string | null; 
  pythonPath: string; 
  projectRoot: string | null;
  usePoetry: boolean;
} {
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

/**
 * Get the Poetry virtual environment Python path
 */
function getPoetryVenvPython(projectRoot: string): string | null {
  try {
    // Common Poetry venv locations (in project)
    const venvPaths = [
      path.join(projectRoot, '.venv', 'Scripts', 'python.exe'),  // Windows
      path.join(projectRoot, '.venv', 'bin', 'python'),  // Unix
      path.join(projectRoot, '.venv', 'bin', 'python3'),
    ]
    
    // Check common venv locations first
    for (const venvPath of venvPaths) {
      if (fs.existsSync(venvPath)) {
        console.log('[PythonBridge] Found Poetry venv at:', venvPath)
        return venvPath
      }
    }
    
    // Try to get venv path from poetry env info
    const { execSync } = require('child_process')
    try {
      const result = execSync('poetry env info --path', { 
        cwd: projectRoot,
        encoding: 'utf-8',
        timeout: 5000 
      }).trim()
      
      if (result) {
        const poetryVenvPython = process.platform === 'win32'
          ? path.join(result, 'Scripts', 'python.exe')
          : path.join(result, 'bin', 'python')
        
        if (fs.existsSync(poetryVenvPython)) {
          console.log('[PythonBridge] Poetry venv from poetry env info:', poetryVenvPython)
          return poetryVenvPython
        }
      }
    } catch (e) {
      // Poetry command failed, continue
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
 * Run poetry install to set up dependencies
 */
async function runPoetryInstall(projectRoot: string): Promise<{ success: boolean; error?: string }> {
  return new Promise((resolve) => {
    console.log('[PythonBridge] Running poetry install in:', projectRoot)
    
    const { spawn } = require('child_process')
    const proc = spawn('poetry', ['install', '--no-interaction'], {
      cwd: projectRoot,
      timeout: 10 * 60 * 1000  // 10 minutes
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
      if (code === 0) {
        console.log('[PythonBridge] Poetry install completed successfully')
        resolve({ success: true })
      } else {
        console.error('[PythonBridge] Poetry install failed with code:', code)
        resolve({ 
          success: false, 
          error: `Poetry install failed (code ${code}): ${stderr || stdout || 'Unknown error'}` 
        })
      }
    })
    
    proc.on('error', (err: Error) => {
      console.error('[PythonBridge] Failed to spawn poetry:', err)
      resolve({ 
        success: false, 
        error: `Cannot run poetry: ${err.message}. Is Poetry installed?` 
      })
    })
  })
}

/**
 * Check if Python dependencies are installed
 */
async function checkDependencies(pythonPath: string): Promise<{ allInstalled: boolean; missing: string[] }> {
  return new Promise((resolve) => {
    const checkScript = `
import sys
missing = []
for dep in [${REQUIRED_DEPENDENCIES.map(d => `'${d}'`).join(', ')}]:
    try:
        __import__(dep)
    except ImportError:
        missing.append(dep)
if missing:
    print(f"MISSING:{','.join(missing)}")
else:
    print("OK:All dependencies installed")
`
    const tmpFile = path.join(os.tmpdir(), `roughcut_deps_${Date.now()}.py`)
    fs.writeFileSync(tmpFile, checkScript)
    
    const proc = spawn(pythonPath, [tmpFile], { timeout: 10000 })
    let output = ''
    
    proc.stdout.on('data', (data: Buffer) => {
      output += data.toString()
    })
    
    proc.on('close', () => {
      try { fs.unlinkSync(tmpFile) } catch {}
      
      const lines = output.split('\n')
      for (const line of lines) {
        if (line.startsWith('MISSING:')) {
          const missing = line.substring(8).split(',').filter(Boolean)
          resolve({ allInstalled: false, missing })
          return
        } else if (line.startsWith('OK:')) {
          resolve({ allInstalled: true, missing: [] })
          return
        }
      }
      resolve({ allInstalled: false, missing: REQUIRED_DEPENDENCIES })
    })
    
    proc.on('error', () => {
      resolve({ allInstalled: false, missing: REQUIRED_DEPENDENCIES })
    })
  })
}

/**
 * Build the Python script for indexing
 */
function buildPythonScript(command: string, params: Record<string, any>, roughcutPath: string): string {
  const paramsJson = JSON.stringify(params)
  
  // Escape backslashes for Python raw string
  const escapedPath = roughcutPath.replace(/\\/g, '\\\\')
  
  return `
import sys
import json
import asyncio
import os

# Add roughcut to path
sys.path.insert(0, r'${escapedPath}')

from roughcut.backend.indexing.indexer import MediaIndexer
from roughcut.config.models import MediaFolderConfig

async def main():
    try:
        params = json.loads(r'''${paramsJson}''')
        
        if '${command}' == 'index' or '${command}' == 'reindex':
            # Create folder config
            config = MediaFolderConfig()
            if params.folders:
                for folder in params.folders:
                    if folder['category'] == 'music':
                        config.music_folder = folder['path']
                    elif folder['category'] == 'sfx':
                        config.sfx_folder = folder['path']
                    elif folder['category'] == 'vfx':
                        config.vfx_folder = folder['path']
            
            indexer = MediaIndexer()
            
            # Connect to database
            connected = await indexer.connect_database()
            
            progress_updates = []
            def progress_callback(update):
                progress_updates.append(update)
                print(f"PROGRESS:{json.dumps(update)}", flush=True)
            
            indexer.progress_callback = progress_callback
            
            if '${command}' == 'reindex':
                result = await indexer.reindex_folders(config)
            else:
                result = await indexer.index_media(config)
            
            # Build result dict
            result_dict = {
                'indexed_count': result.indexed_count,
                'new_count': result.new_count,
                'modified_count': result.modified_count,
                'deleted_count': result.deleted_count,
                'moved_count': getattr(result, 'moved_count', 0),
                'total_scanned': getattr(result, 'total_scanned', 0),
                'duration_ms': result.duration_ms,
                'errors': result.errors,
                'progress_updates': progress_updates,
                'database_connected': connected
            }
            
            print(f"RESULT:{json.dumps(result_dict)}", flush=True)
            
            await indexer.disconnect_database()
            
        elif '${command}' == 'query':
            from roughcut.backend.database.spacetime_client import SpacetimeClient, SpacetimeConfig
            from roughcut.config.settings import get_config_manager
            
            config_manager = get_config_manager()
            spacetime_cfg = config_manager.get_spacetime_config()
            
            db_config = SpacetimeConfig(
                host=spacetime_cfg.get('host', 'localhost'),
                port=spacetime_cfg.get('port', 3000),
                database_name=spacetime_cfg.get('database_name', 'roughcut'),
                identity_token=spacetime_cfg.get('identity_token')
            )
            
            client = SpacetimeClient(db_config)
            connected = await client.connect()
            
            if connected:
                assets = await client.query_assets(
                    category=params.get('category'),
                    limit=params.get('limit', 1000)
                )
                
                # Convert assets to JSON-serializable format
                asset_list = []
                for asset in assets.assets:
                    asset_list.append({
                        'id': asset.id,
                        'file_path': str(asset.file_path),
                        'file_name': asset.file_name,
                        'category': asset.category,
                        'file_size': asset.file_size,
                        'ai_tags': asset.ai_tags,
                        'duration': getattr(asset, 'duration', None),
                        'used': getattr(asset, 'used', False)
                    })
                
                result = {
                    'assets': asset_list,
                    'total_count': assets.total_count,
                    'database_connected': True
                }
            else:
                result = {
                    'assets': [],
                    'total_count': 0,
                    'database_connected': False,
                    'error': 'Could not connect to SpacetimeDB'
                }
            
            print(f"RESULT:{json.dumps(result)}", flush=True)
            await client.disconnect()
            
        elif '${command}' == 'status':
            from roughcut.backend.database.spacetime_client import SpacetimeClient, SpacetimeConfig
            from roughcut.config.settings import get_config_manager
            
            config_manager = get_config_manager()
            spacetime_cfg = config_manager.get_spacetime_config()
            
            db_config = SpacetimeConfig(
                host=spacetime_cfg.get('host', 'localhost'),
                port=spacetime_cfg.get('port', 3000),
                database_name=spacetime_cfg.get('database_name', 'roughcut'),
                identity_token=spacetime_cfg.get('identity_token')
            )
            
            client = SpacetimeClient(db_config)
            connected = await client.connect()
            
            if connected:
                counts = await client.get_asset_counts()
                result = {
                    'connected': True,
                    'music_count': counts.music,
                    'sfx_count': counts.sfx,
                    'vfx_count': counts.vfx,
                    'total_count': counts.total
                }
            else:
                result = {
                    'connected': False,
                    'music_count': 0,
                    'sfx_count': 0,
                    'vfx_count': 0,
                    'total_count': 0
                }
            
            print(f"RESULT:{json.dumps(result)}", flush=True)
            await client.disconnect()
        
        else:
            print(f"ERROR:Unknown command: ${command}", flush=True)
            
    except Exception as e:
        import traceback
        error_msg = f"{str(e)}\\n{traceback.format_exc()}"
        print(f"ERROR:{error_msg}", flush=True)
        sys.exit(1)

asyncio.run(main())
`
}

/**
 * Execute a Python indexing command
 */
export async function executePythonCommand(
  command: string,
  params: Record<string, any> = {},
  onProgress: ((progress: any) => void) | null = null
): Promise<any> {
  const { roughcutPath, pythonPath, projectRoot, usePoetry } = findPythonEnvironment()
  
  if (!roughcutPath) {
    throw new Error('Could not find RoughCut Python module.')
  }
  
  // Determine which Python to use
  let actualPythonPath = pythonPath
  
  if (usePoetry && projectRoot) {
    // Try to find Poetry virtual environment Python
    const poetryPython = getPoetryVenvPython(projectRoot)
    if (poetryPython) {
      actualPythonPath = poetryPython
      console.log('[PythonBridge] Using Poetry virtual environment Python:', actualPythonPath)
    } else {
      console.log('[PythonBridge] Poetry project detected but venv not found, using system Python')
    }
  }
  
  // Check dependencies
  console.log('[PythonBridge] Checking Python dependencies...')
  let depsCheck = await checkDependencies(actualPythonPath)
  
  // If dependencies missing and we have a Poetry project, try auto-install
  if (!depsCheck.allInstalled && usePoetry && projectRoot) {
    console.log('[PythonBridge] Dependencies missing, attempting auto-install with Poetry...')
    console.log('[PythonBridge] Missing:', depsCheck.missing.join(', '))
    
    const installResult = await runPoetryInstall(projectRoot)
    
    if (installResult.success) {
      console.log('[PythonBridge] Poetry install completed, re-checking dependencies...')
      
      // Re-find the venv (it should now exist)
      const poetryPython = getPoetryVenvPython(projectRoot)
      if (poetryPython) {
        actualPythonPath = poetryPython
        console.log('[PythonBridge] Now using Poetry venv Python:', actualPythonPath)
      }
      
      // Re-check dependencies
      depsCheck = await checkDependencies(actualPythonPath)
      
      if (depsCheck.allInstalled) {
        console.log('[PythonBridge] All dependencies now installed!')
      } else {
        console.error('[PythonBridge] Still missing after install:', depsCheck.missing.join(', '))
      }
    } else {
      console.error('[PythonBridge] Poetry install failed:', installResult.error)
    }
  }
  
  if (!depsCheck.allInstalled) {
    const missingList = depsCheck.missing.join(', ')
    
    let errorMsg: string
    if (usePoetry && projectRoot) {
      errorMsg = `Missing required Python dependencies: ${missingList}\n\n`
      errorMsg += `Poetry auto-install failed or is not available.\n\n`
      errorMsg += `To fix this, try one of the following:\n\n`
      errorMsg += `Option 1 - Run from DaVinci Resolve:\n`
      errorMsg += `  Workspace > Scripts > RoughCut (Install)\n\n`
      errorMsg += `Option 2 - Run manually in terminal:\n`
      errorMsg += `  cd "${projectRoot}"\n`
      errorMsg += `  poetry install\n\n`
      errorMsg += `Option 3 - Install with pip:\n`
      errorMsg += `  pip install ${missingList}`
    } else {
      errorMsg = `Missing required Python dependencies: ${missingList}\n\n`
      errorMsg += `Install with:\n`
      errorMsg += `pip install ${missingList}`
    }
    
    console.error('[PythonBridge]', errorMsg)
    throw new Error(errorMsg)
  }
  
  console.log('[PythonBridge] All dependencies are installed')
  
  return new Promise((resolve, reject) => {
    // Build Python script
    const scriptContent = buildPythonScript(command, params, roughcutPath)
    
    // Write script to temp file
    const tmpFile = path.join(os.tmpdir(), `roughcut_index_${Date.now()}.py`)
    fs.writeFileSync(tmpFile, scriptContent)
    
    console.log(`[PythonBridge] ============================================`)
    console.log(`[PythonBridge] Spawning Python: ${actualPythonPath}`)
    console.log(`[PythonBridge] Command: ${command}`)
    console.log(`[PythonBridge] Script: ${tmpFile}`)
    console.log(`[PythonBridge] Roughcut path: ${roughcutPath}`)
    console.log(`[PythonBridge] ============================================`)
    
    const proc = spawn(actualPythonPath, [tmpFile], {
      env: {
        ...process.env,
        PYTHONPATH: roughcutPath
      }
    })
    
    const processId = `index_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
    activeProcesses.set(processId, { proc, tmpFile, command })
    
    let result: any = null
    let errorOutput = ''
    let hasOutput = false
    
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
        } else if (trimmed && trimmed.includes('[Python]')) {
          console.log(trimmed)
        } else if (trimmed) {
          console.log('[Python stdout]', trimmed.substring(0, 200))
        }
      }
    })
    
    proc.stderr.on('data', (data: Buffer) => {
      const line = data.toString().trim()
      if (line) {
        console.error('[Python stderr]', line)
        errorOutput += line + '\n'
      }
    })
    
    // Timeout after 5 minutes
    const timeout = setTimeout(() => {
      console.error('[PythonBridge] Operation timed out after 5 minutes')
      proc.kill('SIGTERM')
    }, 5 * 60 * 1000)
    
    proc.on('close', (code: number | null) => {
      clearTimeout(timeout)
      console.log(`[PythonBridge] Process closed with code: ${code}`)
      
      // Clean up
      const procInfo = activeProcesses.get(processId)
      if (procInfo) {
        activeProcesses.delete(processId)
        try {
          fs.unlinkSync(procInfo.tmpFile)
        } catch (e: any) {
          // Ignore cleanup errors
        }
      }
      
      if (code !== 0 && !result) {
        if (!hasOutput) {
          reject(new Error(
            `Python process failed (code ${code}) with no output. ` +
            `Python may not be installed or roughcut module not found. ` +
            `Error: ${errorOutput || 'Unknown error'}`
          ))
        } else {
          reject(new Error(`Python process failed (code ${code}): ${errorOutput || 'Unknown error'}`))
        }
      } else if (result) {
        resolve(result)
      } else {
        reject(new Error('No result from Python process'))
      }
    })
    
    proc.on('error', (err: Error) => {
      clearTimeout(timeout)
      console.error('[PythonBridge] Process error:', err)
      activeProcesses.delete(processId)
      try {
        fs.unlinkSync(tmpFile)
      } catch (e) {}
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
    
    // Clean up temp file
    try {
      fs.unlinkSync(procInfo.tmpFile)
    } catch (e) {}
    
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
  for (const [processId, procInfo] of activeProcesses) {
    try {
      procInfo.proc.kill('SIGTERM')
      fs.unlinkSync(procInfo.tmpFile)
    } catch (e) {
      // Ignore errors during cleanup
    }
  }
  activeProcesses.clear()
}
