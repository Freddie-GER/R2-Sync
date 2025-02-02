"""Calendar synchronization manager."""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple

from .caldav_client import CalDAVClient, CalendarEvent
from .config import Config, SyncMode
from .privacy import PrivacyEvent

logger = logging.getLogger(__name__)


class SyncManager:
    """Manager for calendar synchronization operations."""
    
    def __init__(self, config: Config):
        """Initialize the sync manager."""
        self.config = config
        self.nextcloud = CalDAVClient(config.nextcloud)
        self.kerio = CalDAVClient(config.kerio)
        self.privacy_handler = PrivacyEvent(
            prefix=config.privacy_event_prefix,
            title=config.privacy_event_title
        )
    
    def sync_calendars(self) -> None:
        """Synchronize all configured calendar pairs."""
        for pair in self.config.calendar_pairs:
            try:
                logger.info(f"Syncing calendars: {pair.source_calendar} -> {pair.target_calendar}")
                
                if pair.sync_mode == SyncMode.TWO_WAY:
                    self._sync_two_way(pair.source_calendar, pair.target_calendar)
                else:  # ONE_WAY
                    self._sync_one_way(
                        pair.source_calendar,
                        pair.target_calendar,
                        privacy_mode=pair.privacy
                    )
                
                logger.info("Sync completed successfully")
            except Exception as e:
                logger.error(f"Failed to sync calendars: {str(e)}")
    
    def _sync_one_way(
        self,
        source_calendar: str,
        target_calendar: str,
        privacy_mode: bool = False
    ) -> None:
        """Perform one-way synchronization between calendars."""
        # Get events from both calendars
        source_events = self._get_source_events(source_calendar)
        target_events = self._get_target_events(target_calendar)
        
        # Create sets of event UIDs for comparison
        source_uids = {event.uid for event in source_events}
        target_uids = {event.uid for event in target_events}
        privacy_uids = {
            self.privacy_handler.get_source_uid(event)
            for event in target_events
            if self.privacy_handler.is_privacy_event(event)
        }
        
        # Process each source event
        for source_event in source_events:
            try:
                if privacy_mode:
                    privacy_uid = f"{self.config.privacy_event_prefix}{source_event.uid}"
                    if privacy_uid not in target_uids:
                        # Create new privacy event
                        privacy_event = self.privacy_handler.create_private_event(
                            start=source_event.start,
                            end=source_event.end,
                            source_uid=source_event.uid,
                            is_all_day=source_event.is_all_day
                        )
                        self._create_target_event(target_calendar, privacy_event)
                else:
                    if source_event.uid not in target_uids:
                        # Create new event with full details
                        self._create_target_event(target_calendar, source_event)
            except Exception as e:
                logger.error(f"Failed to sync event {source_event.uid}: {str(e)}")
        
        # Remove obsolete events from target
        for target_event in target_events:
            try:
                if privacy_mode and self.privacy_handler.is_privacy_event(target_event):
                    source_uid = self.privacy_handler.get_source_uid(target_event)
                    if source_uid not in source_uids:
                        self._delete_target_event(target_calendar, target_event.uid)
                elif not privacy_mode and target_event.uid not in source_uids:
                    self._delete_target_event(target_calendar, target_event.uid)
            except Exception as e:
                logger.error(f"Failed to clean up event {target_event.uid}: {str(e)}")
    
    def _sync_two_way(
        self,
        calendar1: str,
        calendar2: str
    ) -> None:
        """Perform two-way synchronization between calendars."""
        # Get events from both calendars
        events1 = self._get_source_events(calendar1)
        events2 = self._get_source_events(calendar2)
        
        # Create dictionaries for easy lookup
        events1_dict = {event.uid: event for event in events1}
        events2_dict = {event.uid: event for event in events2}
        
        # Skip privacy events in two-way sync
        events1_dict = {
            uid: event
            for uid, event in events1_dict.items()
            if not self.privacy_handler.is_privacy_event(event)
        }
        events2_dict = {
            uid: event
            for uid, event in events2_dict.items()
            if not self.privacy_handler.is_privacy_event(event)
        }
        
        # Sync calendar1 -> calendar2
        for uid, event in events1_dict.items():
            try:
                if uid not in events2_dict:
                    self._create_target_event(calendar2, event)
                else:
                    # Compare events and update if needed
                    event2 = events2_dict[uid]
                    if (event.summary != event2.summary or
                        event.start != event2.start or
                        event.end != event2.end or
                        event.description != event2.description or
                        event.location != event2.location or
                        event.is_all_day != event2.is_all_day):
                        self._update_target_event(calendar2, event)
            except Exception as e:
                logger.error(f"Failed to sync event {uid} to calendar2: {str(e)}")
        
        # Sync calendar2 -> calendar1
        for uid, event in events2_dict.items():
            try:
                if uid not in events1_dict:
                    self._create_target_event(calendar1, event)
                else:
                    # Compare events and update if needed
                    event1 = events1_dict[uid]
                    if (event.summary != event1.summary or
                        event.start != event1.start or
                        event.end != event1.end or
                        event.description != event1.description or
                        event.location != event1.location or
                        event.is_all_day != event1.is_all_day):
                        self._update_target_event(calendar1, event)
            except Exception as e:
                logger.error(f"Failed to sync event {uid} to calendar1: {str(e)}")
    
    def _get_source_events(
        self,
        calendar_id: str,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None
    ) -> List[CalendarEvent]:
        """Get events from the source calendar."""
        if "@nextcloud" in calendar_id:
            return self.nextcloud.list_events(
                calendar_id.replace("@nextcloud", ""),
                start=start,
                end=end
            )
        else:
            return self.kerio.list_events(
                calendar_id.replace("@kerio", ""),
                start=start,
                end=end
            )
    
    def _get_target_events(
        self,
        calendar_id: str,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None
    ) -> List[CalendarEvent]:
        """Get events from the target calendar."""
        return self._get_source_events(calendar_id, start, end)
    
    def _create_target_event(
        self,
        calendar_id: str,
        event: CalendarEvent
    ) -> None:
        """Create an event in the target calendar."""
        if "@nextcloud" in calendar_id:
            self.nextcloud.create_event(
                calendar_id.replace("@nextcloud", ""),
                event
            )
        else:
            self.kerio.create_event(
                calendar_id.replace("@kerio", ""),
                event
            )
    
    def _update_target_event(
        self,
        calendar_id: str,
        event: CalendarEvent
    ) -> None:
        """Update an event in the target calendar."""
        if "@nextcloud" in calendar_id:
            self.nextcloud.update_event(
                calendar_id.replace("@nextcloud", ""),
                event
            )
        else:
            self.kerio.update_event(
                calendar_id.replace("@kerio", ""),
                event
            )
    
    def _delete_target_event(
        self,
        calendar_id: str,
        event_uid: str
    ) -> None:
        """Delete an event from the target calendar."""
        if "@nextcloud" in calendar_id:
            self.nextcloud.delete_event(
                calendar_id.replace("@nextcloud", ""),
                event_uid
            )
        else:
            self.kerio.delete_event(
                calendar_id.replace("@kerio", ""),
                event_uid
            ) 