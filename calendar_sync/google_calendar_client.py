import os
import pickle
import re
import datetime
import logging
from typing import Optional

from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

# Import CalendarEvent from our existing caldav_client module
from .caldav_client import CalendarEvent

SCOPES = ['https://www.googleapis.com/auth/calendar']

class GoogleCalendarClient:
    def __init__(self, credentials_file='client_secret_571324167090-i9l373a0pn3amp4r055c7rfd5ool4bss.apps.googleusercontent.com.json', token_file='google_token.pickle'):
        self.credentials_file = credentials_file
        self.token_file = token_file
        self.service = self.get_service()

    def get_service(self):
        creds = None
        if os.path.exists(self.token_file):
            with open(self.token_file, 'rb') as token:
                creds = pickle.load(token)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_file, SCOPES)
                creds = flow.run_local_server(port=0)
            with open(self.token_file, 'wb') as token:
                pickle.dump(creds, token)
        service = build('calendar', 'v3', credentials=creds)
        return service

    def _sanitize_event_id(self, uid: str) -> str:
        # Google event id must be between 5 and 1024 characters, and may contain only lowercase letters, digits, hyphens, and underscores.
        sanitized = re.sub(r'[^a-z0-9\-_]', '', uid.lower())
        if len(sanitized) < 5:
            sanitized = (sanitized + '00000')[:5]
        return sanitized

    def _convert_event_to_body(self, event: CalendarEvent, include_id: bool = False) -> dict:
        logger = logging.getLogger(__name__)
        logger.debug("[GoogleCalendarClient] Converting event to body. UID: %s, Start: %s (%s), End: %s (%s)", event.uid, event.start, type(event.start), event.end, type(event.end))
        if event.start is None or event.end is None:
            raise ValueError("Event missing start or end time")
        body = {
            'summary': event.summary,
            'start': {},
            'end': {}
        }
        if include_id:
            body['id'] = self._sanitize_event_id(event.uid)
            body['iCalUID'] = event.uid

        if event.is_all_day:
            body['start'] = {'date': event.start.date().isoformat()}
            body['end'] = {'date': event.end.date().isoformat()}
        else:
            # For timed events, if the datetime objects are naive assign UTC, otherwise use the object's timezone
            if event.start.tzinfo is None or event.start.tzinfo.utcoffset(event.start) is None:
                start_body = {'dateTime': event.start.isoformat(), 'timeZone': 'UTC'}
            else:
                start_body = {'dateTime': event.start.isoformat()}

            if event.end.tzinfo is None or event.end.tzinfo.utcoffset(event.end) is None:
                end_body = {'dateTime': event.end.isoformat(), 'timeZone': 'UTC'}
            else:
                end_body = {'dateTime': event.end.isoformat()}

            body['start'] = start_body
            body['end'] = end_body
        
        if event.description:
            body['description'] = event.description
        if event.location:
            body['location'] = event.location
        if event.recurrence:
            # The API expects recurrence rules as a list
            body['recurrence'] = [event.recurrence]

        # If this is a privacy event, add extended properties to store the source UID
        if event.uid.startswith("PRIVACY-SYNC-"):
            source_uid = event.uid[len("PRIVACY-SYNC-"):]
            body['extendedProperties'] = {"private": {"source_uid": source_uid}}

        return body

    def list_events(self, calendar_id: str, start: Optional[datetime.datetime] = None, end: Optional[datetime.datetime] = None) -> list:
        if start is None:
            start = datetime.datetime.utcnow()
        if end is None:
            end = start + datetime.timedelta(days=30)

        time_min = start.isoformat() + 'Z'
        time_max = end.isoformat() + 'Z'

        events_result = self.service.events().list(calendarId=calendar_id,
                                                     timeMin=time_min,
                                                     timeMax=time_max,
                                                     singleEvents=True,
                                                     orderBy='startTime').execute()
        events = events_result.get('items', [])
        list_of_events = []
        for e in events:
            start_info = e.get('start', {})
            end_info = e.get('end', {})
            start_str = start_info.get('dateTime') if 'dateTime' in start_info else start_info.get('date')
            end_str = end_info.get('dateTime') if 'dateTime' in end_info else end_info.get('date')
            try:
                if 'dateTime' in start_info:
                    start_dt = datetime.datetime.fromisoformat(start_str.replace('Z','+00:00'))
                    end_dt = datetime.datetime.fromisoformat(end_str.replace('Z','+00:00'))
                    is_all_day = False
                else:
                    start_dt = datetime.datetime.fromisoformat(start_str)
                    end_dt = datetime.datetime.fromisoformat(end_str)
                    is_all_day = True
            except Exception:
                continue
            # Retrieve extendedProperties if set for privacy events
            ext = e.get('extendedProperties', {}).get('private', {}).get('source_uid')
            if ext:
                final_uid = "PRIVACY-SYNC-" + ext
            else:
                final_uid = e.get('iCalUID', e.get('id'))
            ce = CalendarEvent(
                uid = final_uid,
                summary = e.get('summary', ''),
                start = start_dt,
                end = end_dt,
                description = e.get('description'),
                location = e.get('location'),
                recurrence = None,  # Recurrence handling can be expanded if needed
                is_all_day = is_all_day,
                ical_data = ''
            )
            list_of_events.append(ce)
        return list_of_events

    def create_event(self, calendar_id: str, event: CalendarEvent) -> str:
        logger = logging.getLogger(__name__)
        logger.debug("[GoogleCalendarClient] Creating event in Google Calendar. UID: %s, Start: %s, End: %s, All-day: %s", event.uid, event.start, event.end, event.is_all_day)
        logger.debug("[GoogleCalendarClient] Event details: UID: %s, Start: %s (%s), End: %s (%s), All-day: %s", event.uid, event.start, type(event.start), event.end, type(event.end), event.is_all_day)
        try:
            # Do not include a custom id so Google generates a proper event id
            body = self._convert_event_to_body(event, include_id=False)
        except Exception as e:
            logger.error("[GoogleCalendarClient] Error converting event to body for UID %s. Details: Start: %s (%s), End: %s (%s). Exception: %s", event.uid, event.start, type(event.start), event.end, type(event.end), e)
            raise
        created_event = self.service.events().insert(calendarId=calendar_id, body=body).execute()
        logger.debug("[GoogleCalendarClient] Created event with ID: %s", created_event.get('id'))
        return created_event.get('id')

    def update_event(self, calendar_id: str, event: CalendarEvent) -> None:
        logger = logging.getLogger(__name__)
        logger.debug("[GoogleCalendarClient] Updating event in Google Calendar. UID: %s, Start: %s, End: %s, All-day: %s", event.uid, event.start, event.end, event.is_all_day)
        logger.debug("[GoogleCalendarClient] Event details: UID: %s, Start: %s (%s), End: %s (%s), All-day: %s", event.uid, event.start, type(event.start), event.end, type(event.end), event.is_all_day)
        try:
            event_id = self._sanitize_event_id(event.uid)
            body = self._convert_event_to_body(event, include_id=False)
        except Exception as e:
            logger.error("[GoogleCalendarClient] Error converting event to body for UID %s. Details: Start: %s (%s), End: %s (%s). Exception: %s", event.uid, event.start, type(event.start), event.end, type(event.end), e)
            raise
        self.service.events().update(calendarId=calendar_id, eventId=event_id, body=body).execute()
        logger.debug("[GoogleCalendarClient] Updated event for UID: %s", event.uid)

    def delete_event(self, calendar_id: str, event_uid: str) -> None:
        if event_uid.startswith("PRIVACY-SYNC-"):
            source_uid = event_uid[len("PRIVACY-SYNC-"):] 
            events_result = self.service.events().list(
                calendarId=calendar_id,
                privateExtendedProperty=f"source_uid={source_uid}"
            ).execute()
            events = events_result.get('items', [])
            for event in events:
                self.service.events().delete(calendarId=calendar_id, eventId=event['id']).execute()
        else:
            event_id = self._sanitize_event_id(event_uid)
            self.service.events().delete(calendarId=calendar_id, eventId=event_id).execute()

    def list_calendars(self) -> list:
        """List all calendars accessible by the authenticated Google account."""
        logger = logging.getLogger(__name__)
        try:
            calendar_list = self.service.calendarList().list().execute()
            calendars = calendar_list.get('items', [])
            logger.info("Available Google Calendars:")
            for calendar in calendars:
                logger.info(f"- {calendar['summary']} (ID: {calendar['id']})")
            return calendars
        except Exception as e:
            logger.error(f"Failed to list Google calendars: {e}")
            return [] 