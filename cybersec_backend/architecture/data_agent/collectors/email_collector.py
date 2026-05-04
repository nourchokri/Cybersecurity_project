"""
Email Collector — Captures email metadata from Outlook.
Tracks sent/received emails, external recipients, attachments.
Critical for detecting data exfiltration via email (CERT r4.2).
"""

import os
import getpass
import socket
from datetime import datetime, timedelta
from typing import Optional
from collectors.event_schema import StandardEvent, create_event

# Try to import win32com for Outlook access
try:
    import win32com.client
    import pythoncom
    OUTLOOK_AVAILABLE = True
except ImportError:
    OUTLOOK_AVAILABLE = False
    print("[email_collector] win32com not available. Install: pip install pywin32")


def is_external_email(email_address: str, internal_domains: Optional[list[str]] = None) -> bool:
    """Check if email address is external to the organization."""
    if not email_address or "@" not in email_address:
        return False
    
    # Default internal domains (customize for your org)
    if internal_domains is None:
        internal_domains = [
            "company.com", "internal.local", "corp.local",
        ]
    
    domain = email_address.split("@")[1].lower()
    # If domain is in common personal email providers, it's external
    personal_providers = {
        "gmail.com", "yahoo.com", "hotmail.com", "outlook.com",
        "live.com", "aol.com", "icloud.com", "protonmail.com"
    }
    
    if domain in personal_providers:
        return True
    
    # Check against internal domains
    return not any(domain.endswith(internal) for internal in internal_domains)



def collect_outlook_emails(hours_back: int = 48, max_emails: int = 500) -> list[StandardEvent]:
    """
    Collect email metadata from Outlook.
    Requires Outlook to be installed and configured.
    """
    if not OUTLOOK_AVAILABLE:
        print("[email_collector] Outlook access not available (pywin32 not installed)")
        return []

    pythoncom.CoInitialize()
    try:
        events = []
        user_id = getpass.getuser()
        device_id = socket.gethostname()
        cutoff_time = datetime.now() - timedelta(hours=hours_back)

        try:
            print(f"[email_collector] Connecting to Outlook...")
            outlook = win32com.client.Dispatch("Outlook.Application")
            namespace = outlook.GetNamespace("MAPI")
            
            # Process Sent Items
            print(f"[email_collector] Accessing Sent Items folder...")
            sent_folder = namespace.GetDefaultFolder(5)  # 5 = olFolderSentMail
            sent_items = sent_folder.Items
            total_sent = sent_items.Count
            print(f"[email_collector] Found {total_sent} total items in Sent folder")
            print(f"[email_collector] Looking for emails sent after {cutoff_time}")
            
            sent_items.Sort("[SentOn]", True)  # Sort by SentOn descending

            count = 0
            skipped = 0
            for item in sent_items:
                if count >= max_emails:
                    break
                try:
                    # Check if this is actually an email (not meeting request, etc.)
                    if not hasattr(item, 'SentOn'):
                        skipped += 1
                        continue
                    
                    sent_time = item.SentOn
                    
                    # Convert pywintypes datetime to Python datetime if needed
                    if hasattr(sent_time, 'timestamp'):
                        sent_time = datetime.fromtimestamp(sent_time.timestamp())
                    
                    # Debug: print first item's date
                    if count == 0 and skipped == 0:
                        print(f"[email_collector] Most recent sent email: {sent_time}")
                    
                    if sent_time < cutoff_time:
                        print(f"[email_collector] Reached cutoff time. Stopping sent items scan.")
                        break
                    
                    if not hasattr(item, 'To') or not item.To:
                        skipped += 1
                        continue
                    
                    # Extract recipients
                    recipients = [r.strip() for r in item.To.split(";") if r.strip()]
                    if hasattr(item, 'CC') and item.CC:
                        recipients.extend([r.strip() for r in item.CC.split(";") if r.strip()])
                    
                    # Count external recipients
                    external_count = sum(1 for r in recipients if is_external_email(r))
                    
                    # Count attachments
                    attachment_count = item.Attachments.Count if hasattr(item, 'Attachments') else 0
                    total_attachment_size = 0
                    if attachment_count > 0:
                        for att in item.Attachments:
                            total_attachment_size += att.Size if hasattr(att, 'Size') else 0
                    
                    # Get subject (truncated for privacy)
                    subject = item.Subject[:100] if hasattr(item, 'Subject') and item.Subject else ""
                    
                    # Get first few recipients for display (truncate for privacy)
                    recipients_display = "; ".join(recipients[:3])
                    if len(recipients) > 3:
                        recipients_display += f" (+{len(recipients)-3} more)"
                    
                    # Convert timestamp to ISO format
                    timestamp_str = sent_time.isoformat() if isinstance(sent_time, datetime) else str(sent_time)
                    
                    events.append(create_event(
                        event_type="email_sent",
                        event_category="email",
                        action="send",
                        resource=f"email_to_{len(recipients)}_recipients",
                        user_id=user_id,
                        device_id=device_id,
                        source="outlook",
                        timestamp=timestamp_str,
                        recipient_count=len(recipients),
                        external_recipient_count=external_count,
                        attachment_count=attachment_count,
                        attachment_size_bytes=total_attachment_size,
                        email_subject=subject,
                        email_recipients=recipients_display,
                        is_external=external_count > 0,
                    ))
                    count += 1
                    
                except Exception as e:
                    if count < 3:  # Log first few errors
                        print(f"[email_collector] Error processing sent item: {e}")
                    skipped += 1
                    continue
            
            print(f"[email_collector] Processed {count} sent emails (skipped {skipped})")
            
            # Process Inbox (received emails)
            print(f"[email_collector] Accessing Inbox folder...")
            inbox = namespace.GetDefaultFolder(6)  # 6 = olFolderInbox
            inbox_items = inbox.Items
            total_inbox = inbox_items.Count
            print(f"[email_collector] Found {total_inbox} total items in Inbox")
            
            inbox_items.Sort("[ReceivedTime]", True)
            
            count = 0
            for item in inbox_items:
                if count >= max_emails:
                    break
                
                try:
                    if not hasattr(item, 'ReceivedTime'):
                        continue
                    
                    received_time = item.ReceivedTime
                    
                    # Convert pywintypes datetime to Python datetime if needed
                    if hasattr(received_time, 'timestamp'):
                        received_time = datetime.fromtimestamp(received_time.timestamp())
                    
                    if received_time < cutoff_time:
                        break
                    
                    sender = item.SenderEmailAddress if hasattr(item, 'SenderEmailAddress') else ""
                    is_external = is_external_email(sender)
                    
                    attachment_count = item.Attachments.Count if hasattr(item, 'Attachments') else 0
                    total_attachment_size = 0
                    if attachment_count > 0:
                        for att in item.Attachments:
                            total_attachment_size += att.Size if hasattr(att, 'Size') else 0
                    
                    subject = item.Subject[:100] if hasattr(item, 'Subject') and item.Subject else ""
                    
                    # Convert timestamp to ISO format
                    timestamp_str = received_time.isoformat() if isinstance(received_time, datetime) else str(received_time)
                    
                    events.append(create_event(
                        event_type="email_received",
                        event_category="email",
                        action="receive",
                        resource=f"email_from_{sender}",
                        user_id=user_id,
                        device_id=device_id,
                        source="outlook",
                        timestamp=timestamp_str,
                        sender_email=sender,
                        attachment_count=attachment_count,
                        attachment_size_bytes=total_attachment_size,
                        email_subject=subject,
                        is_external=is_external,
                    ))
                    count += 1
                    
                except Exception as e:
                    if count < 3:  # Log first few errors
                        print(f"[email_collector] Error processing inbox item: {e}")
                    continue
            
            print(f"[email_collector] Processed {count} received emails")
            
        except Exception as e:
            import traceback
            print(f"[email_collector] Error accessing Outlook: {e}")
            print(f"[email_collector] Error type: {type(e).__name__}")
            traceback.print_exc()
            print("\n[email_collector] Troubleshooting:")
            print("  1. Make sure Outlook is installed and configured")
            print("  2. Try opening Outlook manually first")
            print("  3. Check if Outlook is running (Task Manager)")

        return events

    finally:
        pythoncom.CoUninitialize()


if __name__ == "__main__":
    import json
    print("Collecting email metadata from Outlook...")
    events = collect_outlook_emails(hours_back=168)  # 7 days
    print(f"\nCollected {len(events)} email events")
    for e in events[:3]:
        print(json.dumps(e.model_dump(), indent=2))
