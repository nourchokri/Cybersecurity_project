#!/usr/bin/env python3
"""
CERT r4.2 Dataset Converter

Converts CERT Insider Threat Test Dataset r4.2 attack scenarios
to attack_patterns.json format compatible with Attack-Injector MCP.

Usage:
    python data/attacks/cert_converter.py --cert-dir r4.2/answers --output data/attacks/attack_patterns.json --merge --limit 10

CERT Dataset: https://kilthub.cmu.edu/articles/dataset/Insider_Threat_Test_Dataset/12841247
"""

import argparse
import json
import csv
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict


# Mapping from CERT event types to StandardEvent schema
CERT_EVENT_TYPE_MAPPING = {
    "logon": {"event_type": "logon", "event_category": "system", "action": "logon"},
    "logoff": {"event_type": "logoff", "event_category": "system", "action": "logoff"},
    "device": {"event_type": "device_connect", "event_category": "device", "action": "connect"},
    "file": {"event_type": "file_access", "event_category": "file", "action": "write"},
    "email": {"event_type": "email_sent", "event_category": "email", "action": "send"},
    "http": {"event_type": "http_request", "event_category": "web", "action": "request"},
}

# MITRE ATT&CK technique mapping for CERT scenarios (from scenarios.txt)
CERT_SCENARIO_MITRE_MAPPING = {
    1: {"technique": "T1052.001", "category": "data_exfiltration", "name": "USB Exfiltration + Wikileaks"},
    2: {"technique": "T1052.001", "category": "data_exfiltration", "name": "Job Hunting + USB Theft"},
    3: {"technique": "T1056.001", "category": "credential_access", "name": "Keylogger + Impersonation"},
    4: {"technique": "T1114.002", "category": "data_exfiltration", "name": "Unauthorized Access + Email Exfil"},
    5: {"technique": "T1567.002", "category": "data_exfiltration", "name": "Dropbox Upload After Layoff"},
}

# Severity mapping
CERT_SCENARIO_SEVERITY = {
    1: "critical",  # Wikileaks upload
    2: "high",      # USB theft
    3: "critical",  # Keylogger + impersonation
    4: "high",      # Email exfiltration
    5: "medium",    # Dropbox upload
}


def parse_insiders_csv(cert_dir: Path) -> List[Dict[str, Any]]:
    """
    Parse CERT r4.2 insiders.csv for labeled attack scenarios.
    
    Args:
        cert_dir: Path to CERT r4.2 answers/ directory
    
    Returns:
        List of insider threat instances with metadata
    """
    insiders_file = cert_dir / "insiders.csv"
    
    if not insiders_file.exists():
        print(f"Error: insiders.csv not found at {insiders_file}")
        return []
    
    insiders = []
    
    print(f"Parsing {insiders_file}...")
    
    try:
        with open(insiders_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                # Filter for r4.2 dataset only
                if row.get('dataset') == '4.2':
                    insiders.append({
                        "dataset": row['dataset'],
                        "scenario": int(row['scenario']),
                        "details_file": row['details'],
                        "user": row['user'],
                        "start": row['start'],
                        "end": row['end']
                    })
    
    except Exception as e:
        print(f"Error parsing insiders.csv: {e}")
        return []
    
    print(f"Found {len(insiders)} r4.2 insider threat instances")
    return insiders


def parse_cert_detail_file(cert_dir: Path, details_file: str) -> List[Dict[str, Any]]:
    """
    Parse a CERT r4.2 detail file for a specific insider threat instance.
    
    The detail files have variable-length rows with format:
    event_type,id,timestamp,user,pc,activity[,content]
    
    Args:
        cert_dir: Path to CERT r4.2 answers/ directory
        details_file: Name of the details file (e.g., 'r4.2-1-AAM0658.csv')
    
    Returns:
        List of parsed events
    """
    # Determine subdirectory based on filename pattern
    # r4.2-1-*.csv -> r4.2-1/
    # r4.2-2-*.csv -> r4.2-2/
    # r4.2-3-*.csv -> r4.2-3/
    
    parts = details_file.split('-')
    if len(parts) >= 3:
        subdir = f"{parts[0]}-{parts[1]}"
        detail_path = cert_dir / subdir / details_file
    else:
        detail_path = cert_dir / details_file
    
    if not detail_path.exists():
        print(f"Warning: Detail file not found: {detail_path}")
        return []
    
    events = []
    
    try:
        with open(detail_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                
                # Split by comma (CSV format)
                parts = line.split(',')
                
                if len(parts) < 6:
                    continue
                
                event_type = parts[0].lower()
                event_id = parts[1]
                timestamp = parts[2]
                user = parts[3]
                pc = parts[4]
                activity = parts[5]
                content = parts[6] if len(parts) > 6 else ""
                
                events.append({
                    "event_type": event_type,
                    "event_id": event_id,
                    "timestamp": timestamp,
                    "user": user,
                    "pc": pc,
                    "activity": activity,
                    "content": content
                })
    
    except Exception as e:
        print(f"Error parsing {detail_path}: {e}")
        return []
    
    return events


def calculate_time_offsets(events: List[Dict[str, Any]]) -> List[Tuple[int, int]]:
    """
    Calculate time offsets for events relative to the last event.
    
    Args:
        events: List of events with timestamps
    
    Returns:
        List of (min_offset, max_offset) tuples in minutes
    """
    if not events:
        return []
    
    # Parse timestamps
    timestamps = []
    for event in events:
        try:
            ts = datetime.strptime(event['timestamp'], '%m/%d/%Y %H:%M:%S')
            timestamps.append(ts)
        except:
            timestamps.append(None)
    
    # Calculate offsets relative to last event
    last_ts = timestamps[-1]
    if last_ts is None:
        # Fallback to evenly spaced offsets
        return [[-(len(events) - i) * 5, -(len(events) - i) * 3] for i in range(len(events))]
    
    offsets = []
    for i, ts in enumerate(timestamps):
        if ts is None:
            # Fallback
            offset = -(len(events) - i) * 5
            offsets.append([offset, offset])
        else:
            delta = (ts - last_ts).total_seconds() / 60  # Convert to minutes
            # Add some variance (+/- 20%)
            variance = abs(delta) * 0.2
            offsets.append([int(delta - variance), int(delta + variance)])
    
    return offsets


def convert_cert_instance_to_pattern(
    insider: Dict[str, Any],
    events: List[Dict[str, Any]]
) -> Optional[Dict[str, Any]]:
    """
    Convert a CERT insider threat instance to attack_patterns.json format.
    
    Args:
        insider: Insider metadata from insiders.csv
        events: List of events from detail file
    
    Returns:
        Attack pattern dictionary or None if conversion fails
    """
    if not events:
        print(f"Warning: No events for {insider['details_file']}")
        return None
    
    scenario_num = insider['scenario']
    scenario_info = CERT_SCENARIO_MITRE_MAPPING.get(scenario_num, {
        "technique": "T1041",
        "category": "data_exfiltration",
        "name": f"Unknown Scenario {scenario_num}"
    })
    
    # Build event sequence
    sequence = []
    time_offsets = calculate_time_offsets(events)
    
    # Limit to 10 events for pattern (representative sample)
    sampled_events = events[:10]
    sampled_offsets = time_offsets[:10]
    
    for idx, (event, offset) in enumerate(zip(sampled_events, sampled_offsets), start=1):
        event_type = event['event_type']
        
        # Map CERT event type to StandardEvent
        event_mapping = CERT_EVENT_TYPE_MAPPING.get(event_type, {
            "event_type": "file_access",
            "event_category": "file",
            "action": "read"
        })
        
        # Determine resource pattern
        resource = event.get('content', 'unknown')
        if event_type == 'device':
            resource = f"USB_DEVICE_{event.get('activity', 'unknown')}"
        elif event_type == 'http':
            # Extract domain from content
            if 'wikileaks' in resource.lower():
                resource = "http://wikileaks.org/*"
            elif 'dropbox' in resource.lower():
                resource = "http://dropbox.com/*"
            else:
                resource = "http://external_site/*"
        elif event_type == 'file':
            resource = f"E:\\{event.get('activity', 'file.txt')}"
        elif event_type == 'email':
            resource = "email_to_external"
        
        # Build metadata
        metadata = {"sensitivity_level": 1}
        
        if event_type == 'device':
            metadata["device_type"] = "usb_storage"
        elif event_type == 'file':
            metadata["is_usb"] = True
            metadata["file_size_bytes"] = [1000000, 10000000]
        elif event_type == 'email':
            metadata["external_recipient_count"] = 1
            metadata["attachment_count"] = [0, 2]
        
        sequence.append({
            "step": idx,
            "event_type": event_mapping["event_type"],
            "event_category": event_mapping["event_category"],
            "action": event_mapping["action"],
            "resource_patterns": [resource],
            "time_offset_minutes": offset,
            "metadata": metadata
        })
    
    # Build pattern ID
    pattern_id = f"cert_r42_s{scenario_num}_{insider['user'].lower()}"
    
    # Build pattern
    pattern = {
        "id": pattern_id,
        "name": f"CERT r4.2 - {scenario_info['name']}",
        "category": scenario_info['category'],
        "subcategory": "cert_dataset",
        "mitre_technique": scenario_info['technique'],
        "severity": CERT_SCENARIO_SEVERITY.get(scenario_num, 'medium'),
        "description": f"Real insider threat from CERT r4.2 dataset - Scenario {scenario_num}",
        "sequence": sequence,
        "source": "cert_r4.2",
        "cert_metadata": {
            "scenario": scenario_num,
            "user": insider['user'],
            "start_date": insider['start'],
            "end_date": insider['end'],
            "details_file": insider['details_file']
        }
    }
    
    return pattern


def main():
    parser = argparse.ArgumentParser(description="Convert CERT r4.2 dataset to attack_patterns.json")
    parser.add_argument("--cert-dir", required=True, help="Path to CERT r4.2 answers/ directory")
    parser.add_argument("--output", default="data/attacks/attack_patterns.json", help="Output file path")
    parser.add_argument("--merge", action="store_true", help="Merge with existing patterns")
    parser.add_argument("--limit", type=int, default=10, help="Limit number of instances to convert (default: 10)")
    parser.add_argument("--scenario", type=int, help="Convert only specific scenario number (1-5)")
    
    args = parser.parse_args()
    
    cert_dir = Path(args.cert_dir)
    output_path = Path(args.output)
    
    if not cert_dir.exists():
        print(f"Error: CERT directory not found: {cert_dir}")
        return 1
    
    print("=" * 60)
    print("CERT r4.2 Dataset Converter")
    print("=" * 60)
    print(f"Input: {cert_dir}")
    print(f"Output: {output_path}")
    print(f"Limit: {args.limit} instances")
    if args.scenario:
        print(f"Scenario filter: {args.scenario}")
    print()
    
    # Parse insiders.csv
    insiders = parse_insiders_csv(cert_dir)
    
    if not insiders:
        print("Error: No insider threat instances found")
        return 1
    
    # Filter by scenario if specified
    if args.scenario:
        insiders = [i for i in insiders if i['scenario'] == args.scenario]
        print(f"Filtered to {len(insiders)} instances for scenario {args.scenario}")
    
    # Limit number of instances
    if args.limit:
        insiders = insiders[:args.limit]
        print(f"Limited to {len(insiders)} instances")
    
    print()
    
    # Convert instances to patterns
    patterns = []
    
    for idx, insider in enumerate(insiders, start=1):
        print(f"[{idx}/{len(insiders)}] Converting {insider['details_file']}...")
        print(f"  User: {insider['user']}, Scenario: {insider['scenario']}")
        print(f"  Period: {insider['start']} to {insider['end']}")
        
        # Parse events from detail file
        events = parse_cert_detail_file(cert_dir, insider['details_file'])
        
        if not events:
            print(f"  ✗ No events found")
            continue
        
        print(f"  Found {len(events)} events")
        
        # Convert to pattern
        pattern = convert_cert_instance_to_pattern(insider, events)
        
        if pattern:
            patterns.append(pattern)
            print(f"  OK Converted to pattern: {pattern['id']}")
        else:
            print(f"  ✗ Failed to convert")
        
        print()
    
    print("=" * 60)
    print(f"Converted {len(patterns)} patterns from CERT r4.2")
    print("=" * 60)
    print()
    
    # Load existing patterns if merging
    existing_patterns = []
    if args.merge and output_path.exists():
        print(f"Loading existing patterns from {output_path}...")
        try:
            with open(output_path, 'r', encoding='utf-8') as f:
                existing_data = json.load(f)
                existing_patterns = existing_data.get('attack_patterns', [])
            print(f"Found {len(existing_patterns)} existing patterns")
        except Exception as e:
            print(f"Warning: Could not load existing patterns: {e}")
    
    # Merge patterns (avoid duplicates by ID)
    existing_ids = {p['id'] for p in existing_patterns}
    new_patterns = [p for p in patterns if p['id'] not in existing_ids]
    
    all_patterns = existing_patterns + new_patterns
    
    # Create output dataset
    output_data = {
        "schema_version": "1.0",
        "description": "Insider threat attack patterns (custom + CERT r4.2)",
        "last_updated": datetime.now().isoformat(),
        "attack_patterns": all_patterns
    }
    
    # Write output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2)
    
    print(f"\nOK Wrote {len(all_patterns)} patterns to {output_path}")
    print(f"  - {len(existing_patterns)} existing patterns")
    print(f"  - {len(new_patterns)} new CERT patterns")
    print(f"  - {len(patterns) - len(new_patterns)} duplicates skipped")
    print()
    
    return 0


if __name__ == "__main__":
    exit(main())
