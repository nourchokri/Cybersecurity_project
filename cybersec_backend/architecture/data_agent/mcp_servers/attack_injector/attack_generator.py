"""
Attack Generator for Attack-Injector MCP Server

Generates realistic attack event sequences from dataset patterns.
Applies temporal patterns, randomization, and user/device mappings.
"""

import json
import random
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import uuid

from collectors.event_schema import StandardEvent, create_event
from mcp_servers.common.utils import setup_logger, create_error_response
from mcp_servers.attack_injector.dataset_loader import (
    get_pattern_by_id,
    filter_patterns,
    load_attack_patterns
)

logger = setup_logger("attack_injector.generator", "logs/attack_injector.log")

# Path to user/device mapping
USER_DEVICE_MAP_PATH = Path("data/enrichment/user_device_map.json")

# Cache for user/device mappings
_user_device_map: Optional[Dict[str, Any]] = None


def load_user_device_map() -> Dict[str, Any]:
    """Load user/device mappings from JSON file."""
    global _user_device_map
    
    if _user_device_map is not None:
        return _user_device_map
    
    try:
        if not USER_DEVICE_MAP_PATH.exists():
            logger.warning(f"User/device map not found: {USER_DEVICE_MAP_PATH}")
            return {"users": {}, "devices": {}}
        
        with open(USER_DEVICE_MAP_PATH, 'r', encoding='utf-8') as f:
            _user_device_map = json.load(f)
        
        logger.info(f"Loaded {len(_user_device_map.get('users', {}))} users and {len(_user_device_map.get('devices', {}))} devices")
        return _user_device_map
    
    except Exception as e:
        logger.error(f"Failed to load user/device map: {e}")
        return {"users": {}, "devices": {}}



def select_random_user_device() -> tuple[str, str]:
    """
    Select a random user and one of their devices.
    
    Returns:
        Tuple of (user_id, device_id)
    """
    user_device_map = load_user_device_map()
    users = user_device_map.get("users", {})
    
    if not users:
        logger.warning("No users in mapping, using default")
        return "U001", "WORKSTATION-01"
    
    # Select random user
    user_id = random.choice(list(users.keys()))
    user_data = users[user_id]
    
    # Select random device from user's devices
    devices = user_data.get("devices", [])
    if not devices:
        logger.warning(f"User {user_id} has no devices, using default")
        return user_id, "WORKSTATION-01"
    
    device_id = random.choice(devices)
    
    logger.debug(f"Selected user {user_id} and device {device_id}")
    return user_id, device_id


def validate_user_device(user_id: str, device_id: str) -> bool:
    """
    Validate that user_id and device_id exist in mapping.
    
    Args:
        user_id: User identifier
        device_id: Device identifier
    
    Returns:
        True if valid, False otherwise
    """
    user_device_map = load_user_device_map()
    
    users = user_device_map.get("users", {})
    devices = user_device_map.get("devices", {})
    
    if user_id not in users:
        logger.warning(f"User {user_id} not found in mapping")
        return False
    
    if device_id not in devices:
        logger.warning(f"Device {device_id} not found in mapping")
        return False
    
    return True



def generate_events_from_pattern(
    pattern: Dict[str, Any],
    user_id: str,
    device_id: str,
    randomize: bool = True
) -> List[StandardEvent]:
    """
    Generate StandardEvent objects from an attack pattern.
    
    Args:
        pattern: Attack pattern dictionary from dataset
        user_id: User identifier
        device_id: Device identifier
        randomize: Apply timing and resource randomization
    
    Returns:
        List of StandardEvent objects
    """
    events = []
    base_time = datetime.now()
    
    # Get pattern metadata
    attack_id = pattern["id"]
    attack_name = pattern["name"]
    category = pattern["category"]
    mitre_technique = pattern["mitre_technique"]
    
    logger.info(f"Generating attack: {attack_id} for user {user_id} on device {device_id}")
    
    # Process each step in the sequence
    for step_data in pattern["sequence"]:
        step_num = step_data["step"]
        event_type = step_data["event_type"]
        event_category = step_data["event_category"]
        action = step_data["action"]
        resource_patterns = step_data["resource_patterns"]
        time_offset_range = step_data["time_offset_minutes"]
        step_metadata = step_data.get("metadata", {})
        
        # Select resource (random from patterns)
        resource = random.choice(resource_patterns)
        
        # Replace wildcards in resource
        resource = resource.replace("*", user_id)
        
        # Calculate timestamp with offset
        if randomize:
            time_offset = random.uniform(time_offset_range[0], time_offset_range[1])
        else:
            time_offset = time_offset_range[0]
        
        event_time = base_time + timedelta(minutes=time_offset)
        
        # Build event metadata
        event_metadata = {}
        
        # Copy step metadata and apply randomization
        for key, value in step_metadata.items():
            if isinstance(value, list) and len(value) == 2:
                # Randomize range values (or use first value if not randomizing)
                if randomize:
                    event_metadata[key] = random.randint(value[0], value[1])
                else:
                    event_metadata[key] = value[0]  # Use first value when not randomizing
            else:
                event_metadata[key] = value
        
        # Add attack simulation markers
        event_metadata["is_simulated"] = True
        event_metadata["attack_type"] = category
        event_metadata["mitre_technique"] = mitre_technique
        event_metadata["attack_id"] = attack_id
        event_metadata["attack_name"] = attack_name
        event_metadata["attack_step"] = step_num
        
        # Create StandardEvent
        event = create_event(
            event_type=event_type,
            event_category=event_category,
            action=action,
            resource=resource,
            user_id=user_id,
            device_id=device_id,
            source="attack_simulation",
            timestamp=event_time.isoformat(),
            **event_metadata
        )
        
        events.append(event)
        logger.debug(f"Generated event step {step_num}: {event_type} - {resource}")
    
    logger.info(f"Generated {len(events)} events for attack {attack_id}")
    return events



def inject_attack(
    attack_id: Optional[str] = None,
    category: Optional[str] = None,
    mitre_technique: Optional[str] = None,
    severity: Optional[str] = None,
    user_id: Optional[str] = None,
    device_id: Optional[str] = None,
    randomize: bool = True
) -> Dict[str, Any]:
    """
    Inject an attack simulation by generating events from dataset patterns.
    
    Args:
        attack_id: Specific attack pattern ID
        category: Filter by category
        mitre_technique: Filter by MITRE technique
        severity: Filter by severity level
        user_id: User to simulate attack for (random if not provided)
        device_id: Device to simulate attack on (random if not provided)
        randomize: Apply timing and resource randomization
    
    Returns:
        Dictionary with generated events and metadata
    """
    try:
        # Select attack pattern
        if attack_id:
            pattern = get_pattern_by_id(attack_id)
            if not pattern:
                return create_error_response(
                    "validation_error",
                    f"Attack pattern not found: {attack_id}",
                    {"attack_id": attack_id}
                )
        else:
            # Filter patterns by criteria
            patterns = filter_patterns(category, mitre_technique, severity)
            
            if not patterns:
                return create_error_response(
                    "validation_error",
                    "No attack patterns match the specified criteria",
                    {
                        "category": category,
                        "mitre_technique": mitre_technique,
                        "severity": severity
                    }
                )
            
            # Select random pattern from filtered results
            pattern = random.choice(patterns)
            logger.info(f"Selected random pattern: {pattern['id']}")
        
        # Select user and device
        if not user_id or not device_id:
            user_id, device_id = select_random_user_device()
        else:
            # Validate provided user/device
            if not validate_user_device(user_id, device_id):
                logger.warning(f"Invalid user/device: {user_id}/{device_id}, using random")
                user_id, device_id = select_random_user_device()
        
        # Generate events from pattern
        events = generate_events_from_pattern(pattern, user_id, device_id, randomize)
        
        # Convert events to dictionaries
        event_dicts = [event.model_dump() for event in events]
        
        return {
            "events": event_dicts,
            "count": len(event_dicts),
            "attack_id": pattern["id"],
            "attack_name": pattern["name"],
            "attack_type": pattern["category"],
            "mitre_technique": pattern["mitre_technique"],
            "severity": pattern["severity"],
            "description": pattern["description"],
            "user_id": user_id,
            "device_id": device_id,
            "randomized": randomize
        }
    
    except Exception as e:
        logger.error(f"Failed to inject attack: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return create_error_response(
            "internal_error",
            f"Failed to inject attack: {str(e)}",
            {
                "attack_id": attack_id,
                "category": category,
                "mitre_technique": mitre_technique
            }
        )
