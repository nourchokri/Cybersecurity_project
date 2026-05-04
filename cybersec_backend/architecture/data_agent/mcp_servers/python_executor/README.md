# Python-Executor MCP Server

Execute Python code safely in a sandboxed environment with configurable security profiles.

## Overview

The Python-Executor MCP Server provides secure code execution capabilities for AI agents with two distinct security profiles:

- **RESTRICTED mode** (default): Safe data analysis and transformation with minimal imports
- **ATTACK_SIMULATION mode**: Adversarial agent mode with expanded imports for realistic attack code generation

All code execution happens in a Daytona cloud-based sandbox with isolation from the host system. The server focuses on preventing data exfiltration and code injection while trusting Daytona's cloud isolation for file system and process restrictions.

## Available Tools

### 1. execute_code

Execute Python code in a sandboxed environment with mode-aware security controls.

**Parameters:**
- `code` (string, required): Python code to execute
- `timeout_seconds` (integer, optional): Execution timeout in seconds (default: 10, max: 30)
- `execution_mode` (string, optional): Security profile - "restricted" (default) or "attack_simulation"

**Returns:**
```json
{
  "stdout": "string",
  "stderr": "string", 
  "return_value": "string",
  "execution_time_ms": 123.45,
  "execution_mode": "restricted",
  "success": true
}
```

**Error Response:**
```json
{
  "error": {
    "type": "validation_error|timeout_error|ExceptionType",
    "message": "Error description",
    "traceback": "Full traceback (for exceptions)",
    "details": {
      "code_hash": "sha256_hash",
      "execution_mode": "restricted"
    }
  },
  "stdout": "string",
  "stderr": "string",
  "execution_time_ms": 123.45,
  "execution_mode": "restricted",
  "success": false
}
```

**Example Usage (RESTRICTED mode):**
```python
# Data analysis with safe imports
result = execute_code(
    code="""
import json
import statistics

events = [
    {"file_size": 1024},
    {"file_size": 2048},
    {"file_size": 512}
]

sizes = [e["file_size"] for e in events]
print(f"Average: {statistics.mean(sizes)}")
print(f"Max: {max(sizes)}")
""",
    execution_mode="restricted"  # Default
)
```

**Example Usage (ATTACK_SIMULATION mode):**
```python
# Attack pattern generation with expanded imports
result = execute_code(
    code="""
import json
import random
import base64
from datetime import datetime, timedelta

def generate_credential_theft():
    base_time = datetime.now()
    events = []
    
    # Stage 1: Browser profile access
    events.append({
        "timestamp": base_time.isoformat(),
        "event_type": "file_access",
        "resource": "Chrome\\\\User Data",
        "is_simulated": True
    })
    
    # Stage 2: Encode stolen data (simulated)
    fake_creds = base64.b64encode(b"admin:pass").decode()
    
    # Stage 3: Exfiltration attempt
    events.append({
        "timestamp": (base_time + timedelta(minutes=5)).isoformat(),
        "event_type": "network_connection",
        "bytes_sent": len(fake_creds),
        "is_simulated": True
    })
    
    return events

result = generate_credential_theft()
print(json.dumps(result, indent=2))
""",
    execution_mode="attack_simulation",
    timeout_seconds=30
)
```

### 2. list_allowed_imports

Return the whitelist of permitted Python modules for a given execution mode.

**Parameters:**
- `execution_mode` (string, optional): "restricted" (default) or "attack_simulation"

**Returns:**
```json
{
  "execution_mode": "restricted",
  "allowed_imports": [
    "collections",
    "datetime",
    "decimal",
    "fractions",
    "functools",
    "itertools",
    "json",
    "math",
    "re",
    "statistics",
    "string",
    "typing"
  ],
  "count": 12,
  "description": "Safe data analysis and transformation (default)"
}
```

**Example Usage:**
```python
# Check allowed imports for restricted mode
result = list_allowed_imports(execution_mode="restricted")
print(f"Allowed modules: {result['allowed_imports']}")

# Check allowed imports for attack simulation mode
result = list_allowed_imports(execution_mode="attack_simulation")
print(f"Attack simulation modules: {result['allowed_imports']}")
```

## Execution Modes

### RESTRICTED Mode (Default)

**Purpose:** Safe data analysis and transformation

**Use Case:** Data Engineering Agent processing events

**Timeout:** 10 seconds (default)

**Allowed Imports:**
- Data manipulation: `json`
- Date/time: `datetime`
- Text processing: `re`, `string`
- Math/stats: `math`, `statistics`, `decimal`, `fractions`
- Data structures: `collections`, `itertools`, `functools`
- Type hints: `typing`

**Blocked Operations:**
- Network operations (requests, urllib, socket, http.client)
- Code injection (eval, exec, __import__, compile)
- Subprocess/system access (subprocess, os.system, os.popen)

### ATTACK_SIMULATION Mode

**Purpose:** Realistic adversarial attack code generation

**Use Case:** Adversarial Agent creating novel attack patterns

**Timeout:** 30 seconds (default)

**Allowed Imports:** All RESTRICTED imports plus:
- Randomization: `random`
- Encoding/hashing: `base64`, `hashlib`, `uuid`, `hmac`, `secrets`

**Blocked Operations:** Same as RESTRICTED mode
- Network operations still blocked to prevent real data exfiltration
- Code injection still blocked for safety

**Additional Logging:** All executions tagged with "ATTACK_SIM" for audit trail

## Security Model

### Daytona Cloud Isolation

The Python-Executor trusts Daytona's cloud-based sandbox for:
- File system restrictions (cannot access host files)
- Process isolation (cannot spawn processes on host)
- Memory limits (enforced by Daytona)

### Application-Level Controls

The Python-Executor implements:
- Import whitelisting (mode-specific)
- Dangerous pattern scanning (network ops, code injection)
- Execution timeouts (mode-specific)
- Code hash logging for audit trail

### Validation Flow

1. Validate code is not empty
2. Select configuration based on execution_mode
3. Scan for dangerous patterns using mode-specific pattern list
4. Validate imports against mode-specific whitelist
5. Execute in Daytona sandbox with appropriate timeout
6. Capture stdout, stderr, return value
7. Return results with execution_mode tag

## Error Handling

### Validation Errors
- Empty code
- Blocked imports
- Dangerous patterns detected

### Execution Errors
- Timeout exceeded
- Python exceptions (with full traceback)
- Unexpected errors

All errors return structured responses with:
- `error.type`: Error category
- `error.message`: Human-readable description
- `error.details`: Additional context (code hash, execution mode)
- `error.traceback`: Full traceback (for exceptions)

## Logging

All operations are logged to `logs/python_executor.log`:

- Code execution attempts (with SHA-256 hash)
- Validation failures
- Execution results (success/failure)
- Execution time and mode
- Exception details with traceback

**Log Format:**
```
2024-01-15 10:30:00 - INFO - Executing code (hash: abc123..., mode: restricted, timeout: 10s)
2024-01-15 10:30:00 - INFO - Code execution succeeded (hash: abc123..., mode: restricted, time: 45.2ms)
```

## ADK Agent Integration

### Tool Discovery

The Python-Executor registers with ADK via `mcp_config.json`:

```json
{
  "mcpServers": {
    "python-executor": {
      "command": "python",
      "args": ["-m", "mcp_servers.python_executor.server"],
      "transport": "stdio"
    }
  }
}
```

### Example Agent Workflow

```python
# Data Engineering Agent workflow
from google.adk import Agent

agent = Agent()

# 1. Check allowed imports
imports = agent.use_tool("list_allowed_imports", {
    "execution_mode": "restricted"
})
print(f"Available modules: {imports['allowed_imports']}")

# 2. Execute data analysis code
result = agent.use_tool("execute_code", {
    "code": """
import json
import statistics

# Analyze event file sizes
events = [{"size": 1024}, {"size": 2048}]
avg = statistics.mean([e["size"] for e in events])
print(f"Average size: {avg}")
""",
    "execution_mode": "restricted"
})

print(result["stdout"])  # "Average size: 1536"
```

## Testing

Run the test suite:

```bash
python tests/test_list_allowed_imports.py
```

Tests cover:
- Import whitelisting for both modes
- Mode differences (attack_simulation is superset of restricted)
- MCP tool invocation
- Default mode behavior
- Invalid mode rejection
- Error handling

## Requirements Satisfied

- **5.1**: Execute Python code with execution_mode and timeout parameters
- **5.3**: RESTRICTED mode with minimal imports
- **5.4**: ATTACK_SIMULATION mode with expanded imports
- **5.5**: Block code injection patterns in both modes
- **5.6**: Enforce mode-specific timeouts (10s restricted, 30s attack_sim)
- **5.7**: Block network operations in both modes
- **5.8**: Block code injection patterns before execution
- **5.9**: Return structured error responses with exception details
- **5.10**: Capture stdout and stderr from executed code
- **5.11**: list_allowed_imports tool with mode parameter
- **5.12**: Log all code execution with hash and mode
- **5.13**: Return execution_mode tag in all responses
- **5.15**: Trust Daytona for file system and process restrictions

## Architecture Notes

### Why Two Modes?

The dual-mode design balances security with functionality:

- **RESTRICTED mode** prevents accidental or malicious misuse by Data Engineering Agents
- **ATTACK_SIMULATION mode** enables Adversarial Agents to generate realistic attack patterns without compromising security

Both modes block network operations to prevent real data exfiltration, even in attack simulation scenarios.

### Why Trust Daytona?

Daytona provides enterprise-grade cloud isolation:
- Containerized execution environment
- File system virtualization
- Process isolation
- Resource limits

The Python-Executor focuses on preventing API abuse (network calls, code injection) while trusting Daytona for infrastructure-level isolation.

## Future Enhancements

Potential improvements for Phase 3:

1. **Custom import whitelists**: Allow agents to request additional modules
2. **Resource monitoring**: Track memory and CPU usage per execution
3. **Execution history**: Store code hashes and results for audit trail
4. **Rate limiting**: Prevent abuse by limiting executions per agent
5. **Code templates**: Pre-approved code snippets for common tasks
