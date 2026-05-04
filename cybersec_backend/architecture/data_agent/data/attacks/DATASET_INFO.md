# Attack Pattern Dataset - Quick Reference

## What You Have

✅ **6 pre-built attack patterns** covering insider threats
✅ **Dataset-driven architecture** - no hardcoded attack logic
✅ **Extensible design** - add unlimited patterns via JSON
✅ **MITRE ATT&CK mapped** - industry-standard technique IDs

## Dataset Location

```
data/attacks/
├── attack_patterns.json    # Main dataset (6 patterns)
└── README.md               # Full documentation
```

## Current Attack Patterns

| ID | Name | Category | MITRE | Events | Severity |
|----|------|----------|-------|--------|----------|
| usb_exfil_financial_001 | USB Exfiltration - Financial Docs | data_exfiltration | T1052.001 | 3 | high |
| usb_exfil_source_code_002 | USB Exfiltration - Source Code | data_exfiltration | T1052.001 | 3 | critical |
| email_exfil_customer_data_001 | Email Exfiltration - Customer DB | data_exfiltration | T1114.002 | 3 | critical |
| email_exfil_strategic_plans_002 | Email Exfiltration - Strategic Plans | data_exfiltration | T1114.002 | 2 | high |
| credential_theft_browser_001 | Credential Theft - Browser Passwords | credential_access | T1555.003 | 4 | high |
| file_discovery_hr_001 | Unauthorized File Discovery - HR | discovery | T1083 | 5 | medium |

## No External Dataset Installation Required!

**You don't need to download anything.** The dataset is already created and ready to use.

### Why No External Dataset?

1. **Custom-built for your system**: Patterns match your StandardEvent schema
2. **Insider threat focused**: Specifically designed for your use case
3. **Lightweight**: Only 6 patterns to start (easily expandable)
4. **No dependencies**: Pure JSON, no external libraries needed

## How to Use

### 1. Generate an Attack

```python
# Via MCP tool
inject_attack(attack_id="usb_exfil_financial_001", user_id="U001")

# Or by category
inject_attack(category="data_exfiltration", randomize=True)

# Or by MITRE technique
inject_attack(mitre_technique="T1052.001")
```

### 2. List Available Patterns

```python
list_attack_patterns()
# Returns all 6 patterns with metadata
```

### 3. Add Your Own Pattern

```python
add_attack_pattern({
  "id": "my_custom_attack_001",
  "name": "My Custom Attack",
  "category": "data_exfiltration",
  "mitre_technique": "T1048",
  "severity": "high",
  "sequence": [/* event definitions */]
})
```

## Adding More Patterns

Want more attack types? You have 3 options:

### Option 1: Add Manually to JSON
Edit `data/attacks/attack_patterns.json` and add new patterns following the schema.

### Option 2: Use the MCP Tool
Use `add_attack_pattern` tool to add patterns programmatically.

### Option 3: Import from Research Datasets
Convert patterns from:
- **CERT Insider Threat Dataset**: https://kilthub.cmu.edu/articles/dataset/Insider_Threat_Test_Dataset/12841247
- **LANL Cyber Security Dataset**: https://csr.lanl.gov/data/cyber1/
- **DARPA Intrusion Detection**: https://www.ll.mit.edu/r-d/datasets

(You'll need to write a converter script to transform their format to ours)

## Pattern Randomization

Each pattern supports randomization:
- **Timing**: Random delays within specified ranges
- **Resources**: Random selection from resource_patterns array
- **File sizes**: Random values within [min, max] ranges
- **User/Device**: Random selection from user_device_map.json

This creates variety even with the same pattern!

## Example Generated Attack

**Pattern**: `usb_exfil_financial_001`

**Generated Events**:
```json
[
  {
    "event_id": "uuid-1",
    "timestamp": "2024-01-15T10:45:00",
    "event_type": "file_access",
    "action": "read",
    "resource": "C:\\Finance\\Q4_Budget.xlsx",
    "metadata": {
      "sensitivity_level": 2,
      "file_size_bytes": 5242880,
      "is_simulated": true,
      "attack_type": "usb_exfil_financial_001",
      "mitre_technique": "T1052.001"
    }
  },
  {
    "event_id": "uuid-2",
    "timestamp": "2024-01-15T10:57:00",
    "event_type": "device_connect",
    "action": "connect",
    "resource": "USB_DEVICE_VID_0781_PID_5567",
    "metadata": {
      "device_type": "usb_storage",
      "is_simulated": true,
      "attack_type": "usb_exfil_financial_001",
      "mitre_technique": "T1052.001"
    }
  },
  {
    "event_id": "uuid-3",
    "timestamp": "2024-01-15T11:00:00",
    "event_type": "file_access",
    "action": "write",
    "resource": "E:\\Financial_Data.xlsx",
    "metadata": {
      "is_usb": true,
      "sensitivity_level": 2,
      "file_size_bytes": 15728640,
      "is_simulated": true,
      "attack_type": "usb_exfil_financial_001",
      "mitre_technique": "T1052.001"
    }
  }
]
```

## Next Steps

1. ✅ Dataset is ready - no installation needed
2. ⏳ Implement Attack-Injector MCP (Task 6)
3. ⏳ Test with the 6 existing patterns
4. ⏳ Add more patterns as needed

## Questions?

- **How do I add more patterns?** See `README.md` for schema and examples
- **Can I use real attack datasets?** Yes, but you'll need to convert their format
- **How many patterns should I have?** Start with 6, add more based on testing needs
- **Can patterns overlap?** Yes! Multiple patterns can use the same MITRE technique

## Summary

✅ **No external dataset installation required**
✅ **6 ready-to-use attack patterns**
✅ **Fully documented schema**
✅ **Easy to extend**
✅ **MITRE ATT&CK compliant**

You're ready to implement the Attack-Injector MCP!
