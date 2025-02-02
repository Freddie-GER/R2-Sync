"""CalDAV client implementation for calendar operations."""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import caldav
from caldav.elements import dav, cdav
from icalendar import Calendar, Event

from .config import ServerConfig

logger = logging.getLogger(__name__)


@dataclass
class CalendarEvent:
    """Representation of a calendar event."""
    uid: str
    summary: str
    start: datetime
    end: datetime
    description: Optional[str] = None
    location: Optional[str] = None
    recurrence: Optional[str] = None
    is_all_day: bool = False
    ical_data: str = ""
    
    def __getitem__(self, key: str) -> any:
        """Support dictionary-style access for backward compatibility."""
        if hasattr(self, key):
            return getattr(self, key)
        raise KeyError(f"'{self.__class__.__name__}' object has no attribute '{key}'")
    
    def __setitem__(self, key: str, value: any) -> None:
        """Support dictionary-style access for backward compatibility."""
        if hasattr(self, key):
            setattr(self, key, value)
        else:
            raise KeyError(f"'{self.__class__.__name__}' object has no attribute '{key}'")
            
    @classmethod
    def from_ical(cls, ical_data: str) -> "CalendarEvent":
        """Create a CalendarEvent from iCalendar data."""
        cal = Calendar.from_ical(ical_data)
        event = None
        
        for component in cal.walk():
            if component.name == "VEVENT":
                event = component
                break
        
        if not event:
            raise ValueError("No VEVENT component found in iCalendar data")
        
        # Handle both datetime and date objects
        start = event.get('dtstart').dt
        end = event.get('dtend').dt
        
        # Check if this is an all-day event (date objects instead of datetime)
        is_all_day = not isinstance(start, datetime)
        
        # For all-day events, keep the date but set time to midnight
        if is_all_day:
            start = datetime.combine(start, datetime.min.time())
            end = datetime.combine(end, datetime.min.time())
        
        return cls(
            uid=event.get('uid'),
            summary=event.get('summary'),
            start=start,
            end=end,
            description=event.get('description'),
            location=event.get('location'),
            recurrence=event.get('rrule'),
            is_all_day=is_all_day,
            ical_data=ical_data
        )


class CalDAVClient:
    """Client for interacting with CalDAV servers."""
    
    def __init__(self, config: ServerConfig):
        """Initialize the CalDAV client."""
        self.config = config
        self.client = caldav.DAVClient(
            url=config.url,
            username=config.username,
            password=config.password
        )
        self._principal = None
        self._calendars: Dict[str, caldav.Calendar] = {}
    
    @property
    def principal(self) -> caldav.Principal:
        """Get the CalDAV principal."""
        if not self._principal:
            self._principal = self.client.principal()
        return self._principal
    
    def get_calendar(self, calendar_id: str) -> caldav.Calendar:
        """Get a calendar by its ID."""
        if calendar_id not in self._calendars:
            calendars = self.principal.calendars()
            for calendar in calendars:
                if calendar.id == calendar_id:
                    self._calendars[calendar_id] = calendar
                    break
            if calendar_id not in self._calendars:
                raise ValueError(f"Calendar not found: {calendar_id}")
        return self._calendars[calendar_id]
    
    def list_events(
        self,
        calendar_id: str,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None
    ) -> List[CalendarEvent]:
        """List events in a calendar."""
        calendar = self.get_calendar(calendar_id)
        
        # Default to fetching events from the last week to next month
        if not start:
            start = datetime.now() - timedelta(days=7)
        if not end:
            end = datetime.now() + timedelta(days=30)
        
        events = []
        for event in calendar.date_search(start=start, end=end):
            try:
                events.append(CalendarEvent.from_ical(event.data))
            except Exception as e:
                logger.warning(f"Failed to parse event: {e}")
        
        return events
    
    def create_event(
        self,
        calendar_id: str,
        event: CalendarEvent
    ) -> str:
        """Create a new event in the calendar."""
        calendar = self.get_calendar(calendar_id)
        
        cal = Calendar()
        cal.add('prodid', '-//Calendar Sync Tool//EN')
        cal.add('version', '2.0')
        
        vevent = Event()
        vevent.add('summary', event.summary)
        
        # Handle all-day events properly
        if event.is_all_day:
            # For all-day events, we need to use date objects
            vevent.add('dtstart', event.start.date())
            vevent.add('dtend', event.end.date())
        else:
            # For regular events, use datetime objects
            vevent.add('dtstart', event.start)
            vevent.add('dtend', event.end)
            
        vevent.add('uid', event.uid)
        
        if event.description:
            vevent.add('description', event.description)
        if event.location:
            vevent.add('location', event.location)
        if event.recurrence:
            vevent.add('rrule', event.recurrence)
        
        cal.add_component(vevent)
        
        calendar.save_event(cal.to_ical().decode('utf-8'))
        return event.uid
    
    def update_event(
        self,
        calendar_id: str,
        event: CalendarEvent
    ) -> None:
        """Update an existing event in the calendar."""
        calendar = self.get_calendar(calendar_id)
        events = calendar.event_by_uid(event.uid)
        
        if not events:
            raise ValueError(f"Event not found: {event.uid}")
        
        cal = Calendar()
        cal.add('prodid', '-//Calendar Sync Tool//EN')
        cal.add('version', '2.0')
        
        vevent = Event()
        vevent.add('summary', event.summary)
        
        # Handle all-day events properly
        if event.is_all_day:
            # For all-day events, we need to use date objects
            vevent.add('dtstart', event.start.date())
            vevent.add('dtend', event.end.date())
        else:
            # For regular events, use datetime objects
            vevent.add('dtstart', event.start)
            vevent.add('dtend', event.end)
            
        vevent.add('uid', event.uid)
        
        if event.description:
            vevent.add('description', event.description)
        if event.location:
            vevent.add('location', event.location)
        if event.recurrence:
            vevent.add('rrule', event.recurrence)
        
        cal.add_component(vevent)
        
        events[0].data = cal.to_ical().decode('utf-8')
    
    def delete_event(
        self,
        calendar_id: str,
        event_uid: str
    ) -> None:
        """Delete an event from the calendar."""
        calendar = self.get_calendar(calendar_id)
        events = calendar.event_by_uid(event_uid)
        
        if not events:
            raise ValueError(f"Event not found: {event_uid}")
        
        events[0].delete() 