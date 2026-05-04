# Attack-Injector MCP Server

The Attack-Injector MCP Server generates realistic attack simulations based on MITRE ATT&CK techniques. It uses a dataset-driven architecture where attack patterns are defined in `data/attacks/attack_patterns.json` and can be injected into the event stream for testing detection algorithms and training behavior analysis models.

## Architecture

### Dataset-Driven Approach

The Attack-Injector uses a JSON dataset (`data/attacks/attack_patterns.json`) that defines attack patterns with:
- **Attack metadata**: ID, name, category, MITRE technique, severity, description
- **Event sequences**: Step-by-step event patterns with timing offsets
- **Randomization parameters**: Ranges for file sizes, timing variations, resource selection

This approach allows for:
- Easy addition of new attack patterns without code changes
- Realistic temporal patterns (5-30 minute attack windows)
- Randomization of resources, timing, and file sizes
- Integration with CERT r4.2 dataset (via converter)

### Components

1. **server.py**: MCP server implementation with stdio transport
2. **dataset_loader.py**: Loads and caches attack patterns from JSON dataset
3. **attack_generator.py**: Generates StandardEvent objects from patterns
4. **data/attacks/attack_patterns.json**: Attack pattern dataset

## Available Tools

### 1. inject_attack

Generate realistic attack simulation events from dataset patterns.

**Parameters:**
- `attack_id` (string, optional): Specific attack pattern ID (e.g., 'usb_exfil_financial_001')
- `category` (string, optional): Filter by category ('data_exfiltration', 'credential_access', 'discovery')
- `mitre_technique` (string, optional): Filter by MITRE ATT&CK technique (e.g., 'T1052.001')
- `severity` (string, optional): Filter by severity ('low', 'medium', 'high', 'critical')
- `user_id` (string, optional): User to simulate attack for (random if not provided)
- `device_id` (string, optional): Device to simulate attack on (random if not provided)
- `randomize` (boolean, optional): Apply timing/resource randomization (default: true)

**Returns:**
```json
{
  "events": [
    {
      "event_id": "uuid",
      "timestamp": "2024-01-15T10:00:00",
      "user_id": "U003",
      "device_id": "WORKSTATION-FIN-01",
      "event_type": "file_access",
      "event_category": "file",
      "action": "read",
      "resource": "C:\\Finance\\Q4_Budget.xlsx",
      "metadata": {
        "sensitivity_level": 2,
        "file_size_bytes": 5242880,
        "is_simulated": true,
        "attack_type": "data_exfiltration",
        "mitre_technique": "T1052.001",
        "attack_id": "usb_exfil_financial_001",
        "attack_name": "USB Exfiltration - Financial Documents",
        "attack_step": 1
      },
      "source": "attack_simulation"
    }
  ],
  "count": 3,
  "attack_id": "usb_exfil_financial_001",
  "attack_name": "USB Exfiltration - Financial Documents",
  "attack_type": "data_exfiltration",
  "mitre_technique": "T1052.001",
  "severity": "high",
  "description": "Employee copies sensitive financial documents to USB drive",
  "user_id": "U003",
  "device_id": "WORKSTATION-FIN-01",
  "randomized": true
}
```

**Example Usage:**

```python
# Inject specific attack pattern
result = await agent.call_tool(
    "inject_attack",
    {"attack_id": "usb_exfil_financial_001"}
)

# Inject random data exfiltration attack
result = await agent.call_tool(
    "inject_attack",
    {"category": "data_exfiltration", "randomize": true}
)

# Inject attack for specific user
result = await agent.call_tool(
    "inject_attack",
    {
        "mitre_technique": "T1114.002",
        "user_id": "U003",
        "device_id": "WORKSTATION-FIN-01"
    }
)
```

### 2. list_attack_patterns

List all available attack patterns from dataset with optional filtering.

**Parameters:**
- `category` (string, optional): Filter by category
- `mitre_technique` (string, optional): Filter by MITRE technique
- `severity` (string, optional): Filter by severity level

**Returns:**
```json
{
  "patterns": [
    {
      "id": "usb_exfil_financial_001",
      "name": "USB Exfiltration - Financial Documents",
      "category": "data_exfiltration",
      "subcategory": "physical_medium",
      "mitre_technique": "T1052.001",
      "severity": "high",
      "description": "Employee copies sensitive financial documents to USB drive",
      "event_count": 3
    }
  ],
  "count": 1,
  "filters_applied": {
    "category": "data_exfiltration",
    "mitre_technique": null,
    "severity": null
  }
}
```

**Example Usage:**

```python
# List all patterns
result = await agent.call_tool("list_attack_patterns", {})

# List high-severity patterns
result = await agent.call_tool(
    "list_attack_patterns",
    {"severity": "high"}
)

# List credential theft patterns
result = await agent.call_tool(
    "list_attack_patterns",
    {"category": "credential_access"}
)
```

### 3. add_attack_pattern

Add a new attack pattern to the dataset (optional).

**Parameters:**
- `pattern` (object, required): Attack pattern object conforming to dataset schema

**Returns:**
```json
{
  "success": true,
  "message": "Attack pattern 'custom_attack_001' added successfully",
  "pattern_id": "custom_attack_001"
}
```

**Example Usage:**

```python
new_pattern = {
    "id": "custom_attack_001",
    "name": "Custom Attack Pattern",
    "category": "data_exfiltration",
    "subcategory": "network",
    "mitre_technique": "T1041",
    "severity": "high",
    "description": "Custom attack description",
    "sequence": [
        {
            "step": 1,
            "event_type": "file_access",
            "event_category": "file",
            "action": "read",
            "resource_patterns": ["C:\\Data\\sensitive.txt"],
            "time_offset_minutes": [-10, -5],
            "metadata": {"sensitivity_level": 2}
        }
    ]
}

result = await agent.call_tool(
    "add_attack_pattern",
    {"pattern": new_pattern}
)
```

## Attack Pattern Schema

Attack patterns in `data/attacks/attack_patterns.json` follow this schema:

```json
{
  "id": "unique_attack_id",
  "name": "Human-readable attack name",
  "category": "data_exfiltration | credential_access | discovery",
  "subcategory": "physical_medium | email | network | password_stores | file_directory",
  "mitre_technique": "T1052.001",
  "severity": "low | medium | high | critical",
  "description": "Detailed attack description",
  "sequence": [
    {
      "step": 1,
      "event_type": "file_access | device_connect | email_sent | network_connection",
      "event_category": "file | device | email | network",
      "action": "read | write | connect | send",
      "resource_patterns": ["C:\\Path\\File.txt", "E:\\USB\\File.txt"],
      "time_offset_minutes": [-15, -10],
      "metadata": {
        "sensitivity_level": 2,
        "file_size_bytes": [1000000, 5000000],
        "is_usb": true
      }
    }
  ]
}
```

### Key Fields

- **time_offset_minutes**: `[min, max]` range relative to attack completion time (negative = before, 0 = at completion)
- **resource_patterns**: Array of possible resource strings (one selected randomly)
- **metadata**: Event-specific metadata with optional randomization ranges `[min, max]`

## Adding Custom Attack Patterns

### Method 1: Direct JSON Editing

Edit `data/attacks/attack_patterns.json` and add your pattern to the `attack_patterns` array:

```json
{
  "schema_version": "1.0",
  "attack_patterns": [
    {
      "id": "my_custom_attack",
      "name": "My Custom Attack",
      "category": "data_exfiltration",
      "mitre_technique": "T1041",
      "severity": "high",
      "description": "Description of attack",
      "sequence": [...]
    }
  ]
}
```

### Method 2: Using add_attack_pattern Tool

Use the `add_attack_pattern` tool to programmatically add patterns (see example above).

## CERT r4.2 Dataset Integration

The Attack-Injector supports integration with the CERT Insider Threat r4.2 dataset through a converter utility.

### Using the CERT Converter

```bash
# Convert CERT r4.2 scenarios to attack patterns
python data/attacks/cert_converter.py \
    --cert-dir /path/to/cert/r4.2/answers \
    --output data/attacks/attack_patterns.json \
    --merge
```

The converter:
1. Parses CERT r4.2 `answers/` directory for labeled attack scenarios
2. Extracts attack metadata (user, dates, scenario description)
3. Maps CERT event types to StandardEvent schema
4. Converts sequences to attack_patterns.json format
5. Merges with existing custom patterns (if `--merge` flag used)

## Integration with Event-Storage MCP

Generated attack events are StandardEvent dictionaries compatible with Event-Storage MCP:

```python
# Inject attack
attack_result = await agent.call_tool(
    "inject_attack",
    {"attack_id": "usb_exfil_financial_001"}
)

# Store generated events
storage_result = await agent.call_tool(
    "store_events",
    {"events": attack_result["events"]}
)
```

## User/Device Selection

The Attack-Injector loads user/device mappings from `data/enrichment/user_device_map.json`:

- If `user_id`/`device_id` not provided, selects random user and one of their devices
- Validates provided user/device IDs against mapping
- Falls back to random selection if validation fails

## Simulation Markers

All generated events include simulation metadata:

```json
{
  "metadata": {
    "is_simulated": true,
    "attack_type": "data_exfiltration",
    "mitre_technique": "T1052.001",
    "attack_id": "usb_exfil_financial_001",
    "attack_name": "USB Exfiltration - Financial Documents",
    "attack_step": 1
  }
}
```

This allows downstream systems to:
- Filter out simulated events for production analysis
- Identify attack patterns for training ML models
- Track attack sequences across multiple events

## Logging

All operations are logged to `logs/attack_injector.log`:

```
2024-01-15 10:30:00 - attack_injector - INFO - Starting Attack-Injector MCP Server
2024-01-15 10:30:05 - attack_injector.dataset_loader - INFO - Loaded 6 attack patterns
2024-01-15 10:30:10 - attack_injector.generator - INFO - Generating attack: usb_exfil_financial_001 for user U003 on device WORKSTATION-FIN-01
2024-01-15 10:30:10 - attack_injector.generator - INFO - Generated 3 events for attack usb_exfil_financial_001
```

## Error Handling

The server returns structured error responses:

```json
{
  "error": {
    "type": "validation_error",
    "message": "Attack pattern not found: invalid_id",
    "timestamp": "2024-01-15T10:30:00",
    "details": {
      "attack_id": "invalid_id"
    }
  }
}
```

Error types:
- `validation_error`: Invalid parameters or pattern not found
- `internal_error`: Unexpected server error

## Running the Server

```bash
# Start the server
python -m mcp_servers.attack_injector.server

# Or via MCP config (mcp_config.json)
{
  "mcpServers": {
    "attack-injector": {
      "command": "python",
      "args": ["-m", "mcp_servers.attack_injector.server"],
      "transport": "stdio"
    }
  }
}
```
