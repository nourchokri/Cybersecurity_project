"""
Dataset Loader for Attack-Injector MCP Server

Loads and caches attack patterns from data/attacks/attack_patterns.json.
Provides filtering and validation capabilities.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

from mcp_servers.common.utils import setup_logger, create_error_response

logger = setup_logger("attack_injector.dataset_loader", "logs/attack_injector.log")

# Cache for loaded attack patterns
_attack_patterns_cache: Optional[Dict[str, Any]] = None
_cache_timestamp: Optional[float] = None

# Path to attack patterns dataset
DATASET_PATH = Path("data/attacks/attack_patterns.json")


def load_attack_patterns(force_reload: bool = False) -> Dict[str, Any]:
    """
    Load attack patterns from JSON dataset with caching.
    
    Args:
        force_reload: Force reload from disk even if cached
    
    Returns:
        Dictionary containing attack patterns dataset
    """
    global _attack_patterns_cache, _cache_timestamp
    
    # Check if we need to reload
    if not force_reload and _attack_patterns_cache is not None:
        # Check if file has been modified since cache
        if DATASET_PATH.exists():
            file_mtime = DATASET_PATH.stat().st_mtime
            if _cache_timestamp and file_mtime <= _cache_timestamp:
                logger.debug("Using cached attack patterns")
                return _attack_patterns_cache
    
    # Load from disk
    try:
        logger.info(f"Loading attack patterns from {DATASET_PATH}")
        
        if not DATASET_PATH.exists():
            logger.error(f"Attack patterns file not found: {DATASET_PATH}")
            return {
                "schema_version": "1.0",
                "description": "Attack patterns dataset",
                "last_updated": datetime.now().isoformat(),
                "attack_patterns": []
            }
        
        with open(DATASET_PATH, 'r', encoding='utf-8') as f:
            dataset = json.load(f)
        
        # Validate dataset schema
        if not validate_dataset_schema(dataset):
            logger.error("Invalid dataset schema")
            return {
                "schema_version": "1.0",
                "description": "Attack patterns dataset",
                "last_updated": datetime.now().isoformat(),
                "attack_patterns": []
            }
        
        # Cache the dataset
        _attack_patterns_cache = dataset
        _cache_timestamp = datetime.now().timestamp()
        
        logger.info(f"Loaded {len(dataset.get('attack_patterns', []))} attack patterns")
        return dataset
    
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse attack patterns JSON: {e}")
        return {
            "schema_version": "1.0",
            "description": "Attack patterns dataset",
            "last_updated": datetime.now().isoformat(),
            "attack_patterns": []
        }
    
    except Exception as e:
        logger.error(f"Failed to load attack patterns: {e}")
        return {
            "schema_version": "1.0",
            "description": "Attack patterns dataset",
            "last_updated": datetime.now().isoformat(),
            "attack_patterns": []
        }


def validate_dataset_schema(dataset: Dict[str, Any]) -> bool:
    """
    Validate that dataset conforms to expected schema.
    
    Args:
        dataset: Dataset dictionary to validate
    
    Returns:
        True if valid, False otherwise
    """
    required_fields = ["schema_version", "attack_patterns"]
    
    # Check required top-level fields
    for field in required_fields:
        if field not in dataset:
            logger.error(f"Missing required field: {field}")
            return False
    
    # Validate attack patterns array
    if not isinstance(dataset["attack_patterns"], list):
        logger.error("attack_patterns must be an array")
        return False
    
    # Validate each pattern
    for pattern in dataset["attack_patterns"]:
        if not validate_pattern_schema(pattern):
            return False
    
    return True


def validate_pattern_schema(pattern: Dict[str, Any]) -> bool:
    """
    Validate that an attack pattern conforms to expected schema.
    
    Args:
        pattern: Attack pattern dictionary to validate
    
    Returns:
        True if valid, False otherwise
    """
    required_fields = ["id", "name", "category", "mitre_technique", "severity", "description", "sequence"]
    
    for field in required_fields:
        if field not in pattern:
            logger.error(f"Pattern missing required field: {field}")
            return False
    
    # Validate sequence
    if not isinstance(pattern["sequence"], list) or len(pattern["sequence"]) == 0:
        logger.error(f"Pattern {pattern.get('id')} has invalid sequence")
        return False
    
    # Validate each step in sequence
    for step in pattern["sequence"]:
        required_step_fields = ["step", "event_type", "event_category", "action", "resource_patterns", "time_offset_minutes"]
        for field in required_step_fields:
            if field not in step:
                logger.error(f"Pattern {pattern.get('id')} step missing field: {field}")
                return False
    
    return True


def get_pattern_by_id(attack_id: str) -> Optional[Dict[str, Any]]:
    """
    Get a specific attack pattern by ID.
    
    Args:
        attack_id: Attack pattern ID
    
    Returns:
        Attack pattern dictionary or None if not found
    """
    dataset = load_attack_patterns()
    
    for pattern in dataset.get("attack_patterns", []):
        if pattern["id"] == attack_id:
            return pattern
    
    logger.warning(f"Attack pattern not found: {attack_id}")
    return None


def filter_patterns(
    category: Optional[str] = None,
    mitre_technique: Optional[str] = None,
    severity: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Filter attack patterns by criteria.
    
    Args:
        category: Filter by category (e.g., 'data_exfiltration')
        mitre_technique: Filter by MITRE technique (e.g., 'T1052.001')
        severity: Filter by severity level
    
    Returns:
        List of matching attack patterns
    """
    dataset = load_attack_patterns()
    patterns = dataset.get("attack_patterns", [])
    
    # Apply filters
    if category:
        patterns = [p for p in patterns if p.get("category") == category]
    
    if mitre_technique:
        patterns = [p for p in patterns if p.get("mitre_technique") == mitre_technique]
    
    if severity:
        patterns = [p for p in patterns if p.get("severity") == severity]
    
    return patterns


def list_attack_patterns(
    category: Optional[str] = None,
    mitre_technique: Optional[str] = None,
    severity: Optional[str] = None
) -> Dict[str, Any]:
    """
    List all available attack patterns with optional filtering.
    
    Args:
        category: Filter by category
        mitre_technique: Filter by MITRE technique
        severity: Filter by severity level
    
    Returns:
        Dictionary with patterns and metadata
    """
    patterns = filter_patterns(category, mitre_technique, severity)
    
    # Create summary for each pattern
    pattern_summaries = []
    for pattern in patterns:
        pattern_summaries.append({
            "id": pattern["id"],
            "name": pattern["name"],
            "category": pattern["category"],
            "subcategory": pattern.get("subcategory"),
            "mitre_technique": pattern["mitre_technique"],
            "severity": pattern["severity"],
            "description": pattern["description"],
            "event_count": len(pattern["sequence"])
        })
    
    return {
        "patterns": pattern_summaries,
        "count": len(pattern_summaries),
        "filters_applied": {
            "category": category,
            "mitre_technique": mitre_technique,
            "severity": severity
        }
    }


def add_attack_pattern(pattern: Dict[str, Any]) -> Dict[str, Any]:
    """
    Add a new attack pattern to the dataset.
    
    Args:
        pattern: Attack pattern dictionary to add
    
    Returns:
        Success or error response
    """
    try:
        # Validate pattern schema
        if not validate_pattern_schema(pattern):
            return create_error_response(
                "validation_error",
                "Invalid attack pattern schema",
                {"pattern_id": pattern.get("id")}
            )
        
        # Load current dataset
        dataset = load_attack_patterns()
        
        # Check for duplicate ID
        existing_ids = [p["id"] for p in dataset.get("attack_patterns", [])]
        if pattern["id"] in existing_ids:
            return create_error_response(
                "validation_error",
                f"Attack pattern with ID '{pattern['id']}' already exists",
                {"pattern_id": pattern["id"]}
            )
        
        # Add pattern to dataset
        dataset["attack_patterns"].append(pattern)
        dataset["last_updated"] = datetime.now().isoformat()
        
        # Write back to file
        DATASET_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(DATASET_PATH, 'w', encoding='utf-8') as f:
            json.dump(dataset, f, indent=2)
        
        # Invalidate cache
        global _attack_patterns_cache, _cache_timestamp
        _attack_patterns_cache = None
        _cache_timestamp = None
        
        logger.info(f"Added new attack pattern: {pattern['id']}")
        
        return {
            "success": True,
            "message": f"Attack pattern '{pattern['id']}' added successfully",
            "pattern_id": pattern["id"]
        }
    
    except Exception as e:
        logger.error(f"Failed to add attack pattern: {e}")
        return create_error_response(
            "internal_error",
            f"Failed to add attack pattern: {str(e)}",
            {"pattern_id": pattern.get("id")}
        )
