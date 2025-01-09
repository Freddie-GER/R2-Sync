"""
CalDAV Instance-Based Calendar Sync

A calendar synchronization implementation that handles both single events and recurring series
by treating all events as individual instances. This approach avoids the complexity of RRULE
handling and works reliably with different CalDAV server implementations.

Features:
- Syncs single events and recurring series
- Handles deletions in both directions
- Detects and removes duplicate events
- Uses UIDs and instance-specific dates for reliable matching
- Works with both Nextcloud and Kerio CalDAV servers

Original implementation by Frederike Reppekus for ProSi calendar sync
"""

import caldav
import datetime
import pytz
from icalendar import Calendar
import logging
import json
from collections import defaultdict

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CalendarSync:
    def __init__(self, source_calendar, target_calendar):
        self.source_calendar = source_calendar
        self.target_calendar = target_calendar
        
    def sync(self):
        # First clean up duplicates
        self._cleanup_duplicates(self.target_calendar)
        
        # Then do the normal sync
        now = datetime.datetime.now(pytz.UTC)
        start = now - datetime.timedelta(days=90)   # Keep 90 days of history
        end = now + datetime.timedelta(days=365)    # Look ahead one full year
        
        source_events = self.source_calendar.date_search(start=start, end=end)
        target_events = self.target_calendar.date_search(start=start, end=end)
        
        # Group events by UID
        source_by_uid = self._group_events_by_uid(source_events)
        target_by_uid = self._group_events_by_uid(target_events)
        
        # Sync each UID group
        for uid, source_instances in source_by_uid.items():
            target_instances = target_by_uid.get(uid, [])
            self._sync_instances(source_instances, target_instances)
            
        # Handle deletions - remove events in target that no longer exist in source
        for uid, target_instances in target_by_uid.items():
            if uid not in source_by_uid:
                for event, comp in target_instances:
                    summary = str(comp.get('summary', ''))
                    logger.info(f"Deleting event no longer in source: {summary}")
                    try:
                        event.delete()
                    except Exception as e:
                        logger.error(f"Error deleting event {summary}: {str(e)}")
    
    def _cleanup_duplicates(self, calendar):
        """Remove duplicate events from calendar"""
        logger.info("Cleaning up duplicates...")
        
        # Get all events
        now = datetime.datetime.now(pytz.UTC)
        start = now - datetime.timedelta(days=30)
        end = now + datetime.timedelta(days=90)
        events = calendar.date_search(start=start, end=end)
        
        # Group events by UID
        by_uid = self._group_events_by_uid(events)
        
        # For each UID group, find and remove duplicates
        for uid, instances in by_uid.items():
            seen = {}  # (summary, full_datetime) -> event
            duplicates = []
            
            for event, comp in instances:
                # Get the full datetime (not just time)
                dt = comp.get('dtstart').dt
                
                key = (
                    str(comp.get('summary', '')).strip(),
                    dt  # This is now the full datetime object
                )
                
                if key in seen:
                    # Keep the older event (lower sequence number)
                    existing_event, existing_comp = seen[key]
                    existing_seq = int(existing_comp.get('sequence', 0) or 0)
                    current_seq = int(comp.get('sequence', 0) or 0)
                    
                    if current_seq > existing_seq:
                        duplicates.append(existing_event)
                        seen[key] = (event, comp)
                    else:
                        duplicates.append(event)
                else:
                    seen[key] = (event, comp)
            
            # Delete duplicates
            for event in duplicates:
                try:
                    summary = str(Calendar.from_ical(event.data).walk('VEVENT').__next__().get('summary', ''))
                    dt = Calendar.from_ical(event.data).walk('VEVENT').__next__().get('dtstart').dt
                    logger.info(f"Removing duplicate: {summary} on {dt}")
                    event.delete()
                except Exception as e:
                    logger.error(f"Error deleting duplicate: {str(e)}")
    
    def _group_events_by_uid(self, events):
        grouped = defaultdict(list)
        for event in events:
            cal = Calendar.from_ical(event.data)
            for component in cal.walk('VEVENT'):
                uid = str(component.get('uid', ''))
                # Skip busy events
                if uid.startswith('BUSY-') or component.get('X-BUSY-SYNC'):
                    continue
                if uid:
                    grouped[uid].append((event, component))
        return grouped
    
    def _event_exists(self, source_comp, target_instances):
        """Check if an event already exists in target calendar"""
        source_rid = source_comp.get('recurrence-id')
        source_start = source_comp.get('dtstart').dt
        source_summary = str(source_comp.get('summary', ''))
        
        for _, target_comp in target_instances:
            # If both events have recurrence-id, compare those
            if source_rid and target_comp.get('recurrence-id'):
                if str(source_rid.dt) == str(target_comp.get('recurrence-id').dt):
                    return True
            # For non-recurring events, compare start time and summary
            else:
                target_start = target_comp.get('dtstart').dt
                target_summary = str(target_comp.get('summary', ''))
                if (source_start == target_start and 
                    source_summary.strip() == target_summary.strip()):
                    return True
        return False
    
    def _sync_instances(self, source_instances, target_instances):
        # Process each source instance
        for source_event, source_comp in source_instances:
            summary = str(source_comp.get('summary', ''))
            
            if self._event_exists(source_comp, target_instances):
                logger.info(f"Instance exists: {summary}")
                continue
                
            logger.info(f"Creating new instance: {summary}")
            try:
                # Get the raw iCal data and ensure it's a string
                ical_data = source_event.data
                if isinstance(ical_data, bytes):
                    ical_data = ical_data.decode('utf-8')
                    
                # Create new event using save_event
                self.target_calendar.save_event(
                    ical=ical_data
                )
            except Exception as e:
                logger.error(f"Error creating event {summary}: {str(e)}") 