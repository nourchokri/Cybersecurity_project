# Python-Executor Hybrid Approach

## Overview

The Python-Executor MCP Server implements a **hybrid security model** with two execution modes to balance safety with functionality for different agent types.

## Why Hybrid?

### The Problem
- **Data Engineering Agents** need safe data processing (JSON parsing, statistics, filtering)
- **Adversarial Agents** need to generate realistic attack code (randomization, encoding, multi-stage logic)
- A single security profile can't serve both needs effectively

### The Solution
Two execution modes with different security profiles:
1. **RESTRICTED** - Default, safe mode for data analysis
2. **ATTACK_SIMULATION** - Permissive mode for adversarial agents

---

## Execution Modes

### RESTRICTED Mode (Default)

**Purpose**: Safe data analysis and transformation

**Use Cases**:
- Parse and analyze collected events
- Calculate statistics on event data
- Transform event formats
- Filter and aggregate data

**Security Profile**:
- **Timeout**: 10 seconds (default)
- **Allowed Imports**: json, csv, datetime, time, calendar, math, statistics, decimal, fractions, re, string, textwrap, collections, itertools, functools, heapq, typing
- **Blocked**: Network operations (requests, urllib, socket), code injection (eval, exec, __import__)

**Example**:
```python
execute_code(
    code="""
import json
import statistics

events = [{"size": 1024}, {"size": 2048}, {"size": 512}]
sizes = [e["size"] for e in events]
print(f"Average: {statistics.mean(sizes)}")
""",
    execution_mode="restricted"  # Default
)
```

---

### ATTACK_SIMULATION Mode

**Purpose**: Realistic adversarial attack code generation

**Use Cases**:
- Generate novel attack patterns dynamically
- Create multi-stage attack sequences
- Simulate credential theft, data exfiltration
- Adaptive attack strategies

**Security Profile**:
- **Timeout**: 30 seconds (default, longer for complex attacks)
- **Allowed Imports**: All RESTRICTED imports + random, base64, hashlib, uuid, hmac, secrets
- **Blocked**: Network operations (prevents real data exfiltration), code injection
- **Extra Logging**: All executions tagged with "ATTACK_SIM" for audit trail

**Example**:
```python
execute_code(
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
        "resource": "Chrome User Data",
        "is_simulated": True
    })
    
    # Stage 2: Encode stolen data
    fake_creds = base64.b64encode(b"admin:pass").decode()
    
    # Stage 3: Exfiltration attempt
    events.append({
        "timestamp": (base_time + timedelta(minutes=5)).isoformat(),
        "event_type": "network_connection",
        "bytes_sent": len(fake_creds),
        "is_simulated": True
    })
    
    return events

print(json.dumps(generate_credential_theft(), indent=2))
""",
    execution_mode="attack_simulation",
    timeout_seconds=30
)
```

---

## Security Boundaries

### What Both Modes Block

**Network Operations** (prevents data exfiltration):
- `requests.*`
- `urllib.*`
- `socket.*`
- `http.client`

**Code Injection** (prevents agent from modifying its own code):
- `eval()`
- `exec()`
- `__import__()`
- `compile()`

### What Daytona Cloud Isolation Handles

Since Daytona executes code in cloud-based containers, we **trust Daytona** for:
- **File system isolation** - Can't access host files
- **Process isolation** - Can't spawn processes on host
- **Memory limits** - Enforced by Daytona
- **Container escape prevention** - Daytona's responsibility

This is why we don't need to block `os.*`, `subprocess.*`, or file operations - Daytona's container already isolates them.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    AI Agent Layer                            │
│  (Data Engineering Agent | Adversarial Agent)                │
└────────────────────────┬────────────────────────────────────┘
                         │
                         │ execute_code(code, execution_mode)
                         │
┌────────────────────────┴────────────────────────────────────┐
│              Python-Executor MCP Server                      │
│                                                              │
│  ┌──────────────────┐         ┌──────────────────┐         │
│  │ RESTRICTED Mode  │         │ ATTACK_SIM Mode  │         │
│  │ - 10s timeout    │         │ - 30s timeout    │         │
│  │ - Safe imports   │         │ - Expanded imports│         │
│  │ - Network blocked│         │ - Network blocked│         │
│  └──────────────────┘         └──────────────────┘         │
│                                                              │
│         ┌────────────────────────────────┐                  │
│         │  Code Sanitization             │                  │
│         │  - Block network ops           │                  │
│         │  - Block code injection        │                  │
│         │  - Validate imports            │                  │
│         └────────────────────────────────┘                  │
└────────────────────────┬────────────────────────────────────┘
                         │
                         │ API Call
                         │
┌────────────────────────┴────────────────────────────────────┐
│                  Daytona Cloud Sandbox                       │
│  - Container isolation                                       │
│  - File system restrictions                                  │
│  - Process isolation                                         │
│  - Memory limits                                             │
└──────────────────────────────────────────────────────────────┘
```

---

## Benefits

1. **Safety by Default** - Most agents use RESTRICTED mode
2. **Flexibility for Adversarial** - Attack agents can be creative
3. **Defense in Depth** - Even ATTACK_SIMULATION mode has limits
4. **Auditability** - All ATTACK_SIMULATION executions logged separately
5. **Realistic Testing** - Adversarial agents can generate novel attacks
6. **Cost Protection** - Timeouts prevent API abuse

---

## Usage Guidelines

### For Data Engineering Agents
- Use **RESTRICTED mode** (default)
- Focus on data processing, not attack simulation
- Leverage safe imports for analysis

### For Adversarial Agents
- Use **ATTACK_SIMULATION mode** explicitly
- Generate creative attack patterns
- Combine multiple stages for realism
- Remember: Network is still blocked (no real exfiltration)

### For Developers
- Trust Daytona's cloud isolation
- Focus blocking on data exfiltration and code injection
- Don't redundantly block file/process operations
- Monitor ATTACK_SIM logs for audit trail

---

## Implementation Files

- `server.py` - MCP server with mode-aware tool definitions
- `sandbox_config.py` - Mode configurations, import whitelists, dangerous patterns
- `HYBRID_APPROACH.md` - This documentation

---

## Future Enhancements

1. **Additional Modes** - Could add "PRIVILEGED" mode for trusted agents
2. **Dynamic Timeouts** - Adjust based on code complexity
3. **Import Expansion** - Add more safe modules as needed
4. **Rate Limiting** - Prevent API abuse per agent
5. **Audit Dashboard** - Visualize ATTACK_SIM executions
