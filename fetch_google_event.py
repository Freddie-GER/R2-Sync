import datetime
import logging

from calendar_sync.google_calendar_client import GoogleCalendarClient


def main():
    # Configure basic logging
    logging.basicConfig(level=logging.DEBUG)

    # Create an instance of GoogleCalendarClient
    client = GoogleCalendarClient()

    # Use the test Google Calendar ID (from our configuration, typically the email address is used, e.g., 'r2reppekus@gmail.com')
    calendar_id = 'r2reppekus@gmail.com'
    
    # Define a time range: now to 30 days ahead
    now = datetime.datetime.utcnow()
    end = now + datetime.timedelta(days=30)

    try:
        events = client.list_events(calendar_id, start=now, end=end)
        if events:
            print('Fetched events from Google Calendar:')
            for event in events:
                print('Event UID:', event.uid)
                print('Summary:', event.summary)
                print('Start:', event.start)
                print('End:', event.end)
                print('All-day:', event.is_all_day)
                print('Description:', event.description)
                print('Location:', event.location)
                print('---')
        else:
            print('No events found in the specified time range.')
    except Exception as e:
        print(f'Error fetching events: {e}')


if __name__ == '__main__':
    main() 