import datetime
import logging

from calendar_sync.google_calendar_client import GoogleCalendarClient
from calendar_sync.caldav_client import CalendarEvent


def main():
    # Configure basic logging
    logging.basicConfig(level=logging.DEBUG)

    # Create an instance of GoogleCalendarClient
    gc = GoogleCalendarClient()

    # Create a dummy timed event (Nextcloud event with specific times)
    timed_event = CalendarEvent(
        uid='timed-event-123',
        summary='Test Timed Event',
        start=datetime.datetime(2023, 10, 15, 10, 0, 0),
        end=datetime.datetime(2023, 10, 15, 11, 0, 0),
        description='This is a timed test event',
        location='Virtual Meeting Room',
        recurrence=None,
        is_all_day=False,
        ical_data=''
    )

    # Convert timed event to Google Calendar API body
    try:
        timed_body = gc._convert_event_to_body(timed_event, include_id=True)
        print('Timed Event Conversion:')
        print(timed_body)
    except Exception as e:
        print(f'Error converting timed event: {e}')

    # Create a dummy all-day event
    all_day_event = CalendarEvent(
        uid='all-day-event-456',
        summary='Test All-Day Event',
        start=datetime.datetime(2023, 10, 16),
        end=datetime.datetime(2023, 10, 17),
        description='This is an all-day test event',
        location='Office',
        recurrence=None,
        is_all_day=True,
        ical_data=''
    )

    # Convert all-day event to Google Calendar API body
    try:
        all_day_body = gc._convert_event_to_body(all_day_event, include_id=True)
        print('\nAll-Day Event Conversion:')
        print(all_day_body)
    except Exception as e:
        print(f'Error converting all-day event: {e}')


if __name__ == '__main__':
    main() 