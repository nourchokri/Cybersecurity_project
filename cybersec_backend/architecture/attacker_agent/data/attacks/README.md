# Attack Pattern Dataset

## Overview

This directory contains attack pattern definitions used by the Attack-Injector MCP server to generate realistic insider threat simulations.

## Dataset Structure

### `attack_patterns.json`

Main dataset containing attack pattern definitions. Each pattern includes:

- **id**: Unique identifier for the attack pattern
- **name**: Human-readable name
- **category**: High-level category (data_exfiltration, credential_access, discovery, etc.)
- **subcategory**: More specific classification
- **mitre_technique**: MITRE ATT&CK technique ID
- **severity**: low, medium, high, critical
- **description**: What the attack simulates
- **sequence**: Array of event steps with timing and metadata

## Attack Pattern Schema

```json
{
  "id": "unique_attack_id",
  "name": "Attack Name",
  "category": "data_exfiltration",
  "subcategory": "physical_medium",
  "mitre_technique": "T1052.001",
  "severity": "high",
  "description": "What this attack simulates",
  "sequence": [
    {
      "step": 1,
      "event_type": "file_access",
      "event_category": "file",
      "action": "read",
      "resource_patterns": ["C:\\Path\\*.xlsx"],
      "time_offset_minutes": [-15, -10],
      "metadata": {
        "sensitivity_level": 2,
        "file_size_bytes": [2000000, 8000000]
      }
    }
  ]
}
```

## Field Descriptions

### Pattern-Level Fields

- **id**: Unique identifier (use descriptive naming: `category_subcategory_variant_###`)
- **name**: Descriptive name for the attack
- **category**: One of: `data_exfiltration`, `credential_access`, `discovery`, `lateral_movement`, `privilege_escalation`, `impact`
- **subcategory**: More specific classification
- **mitre_technique**: MITRE ATT&CK technique ID (e.g., T1052.001)
- **severity**: `low`, `medium`, `high`, `critical`
- **description**: Brief explanation of what the attack simulates

### Sequence Step Fields

- **step**: Sequential step number (1, 2, 3, ...)
- **event_type**: Type of event (file_access, device_connect, email_sent, network_connection, etc.)
- **event_category**: Category (file, device, email, network, system, etc.)
- **action**: Specific action (read, write, connect, send, etc.)
- **resource_patterns**: Array of possible resource strings (randomly selected)
- **time_offset_minutes**: [min, max] range for timing relative to attack completion
  - Negative values = before attack completion
  - 0 = attack completion time
  - Positive values = after attack completion
- **metadata**: Event-specific metadata fields

### Metadata Fields (varies by event type)

**File events:**
- `sensitivity_level`: 0 (low), 1 (medium), 2 (high)
- `file_size_bytes`: [min, max] range for file size
- `is_usb`: true/false (for USB-related file operations)

**Device events:**
- `device_type`: "usb_storage", "external_drive", etc.

**Email events:**
- `external_recipient_count`: Number of external recipients
- `attachment_count`: Number of attachments
- `attachment_size_bytes`: [min, max] range for attachment size

**Network events:**
- `dst_ip`: Destination IP address
- `protocol`: "HTTP", "HTTPS", "FTP", etc.
- `bytes_sent`: [min, max] range for data sent

## Current Attack Patterns

### Data Exfiltration (6 patterns)
1. **usb_exfil_financial_001**: USB exfiltration of financial documents
2. **usb_exfil_source_code_002**: USB exfiltration of source code
3. **email_exfil_customer_data_001**: Email exfiltration of customer database
4. **email_exfil_strategic_plans_002**: Email exfiltration of strategic plans

### Credential Access (1 pattern)
5. **credential_theft_browser_001**: Browser password theft

### Discovery (1 pattern)
6. **file_discovery_hr_001**: Unauthorized file discovery in HR directories

## Adding New Attack Patterns

To add a new attack pattern:

1. Choose a unique ID following the naming convention: `category_subcategory_variant_###`
2. Define the attack metadata (name, category, MITRE technique, severity)
3. Create the event sequence with realistic timing
4. Use resource patterns for variety (multiple possible file paths, IPs, etc.)
5. Add appropriate metadata for each event type
6. Test the pattern using the Attack-Injector MCP

### Example: Adding a New Pattern

```json
{
  "id": "lateral_movement_rdp_001",
  "name": "Lateral Movement via RDP",
  "category": "lateral_movement",
  "subcategory": "remote_services",
  "mitre_technique": "T1021.001",
  "severity": "high",
  "description": "Employee uses RDP to access unauthorized servers",
  "sequence": [
    {
      "step": 1,
      "event_type": "network_connection",
      "event_category": "network",
      "action": "connect",
      "resource_patterns": [
        "connection_to_192.168.1.50",
        "connection_to_192.168.1.51"
      ],
      "time_offset_minutes": [0, 0],
      "metadata": {
        "dst_ip": "192.168.1.50",
        "protocol": "RDP",
        "dst_port": 3389
      }
    }
  ]
}
```

## MITRE ATT&CK Technique Reference

Common insider threat techniques:

- **T1052.001**: Exfiltration Over Physical Medium (USB)
- **T1114.002**: Email Collection (Remote Email Collection)
- **T1555.003**: Credentials from Password Stores (Web Browsers)
- **T1083**: File and Directory Discovery
- **T1021.001**: Remote Services (RDP)
- **T1078**: Valid Accounts
- **T1486**: Data Encrypted for Impact (Ransomware)

Full reference: https://attack.mitre.org/

## Dataset Maintenance

- **Version**: Update `schema_version` when making breaking changes
- **Last Updated**: Update `last_updated` field when adding/modifying patterns
- **Validation**: Use the Attack-Injector's validation to ensure patterns are correct
- **Testing**: Test new patterns before deploying to production

## Future Enhancements

Potential additions:
- Privilege escalation patterns
- Lateral movement patterns
- Data destruction/ransomware patterns
- Multi-stage APT-style attacks
- Time-based attack variations (working hours vs. after hours)
- User role-specific attacks (admin vs. regular user)
