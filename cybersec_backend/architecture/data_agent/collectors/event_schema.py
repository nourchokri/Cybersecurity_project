"""
Event Schema — Standard schema for ALL events flowing through the pipeline.

Every collector MUST output events conforming to this schema.
This is the contract between Team 1 (Data Processing) and Team 2 (Behavior Analysis).
"""

from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime
import uuid


class EventMetadata(BaseModel):
    """Flexible metadata that varies by event type."""
    # System / logon events
    idle_time_seconds: Optional[float] = None
    session_duration_minutes: Optional[float] = None

    # File events
    file_path: Optional[str] = None
    file_extension: Optional[str] = None
    file_size_bytes: Optional[int] = None
    is_usb: Optional[bool] = None
    sensitivity_level: Optional[int] = None  # 0=low, 1=medium, 2=high

    # Network events
    src_ip: Optional[str] = None
    dst_ip: Optional[str] = None
    src_port: Optional[int] = None
    dst_port: Optional[int] = None
    protocol: Optional[str] = None
    bytes_sent: Optional[int] = None
    bytes_received: Optional[int] = None
    process_name: Optional[str] = None

    # Process events
    pid: Optional[int] = None
    cpu_percent: Optional[float] = None
    memory_mb: Optional[float] = None
    parent_pid: Optional[int] = None
    command_line: Optional[str] = None

    # Browser / web events
    url: Optional[str] = None
    domain: Optional[str] = None
    page_title: Optional[str] = None
    visit_count: Optional[int] = None

    # Attack simulation fields (added by Adversarial Agent)
    is_simulated: Optional[bool] = False
    attack_type: Optional[str] = None       # e.g., "lateral_movement"
    mitre_technique: Optional[str] = None   # e.g., "T1078"
    attack_id: Optional[str] = None         # e.g., "cert_r42_s1_aam0658"
    attack_name: Optional[str] = None       # e.g., "USB Exfiltration + Wikileaks"
    attack_step: Optional[int] = None       # Step number in attack sequence
    severity: Optional[str] = None          # e.g., "high", "medium", "low"
    
    # Email events (email_collector)
    recipient_count: Optional[int] = None
    external_recipient_count: Optional[int] = None
    attachment_count: Optional[int] = None
    attachment_size_bytes: Optional[int] = None
    email_subject: Optional[str] = None
    email_recipients: Optional[str] = None
    sender_email: Optional[str] = None
    is_external: Optional[bool] = None
    
    # Windows Event Log (windows_event_collector)
    event_id: Optional[int] = None
    event_description: Optional[str] = None
    log_source: Optional[str] = None  # e.g., "Security", "System", "Application"
    
    # USB Device (usb_device_collector)
    device_type: Optional[str] = None
    device_vendor: Optional[str] = None
    device_product: Optional[str] = None
    device_serial: Optional[str] = None
    device_vid: Optional[str] = None
    device_pid: Optional[str] = None
    device_description: Optional[str] = None
    device_status: Optional[str] = None
    
    # Clipboard (clipboard_collector)
    clipboard_length: Optional[int] = None
    clipboard_sensitivity: Optional[int] = None
    clipboard_patterns: Optional[str] = None
    clipboard_preview: Optional[str] = None
    
    # Registry (registry_collector)
    registry_key: Optional[str] = None
    registry_value_name: Optional[str] = None
    registry_value_data: Optional[str] = None
    is_suspicious: Optional[bool] = None
    suspicious_indicators: Optional[str] = None
    
    # DNS (dns_collector)
    dns_record_type: Optional[str] = None
    dns_response: Optional[str] = None


class StandardEvent(BaseModel):
    """
    The unified event schema. Every event in the pipeline follows this format.
    Maps to Contract 1 (Team 1 -> Team 2) from the project spec.
    """
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = Field(description="ISO 8601 timestamp")
    user_id: str = Field(description="User identifier")
    device_id: str = Field(description="Device/hostname identifier")
    event_type: Literal[
        "logon", "logoff",
        "file_access",
        "device_connect", "device_disconnect",
        "process_start", "process_stop",
        "network_connection",
        "http_request",
        "email_sent", "email_received",
    ] = Field(description="Type of event")
    event_category: Literal[
        "system", "file", "device", "process", "network", "web", "email"
    ] = Field(description="High-level category")
    action: str = Field(description="Specific action (e.g., 'open', 'connect')")
    resource: str = Field(description="Target resource (path, URL, IP:port)")
    metadata: EventMetadata = Field(default_factory=EventMetadata)
    source: str = Field(description="Collection source (e.g., 'psutil', 'watchdog')")


def create_event(event_type, event_category, action, resource,
                 user_id, device_id, source, timestamp=None,
                 **metadata_kwargs) -> StandardEvent:
    """Helper to create a standard event with sensible defaults."""
    return StandardEvent(
        timestamp=timestamp or datetime.now().isoformat(),
        user_id=user_id,
        device_id=device_id,
        event_type=event_type,
        event_category=event_category,
        action=action,
        resource=resource,
        metadata=EventMetadata(**metadata_kwargs),
        source=source,
    )
