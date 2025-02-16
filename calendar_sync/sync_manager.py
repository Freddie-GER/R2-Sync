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
        # Get events from source calendar
        source_events = self._get_source_events(source_calendar)
        
        # For Google and Kerio calendars in privacy mode, perform a full deletion of busy events in the sync period
        if privacy_mode and (target_calendar.endswith("@google") or target_calendar.endswith("@kerio")):
            from datetime import datetime, timedelta
            now = datetime.utcnow()
            sync_end = now + timedelta(days=30)
            if target_calendar.endswith("@google"):
                if not hasattr(self, 'google'):
                    from .google_calendar_client import GoogleCalendarClient
                    self.google = GoogleCalendarClient()
                real_calendar_id = target_calendar[:-7].strip()
                existing_events = self.google.list_events(real_calendar_id, start=now, end=sync_end)
                for event in existing_events:
                    if event.summary == self.privacy_handler.title:
                        try:
                            self.google.delete_event(real_calendar_id, event.uid)
                            logger.info(f"Deleted busy event {event.uid} from Google during sync cleanup.")
                        except Exception as e:
                            if hasattr(e, 'resp') and e.resp.status == 404:
                                logger.info(f"Busy event {event.uid} already deleted (404).")
                            else:
                                logger.error(f"Failed to delete busy event {event.uid}: {e}")
                target_events = []
            elif target_calendar.endswith("@kerio"):
                real_calendar_id = target_calendar.replace("@kerio", "").strip()
                existing_events = self.kerio.list_events(real_calendar_id, start=now, end=sync_end)
                for event in existing_events:
                    if event.summary == self.privacy_handler.title:
                        try:
                            self.kerio.delete_event(real_calendar_id, event.uid)
                            logger.info(f"Deleted busy event {event.uid} from Kerio during sync cleanup.")
                        except Exception as e:
                            if "not subscriptable" in str(e):
                                logger.info(f"Busy event {event.uid} already deleted or not deletable (non subscriptable error).")
                            else:
                                logger.error(f"Failed to delete busy event {event.uid} on Kerio: {e}")
                target_events = []
        else:
            target_events = self._get_target_events(target_calendar)
        
        # Create sets of event UIDs for comparison (for non-Google or non-privacy or after deletion)
        source_uids = {event.uid for event in source_events}
        target_uids = {event.uid for event in target_events}
        privacy_uids = {
            self.privacy_handler.get_source_uid(event)
            for event in target_events
            if self.privacy_handler.is_privacy_event(event)
        }
        
        # Process each source event: in privacy mode, always create a new busy event since we've wiped old ones
        for source_event in source_events:
            try:
                # Skip events with missing start or end time
                if source_event.start is None or source_event.end is None:
                    logger.error(f"Skipping event {source_event.uid} due to missing start or end time")
                    continue

                if privacy_mode:
                    # Create new privacy (busy) event for each source event
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
        
        # For non-Google or non-privacy mode, remove obsolete events from target
        if not (privacy_mode and target_calendar.endswith("@google")):
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
        events1_dict = {uid: event for uid, event in events1_dict.items() if not self.privacy_handler.is_privacy_event(event) and event.summary != self.privacy_handler.title}
        events2_dict = {uid: event for uid, event in events2_dict.items() if not self.privacy_handler.is_privacy_event(event) and event.summary != self.privacy_handler.title}
        
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
        if "@nextcloud" in calendar_id:
            return self.nextcloud.list_events(
                calendar_id.replace("@nextcloud", ""), start, end
            )
        elif "@kerio" in calendar_id:
            return self.kerio.list_events(
                calendar_id.replace("@kerio", ""), start, end
            )
        elif "@google" in calendar_id:
            if not hasattr(self, 'google'):
                from .google_calendar_client import GoogleCalendarClient
                self.google = GoogleCalendarClient()
            return self.google.list_events(
                calendar_id.replace("@google", "").strip(), start, end
            )
        else:
            raise ValueError(f"Unsupported calendar identifier: {calendar_id}")
    
    def _create_target_event(
        self,
        calendar_id: str,
        event: CalendarEvent
    ) -> None:
        """Create an event in the target calendar for Nextcloud, Google, or Kerio."""
        if "@nextcloud" in calendar_id:
            target = self.nextcloud
            real_id = calendar_id.replace("@nextcloud", "")
        elif "@kerio" in calendar_id:
            target = self.kerio
            real_id = calendar_id.replace("@kerio", "")
        elif calendar_id.endswith("@google"):
            if not hasattr(self, 'google'):
                from .google_calendar_client import GoogleCalendarClient
                self.google = GoogleCalendarClient()
            target = self.google
            real_id = calendar_id[:-7].strip()
        else:
            raise ValueError(f"Unsupported calendar identifier: {calendar_id}")
        target.create_event(real_id, event)
    
    def _update_target_event(
        self,
        calendar_id: str,
        event: CalendarEvent
    ) -> None:
        """Update an event in the target calendar for Nextcloud, Google, or Kerio."""
        if "@nextcloud" in calendar_id:
            target = self.nextcloud
            real_id = calendar_id.replace("@nextcloud", "")
        elif "@kerio" in calendar_id:
            target = self.kerio
            real_id = calendar_id.replace("@kerio", "")
        elif calendar_id.endswith("@google"):
            if not hasattr(self, 'google'):
                from .google_calendar_client import GoogleCalendarClient
                self.google = GoogleCalendarClient()
            target = self.google
            real_id = calendar_id[:-7].strip()
        else:
            raise ValueError(f"Unsupported calendar identifier: {calendar_id}")
        target.update_event(real_id, event)
    
    def _delete_target_event(
        self,
        calendar_id: str,
        event_uid: str
    ) -> None:
        """Delete an event from the target calendar for Nextcloud, Google, or Kerio."""
        if "@nextcloud" in calendar_id:
            self.nextcloud.delete_event(
                calendar_id.replace("@nextcloud", ""),
                event_uid
            )
        elif "@kerio" in calendar_id:
            self.kerio.delete_event(
                calendar_id.replace("@kerio", ""),
                event_uid
            )
        elif calendar_id.endswith("@google"):
            if not hasattr(self, 'google'):
                from .google_calendar_client import GoogleCalendarClient
                self.google = GoogleCalendarClient()
            target = self.google
            real_id = calendar_id[:-7].strip()
            target.delete_event(real_id, event_uid) 