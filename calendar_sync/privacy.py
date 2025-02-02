"""Privacy event handling for calendar synchronization."""

import uuid
from datetime import datetime
from typing import Optional

from .caldav_client import CalendarEvent


class PrivacyEvent:
    """Handler for privacy/busy events."""
    
    def __init__(self, prefix: str = "PRIVACY-SYNC-", title: str = "Busy"):
        """Initialize the privacy event handler."""
        self.prefix = prefix
        self.title = title
    
    def create_private_event(
        self,
        start: datetime,
        end: datetime,
        source_uid: Optional[str] = None,
        is_all_day: bool = False
    ) -> CalendarEvent:
        """Create a new private event from a source event."""
        # Generate a deterministic UID based on source event if provided
        if source_uid:
            uid = f"{self.prefix}{source_uid}"
        else:
            uid = f"{self.prefix}{uuid.uuid4()}"
        
        return CalendarEvent(
            uid=uid,
            summary=self.title,
            start=start,
            end=end,
            description=None,  # No description for privacy
            location=None,     # No location for privacy
            recurrence=None,   # Handle recurrence separately
            is_all_day=is_all_day  # Preserve all-day status
        )
    
    def is_privacy_event(self, event: CalendarEvent) -> bool:
        """Check if an event is a privacy event."""
        return event.uid.startswith(self.prefix)
    
    def get_source_uid(self, privacy_event: CalendarEvent) -> Optional[str]:
        """Get the source event UID from a privacy event."""
        if not self.is_privacy_event(privacy_event):
            return None
        return privacy_event.uid[len(self.prefix):] 