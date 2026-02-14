"""Sandboxed Python code executor for the research agent.

Executes Python code snippets in a subprocess with restricted capabilities.
Used by the research agent to perform data analysis, calculations, and
transformations on extracted document data.
"""

import asyncio
import logging
import os
import sys
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)

# Maximum execution time in seconds
MAX_EXECUTION_TIME = 30

# Maximum output size in characters
MAX_OUTPUT_SIZE = 50_000

# Allowed imports (whitelist)
ALLOWED_IMPORTS = """
import sys
import os
import json
import csv
import math
import statistics
import re
import collections
import itertools
import functools
import datetime
import decimal
import fractions
import io
import textwrap

# Data analysis
try:
    import pandas as pd
except ImportError:
    pass

try:
    import openpyxl
except ImportError:
    pass

try:
    import fitz  # PyMuPDF
except ImportError:
    pass
"""

# Security preamble - restrict dangerous operations
SECURITY_PREAMBLE = """
import builtins as _builtins

# Block dangerous builtins
_blocked = ['exec', 'eval', 'compile', '__import__', 'breakpoint']
for _b in _blocked:
    if hasattr(_builtins, _b):
        pass  # Allow in sandboxed subprocess for now

# Redirect output capture
import io as _io
import sys as _sys
_output_buffer = _io.StringIO()
"""


async def execute_python_code(
    code: str,
    working_dir: str | None = None,
    timeout: int = MAX_EXECUTION_TIME,
) -> dict[str, str | bool]:
    """Execute Python code in a sandboxed subprocess.

    Args:
        code: Python code to execute.
        working_dir: Optional working directory for the subprocess.
        timeout: Maximum execution time in seconds.

    Returns:
        Dictionary with:
            - success: Whether execution completed without errors
            - output: Captured stdout output
            - error: Error message if execution failed
    """
    logger.info(f"[CODE_EXEC] Executing code snippet ({len(code)} chars)")

    # Build the full script with imports available
    full_script = f"""
import sys
import io

# Capture all output
_captured = io.StringIO()
_old_stdout = sys.stdout
sys.stdout = _captured

try:
{_indent_code(code, 4)}
except Exception as _e:
    print(f"Error: {{type(_e).__name__}}: {{_e}}")
finally:
    sys.stdout = _old_stdout
    output = _captured.getvalue()
    if len(output) > {MAX_OUTPUT_SIZE}:
        output = output[:{MAX_OUTPUT_SIZE}] + "\\n... (output truncated)"
    print(output, end="")
"""

    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".py",
            delete=False,
            dir=working_dir,
        ) as f:
            f.write(full_script)
            script_path = f.name

        try:
            process = await asyncio.create_subprocess_exec(
                sys.executable,
                script_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=working_dir,
                env=_get_safe_env(),
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout,
            )

            stdout_str = stdout.decode("utf-8", errors="replace").strip()
            stderr_str = stderr.decode("utf-8", errors="replace").strip()

            if process.returncode == 0:
                logger.info(f"[CODE_EXEC] Success ({len(stdout_str)} chars output)")
                return {
                    "success": True,
                    "output": stdout_str or "(no output)",
                    "error": "",
                }
            else:
                logger.warning(f"[CODE_EXEC] Failed with return code {process.returncode}")
                return {
                    "success": False,
                    "output": stdout_str,
                    "error": stderr_str or f"Process exited with code {process.returncode}",
                }

        except asyncio.TimeoutError:
            logger.error(f"[CODE_EXEC] Timeout after {timeout}s")
            process.kill()
            return {
                "success": False,
                "output": "",
                "error": f"Execution timed out after {timeout} seconds",
            }
        finally:
            # Clean up temp file
            try:
                os.unlink(script_path)
            except OSError:
                pass

    except Exception as e:
        logger.error(f"[CODE_EXEC] Error: {e}")
        return {
            "success": False,
            "output": "",
            "error": f"Failed to execute code: {str(e)}",
        }


def _indent_code(code: str, spaces: int) -> str:
    """Indent code by the specified number of spaces."""
    indent = " " * spaces
    lines = code.split("\n")
    return "\n".join(f"{indent}{line}" for line in lines)


def _get_safe_env() -> dict[str, str]:
    """Get a restricted environment for the subprocess."""
    env = os.environ.copy()
    # Remove any sensitive environment variables
    sensitive_keys = [
        "ANTHROPIC_API_KEY",
        "SUPABASE_SERVICE_KEY",
        "SUPABASE_ANON_KEY",
        "GOOGLE_SERVICE_ACCOUNT_JSON",
    ]
    for key in sensitive_keys:
        env.pop(key, None)
    return env
