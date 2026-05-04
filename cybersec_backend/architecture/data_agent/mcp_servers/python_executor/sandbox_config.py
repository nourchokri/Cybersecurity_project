"""
Sandbox Configuration for Python-Executor MCP Server

This module defines security profiles for code execution in the Python-Executor MCP.
Two execution modes are supported:
- RESTRICTED: Safe data analysis with minimal imports (default)
- ATTACK_SIMULATION: Adversarial agent mode with expanded imports for attack logic

The configuration trusts Daytona's cloud isolation for file system and process
restrictions, focusing on preventing data exfiltration and code injection.
"""

import re
from typing import Dict, Set, Tuple


# RESTRICTED mode: Safe data analysis and transformation
RESTRICTED_IMPORTS: Set[str] = {
    # Data manipulation
    "json",
    
    # Date/time
    "datetime",
    
    # Text processing
    "re",
    
    # Math/stats
    "math",
    "statistics",
    
    # Data structures
    "collections",
    "itertools",
    "functools",
    
    # Type hints
    "typing",
    
    # Numeric types
    "decimal",
    "fractions",
    
    # String utilities
    "string",
}


# ATTACK_SIMULATION mode: RESTRICTED + attack simulation utilities
ATTACK_SIMULATION_IMPORTS: Set[str] = RESTRICTED_IMPORTS | {
    # Randomization for attack patterns
    "random",
    
    # Encoding/hashing for attack simulation
    "base64",
    "hashlib",
    "uuid",
    "hmac",
    "secrets",
}


# Dangerous patterns blocked in BOTH modes
DANGEROUS_PATTERNS: list[str] = [
    # Network operations (prevent data exfiltration)
    r"requests\.",
    r"urllib\.",
    r"socket\.",
    r"http\.client",
    r"ftplib\.",
    r"smtplib\.",
    r"telnetlib\.",
    
    # Code injection
    r"eval\s*\(",
    r"exec\s*\(",
    r"__import__",
    r"compile\s*\(",
    
    # Subprocess/system access
    r"subprocess\.",
    r"os\.system",
    r"os\.popen",
    r"os\.spawn",
]


# Configuration for RESTRICTED mode
RESTRICTED_CONFIG: Dict = {
    "timeout_seconds": 10,
    "allowed_imports": RESTRICTED_IMPORTS,
    "dangerous_patterns": DANGEROUS_PATTERNS,
    "description": "Safe data analysis with minimal imports",
}


# Configuration for ATTACK_SIMULATION mode
ATTACK_SIMULATION_CONFIG: Dict = {
    "timeout_seconds": 30,
    "allowed_imports": ATTACK_SIMULATION_IMPORTS,
    "dangerous_patterns": DANGEROUS_PATTERNS,
    "description": "Adversarial agent mode with expanded imports for attack logic",
}


def get_config(execution_mode: str) -> Dict:
    """
    Get configuration for the specified execution mode.
    
    Args:
        execution_mode: "restricted" or "attack_simulation"
        
    Returns:
        Configuration dictionary with timeout, allowed_imports, and dangerous_patterns
        
    Raises:
        ValueError: If execution_mode is not recognized
    """
    if execution_mode == "restricted":
        return RESTRICTED_CONFIG
    elif execution_mode == "attack_simulation":
        return ATTACK_SIMULATION_CONFIG
    else:
        raise ValueError(
            f"Invalid execution_mode: {execution_mode}. "
            f"Must be 'restricted' or 'attack_simulation'"
        )


def validate_imports(code: str, execution_mode: str) -> Tuple[bool, str]:
    """
    Validate that code only imports allowed modules for the execution mode.
    
    Args:
        code: Python code to validate
        execution_mode: "restricted" or "attack_simulation"
        
    Returns:
        Tuple of (is_valid, error_message)
        - is_valid: True if all imports are allowed, False otherwise
        - error_message: Empty string if valid, error description if invalid
    """
    config = get_config(execution_mode)
    allowed_imports = config["allowed_imports"]
    
    # Extract import statements using regex
    import_pattern = r"^\s*(?:import|from)\s+([a-zA-Z_][a-zA-Z0-9_]*)"
    
    for line in code.split("\n"):
        match = re.match(import_pattern, line)
        if match:
            module_name = match.group(1)
            if module_name not in allowed_imports:
                return False, (
                    f"Import '{module_name}' not allowed in {execution_mode} mode. "
                    f"Allowed imports: {sorted(allowed_imports)}"
                )
    
    return True, ""


def scan_dangerous_patterns(code: str, execution_mode: str) -> Tuple[bool, str]:
    """
    Scan code for dangerous patterns (network operations, code injection).
    
    Args:
        code: Python code to scan
        execution_mode: "restricted" or "attack_simulation"
        
    Returns:
        Tuple of (is_safe, error_message)
        - is_safe: True if no dangerous patterns found, False otherwise
        - error_message: Empty string if safe, error description if dangerous
    """
    config = get_config(execution_mode)
    dangerous_patterns = config["dangerous_patterns"]
    
    for pattern in dangerous_patterns:
        if re.search(pattern, code):
            return False, f"Blocked dangerous pattern: {pattern}"
    
    return True, ""


def sanitize_code(code: str, execution_mode: str) -> Tuple[bool, str]:
    """
    Comprehensive code sanitization: validate imports and scan for dangerous patterns.
    
    Args:
        code: Python code to sanitize
        execution_mode: "restricted" or "attack_simulation"
        
    Returns:
        Tuple of (is_safe, error_message)
        - is_safe: True if code passes all checks, False otherwise
        - error_message: Empty string if safe, error description if unsafe
    """
    # Validate code is not empty
    if not code or not code.strip():
        return False, "Code cannot be empty"
    
    # Check imports
    imports_valid, import_error = validate_imports(code, execution_mode)
    if not imports_valid:
        return False, import_error
    
    # Check dangerous patterns
    patterns_safe, pattern_error = scan_dangerous_patterns(code, execution_mode)
    if not patterns_safe:
        return False, pattern_error
    
    return True, ""


def get_allowed_imports(execution_mode: str) -> list[str]:
    """
    Get list of allowed imports for the specified execution mode.
    
    Args:
        execution_mode: "restricted" or "attack_simulation"
        
    Returns:
        Sorted list of allowed module names
    """
    config = get_config(execution_mode)
    return sorted(config["allowed_imports"])


def get_timeout(execution_mode: str) -> int:
    """
    Get timeout in seconds for the specified execution mode.
    
    Args:
        execution_mode: "restricted" or "attack_simulation"
        
    Returns:
        Timeout in seconds
    """
    config = get_config(execution_mode)
    return config["timeout_seconds"]


def execute_code_in_sandbox(code: str, timeout_seconds: int, code_hash: str, execution_mode: str) -> Dict:
    """
    Execute Python code in a sandboxed environment with mode-aware validation.
    
    This function performs comprehensive code sanitization before execution:
    1. Validates imports against mode-specific whitelist
    2. Scans for dangerous patterns (network ops, code injection)
    3. Rejects code with blocked patterns before execution
    
    Args:
        code: Python code to execute
        timeout_seconds: Execution timeout in seconds
        code_hash: SHA-256 hash of code for audit trail
        execution_mode: "restricted" or "attack_simulation"
        
    Returns:
        Dictionary with execution results or error information
    """
    import sys
    import io
    import time
    import traceback
    import threading
    from contextlib import redirect_stdout, redirect_stderr
    from mcp_servers.common.utils import setup_logger
    
    # Initialize logger for error logging
    logger = setup_logger("python_executor", "logs/python_executor.log")
    
    # Step 1: Sanitize code with mode-aware validation
    is_safe, error_message = sanitize_code(code, execution_mode)
    
    if not is_safe:
        logger.error(
            f"Code validation failed (hash: {code_hash[:16]}..., mode: {execution_mode}): {error_message}"
        )
        return {
            "error": {
                "type": "validation_error",
                "message": error_message,
                "details": {
                    "code_hash": code_hash,
                    "execution_mode": execution_mode
                }
            },
            "stdout": "",
            "stderr": "",
            "execution_time_ms": 0,
            "execution_mode": execution_mode,
            "success": False
        }
    
    # Step 2: Execute code in isolated environment with cross-platform timeout
    stdout_capture = io.StringIO()
    stderr_capture = io.StringIO()
    start_time = time.time()
    
    # Shared state for thread execution
    execution_result = {
        "completed": False,
        "exception": None,
        "namespace": None
    }
    
    def execute_in_thread():
        """Execute code in a separate thread to enable timeout on Windows."""
        try:
            # Create isolated namespace for execution
            namespace = {
                "__builtins__": __builtins__,
                "__name__": "__main__",
            }
            
            # Execute code with output capture
            with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
                exec(code, namespace)
            
            execution_result["namespace"] = namespace
            execution_result["completed"] = True
            
        except Exception as e:
            execution_result["exception"] = e
            execution_result["completed"] = True
    
    # Start execution in a separate thread
    execution_thread = threading.Thread(target=execute_in_thread, daemon=True)
    execution_thread.start()
    
    # Wait for completion or timeout
    execution_thread.join(timeout=timeout_seconds)
    
    elapsed_time_ms = (time.time() - start_time) * 1000
    
    # Check if thread is still running (timeout occurred)
    if execution_thread.is_alive():
        # Timeout occurred
        logger.error(
            f"Code execution timeout (hash: {code_hash[:16]}..., mode: {execution_mode}, "
            f"timeout: {timeout_seconds}s, elapsed: {elapsed_time_ms:.2f}ms)"
        )
        
        return {
            "error": {
                "type": "timeout_error",
                "message": f"Code execution exceeded {timeout_seconds} second timeout",
                "details": {
                    "code_hash": code_hash,
                    "execution_mode": execution_mode,
                    "timeout_seconds": timeout_seconds,
                    "elapsed_time_ms": round(elapsed_time_ms, 2)
                }
            },
            "stdout": stdout_capture.getvalue(),
            "stderr": stderr_capture.getvalue(),
            "execution_time_ms": round(elapsed_time_ms, 2),
            "execution_mode": execution_mode,
            "success": False
        }
    
    # Check if an exception occurred during execution
    if execution_result["exception"] is not None:
        e = execution_result["exception"]
        
        # Capture exception details with full traceback
        error_type = type(e).__name__
        error_message = str(e)
        error_traceback = traceback.format_exception(type(e), e, e.__traceback__)
        error_traceback_str = "".join(error_traceback)
        
        logger.error(
            f"Code execution exception (hash: {code_hash[:16]}..., mode: {execution_mode}, "
            f"type: {error_type}, time: {elapsed_time_ms:.2f}ms): {error_message}"
        )
        logger.error(f"Traceback:\n{error_traceback_str}")
        
        return {
            "error": {
                "type": error_type,
                "message": error_message,
                "traceback": error_traceback_str,
                "details": {
                    "code_hash": code_hash,
                    "execution_mode": execution_mode
                }
            },
            "stdout": stdout_capture.getvalue(),
            "stderr": stderr_capture.getvalue(),
            "execution_time_ms": round(elapsed_time_ms, 2),
            "execution_mode": execution_mode,
            "success": False
        }
    
    # Successful execution
    namespace = execution_result.get("namespace", {})
    return_value = namespace.get("__return__", None)
    
    logger.info(
        f"Code execution succeeded (hash: {code_hash[:16]}..., mode: {execution_mode}, "
        f"time: {elapsed_time_ms:.2f}ms)"
    )
    
    return {
        "stdout": stdout_capture.getvalue(),
        "stderr": stderr_capture.getvalue(),
        "return_value": str(return_value) if return_value is not None else "",
        "execution_time_ms": round(elapsed_time_ms, 2),
        "execution_mode": execution_mode,
        "success": True
    }
