from calendar_sync.google_calendar_client import GoogleCalendarClient


def main():
    client = GoogleCalendarClient()
    calendars = client.list_calendars()
    if not calendars:
        print('No calendars found.')
    else:
        print('Accessible Google Calendars:')
        for cal in calendars:
            cal_id = cal.get('id', 'N/A')
            summary = cal.get('summary', 'No Title')
            print(f"ID: {cal_id} - Summary: {summary}")

if __name__ == '__main__':
    main() 