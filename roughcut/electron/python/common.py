"""Common utilities for RoughCut Electron Python scripts.

Provides shared functionality for logging, timeout handling, and result formatting.
"""

import sys
import json
import time
import logging
import traceback
from typing import Any, Callable

# Maximum execution time (10 minutes)
MAX_EXECUTION_TIME = 600


def setup_logging() -> None:
    """Configure logging to output INFO and above to stdout."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(message)s',
        stream=sys.stdout,
        force=True
    )


def log_indexing(message: str) -> None:
    """Log an indexing message with the [INDEXING_LOG] prefix."""
    print(f"[INDEXING_LOG] {message}", flush=True)


def output_progress(progress: dict[str, Any]) -> None:
    """Output a progress update as JSON."""
    print(f"PROGRESS:{json.dumps(progress)}", flush=True)


def output_result(result: dict[str, Any]) -> None:
    """Output the final result as JSON."""
    print(f"RESULT:{json.dumps(result)}", flush=True)


def output_error(message: str, exception: Exception | None = None) -> None:
    """Output an error message with optional exception details."""
    if exception:
        error_msg = f"{message}\n{str(exception)}\n{traceback.format_exc()}"
    else:
        error_msg = message
    print(f"ERROR:{error_msg}", flush=True)
    log_indexing(f"ERROR: {message}")


def output_streaming_asset(asset: dict[str, Any]) -> None:
    """Output a newly indexed asset for real-time GUI streaming.
    
    This sends assets immediately as they're written to the database,
    allowing the GUI to display records in real-time during indexing.
    """
    print(f"STREAM_ASSET:{json.dumps(asset)}", flush=True)


def setup_timeout_handler() -> None:
    """Set up a timeout alarm (Unix only, Windows will ignore)."""
    try:
        import signal

        def timeout_handler(signum: int, frame: Any) -> None:
            log_indexing(f"CRITICAL: Script execution timed out after {MAX_EXECUTION_TIME} seconds")
            print(f"ERROR:Script execution timed out - indexing took too long", flush=True)
            sys.exit(1)

        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(MAX_EXECUTION_TIME)
        log_indexing(f"Set execution timeout: {MAX_EXECUTION_TIME} seconds")
    except (ImportError, AttributeError):
        log_indexing("Note: Timeout alarm not available on this platform")


def cancel_timeout() -> None:
    """Cancel the timeout alarm if it was set."""
    try:
        import signal
        signal.alarm(0)
    except:
        pass


def add_roughcut_to_path(roughcut_path: str) -> None:
    """Add the roughcut module path to sys.path."""
    if roughcut_path not in sys.path:
        sys.path.insert(0, roughcut_path)
    log_indexing("Python path updated")


def run_async_main(main_func: Callable[[], Any]) -> None:
    """Run an async main function with proper error handling and timeout."""
    import asyncio

    setup_timeout_handler()
    log_indexing("Starting asyncio.run(main())...")

    try:
        asyncio.run(main_func())
        log_indexing("asyncio.run(main()) completed successfully")
        cancel_timeout()
    except Exception as e:
        log_indexing(f"CRITICAL ERROR in asyncio.run: {str(e)}")
        output_error("Critical asyncio error", e)
        sys.exit(1)

    log_indexing("Script completed")
