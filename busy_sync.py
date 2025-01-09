"""
Privacy-Preserving Calendar Sync Implementation

This module implements a one-way sync from source calendars to a target calendar,
converting all events to private "busy" events that only show time slots as occupied
without revealing any details about the actual events.
"""

import caldav
import datetime
import pytz
from icalendar import Calendar, Event
import logging
import uuid
import recurring_ical_events

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BusySync:
    def __init__(self, source_calendars, target_calendar):
        """
        Initialize BusySync with multiple source calendars and one target calendar.
        
        Args:
            source_calendars (list): List of source CalDAV calendars to sync from
            target_calendar: Target CalDAV calendar to sync to
        """
        self.source_calendars = source_calendars
        self.target_calendar = target_calendar
        
    def sync(self):
        """
        Perform one-way busy sync from source calendars to target calendar.
        Converts all events to private busy-time events.
        """
        # Set sync window to one year
        now = datetime.datetime.now(pytz.UTC)
        start = now - datetime.timedelta(days=30)  # Keep some history
        end = now + datetime.timedelta(days=365)   # Look ahead one full year
        
        # Get all existing busy events in target
        target_events = self.target_calendar.date_search(start=start, end=end)
        target_busy_events = self._get_busy_events(target_events)
        
        # Process each source calendar
        for source_calendar in self.source_calendars:
            logger.info(f"Processing calendar: {source_calendar.name}")
            source_events = source_calendar.date_search(start=start, end=end)
            
            # Process each event
            for event in source_events:
                self._process_event(event, target_busy_events, start, end)
                
        # Clean up old busy events
        self._cleanup_old_events(target_busy_events)
    
    def _get_busy_events(self, events):
        """Extract busy events from a list of events."""
        busy_events = {}
        for event in events:
            cal = Calendar.from_ical(event.data)
            for component in cal.walk('VEVENT'):
                uid = str(component.get('uid', ''))
                if uid.startswith('BUSY-'):
                    start = component.get('dtstart').dt
                    end = component.get('dtend').dt
                    busy_events[uid] = {
                        'event': event,
                        'start': start,
                        'end': end
                    }
        return busy_events
    
    def _process_event(self, source_event, target_busy_events, start_date, end_date):
        """Process a source event and create/update corresponding busy events."""
        cal = Calendar.from_ical(source_event.data)
        
        # Use recurring_ical_events to expand recurring events
        events = recurring_ical_events.of(cal).between(start_date, end_date)
        
        for component in events:
            # Skip cancelled events
            status = component.get('status', '')
            if status and str(status).upper() == 'CANCELLED':
                continue
                
            # Generate a stable UID for the busy event based on source event and date
            source_uid = str(component.get('uid', ''))
            event_start = component.get('dtstart').dt
            
            # For recurring events, include the date in the UID to make it unique
            if isinstance(event_start, datetime.datetime):
                date_str = event_start.strftime('%Y%m%d-%H%M')
            else:
                date_str = event_start.strftime('%Y%m%d')
                
            busy_uid = f"BUSY-{source_uid}-{date_str}"
            
            # Get event times
            start = component.get('dtstart').dt
            if component.get('dtend'):
                end = component.get('dtend').dt
            else:
                # If no end time, assume 1 hour duration
                if isinstance(start, datetime.datetime):
                    end = start + datetime.timedelta(hours=1)
                else:
                    end = start + datetime.timedelta(days=1)
            
            # Check if busy event already exists
            if busy_uid in target_busy_events:
                existing = target_busy_events[busy_uid]
                if (existing['start'] == start and 
                    existing['end'] == end):
                    # Event unchanged, remove from cleanup list
                    target_busy_events.pop(busy_uid)
                    continue
                else:
                    # Event changed, delete old version
                    try:
                        existing['event'].delete()
                    except Exception as e:
                        logger.error(f"Error deleting old busy event: {str(e)}")
            
            # Create new busy event
            try:
                busy_event = Event()
                busy_event.add('uid', busy_uid)
                busy_event.add('dtstart', start)
                busy_event.add('dtend', end)
                busy_event.add('summary', 'Busy')
                busy_event.add('transp', 'OPAQUE')  # Show as busy
                busy_event.add('class', 'PRIVATE')  # Mark as private
                busy_event.add('X-BUSY-SYNC', 'true')
                
                # Create new calendar for the event
                busy_cal = Calendar()
                busy_cal.add_component(busy_event)
                
                # Save to target calendar
                self.target_calendar.save_event(
                    ical=busy_cal.to_ical().decode('utf-8')
                )
                logger.info(f"Created busy event: {start} - {end}")
                
            except Exception as e:
                logger.error(f"Error creating busy event: {str(e)}")
    
    def _cleanup_old_events(self, target_busy_events):
        """Remove busy events that no longer have corresponding source events."""
        for busy_uid, event_data in target_busy_events.items():
            try:
                event_data['event'].delete()
                logger.info(f"Deleted obsolete busy event: {busy_uid}")
            except Exception as e:
                logger.error(f"Error deleting busy event {busy_uid}: {str(e)}") 