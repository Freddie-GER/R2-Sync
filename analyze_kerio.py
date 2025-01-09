import caldav
import datetime
import pytz
from icalendar import Calendar
import json
from pprint import pprint

# Calendar configurations
kerio_url = "https://kerio1.kampmail.de/caldav/"
kerio_username = "frederike.reppekus@pro-sicherheit.net"
kerio_password = "c411faCj8"
kerio_calendar_name = "ProSi"

def analyze_kerio_events():
    print("Connecting to Kerio calendar...")
    client = caldav.DAVClient(url=kerio_url, username=kerio_username, password=kerio_password)
    principal = client.principal()
    calendars = principal.calendars()
    
    calendar = None
    for cal in calendars:
        if cal.name.lower() == kerio_calendar_name.lower():
            calendar = cal
            break
    
    if not calendar:
        print("Calendar not found!")
        return
    
    # Get events for a longer period to catch recurring patterns
    now = datetime.datetime.now(pytz.UTC)
    start = now - datetime.timedelta(days=30)
    end = now + datetime.timedelta(days=180)  # Look 6 months ahead
    
    print("\nFetching Kerio events...")
    events = calendar.date_search(start=start, end=end)
    
    print(f"\nAnalyzing {len(events)} events from Kerio:")
    print("Looking for KERIOSERIE events...")
    
    kerio_series_events = []
    
    for event in events:
        cal = Calendar.from_ical(event.data)
        for component in cal.walk('VEVENT'):
            summary = str(component.get('summary', '')).strip()
            if 'KERIOSERIE' in summary.upper():
                print(f"\nFound KERIOSERIE event!")
                print("All Properties:")
                for name, value in component.items():
                    print(f"  {name}: {value}")
                
                event_info = {
                    'summary': summary,
                    'uid': str(component.get('uid', '')),
                    'start': component.get('dtstart').dt,
                    'rrule': component.get('rrule'),
                    'recurrence_id': component.get('recurrence-id'),
                    'sequence': component.get('sequence'),
                    'raw_data': event.data if isinstance(event.data, str) else event.data.decode('utf-8')
                }
                kerio_series_events.append(event_info)
    
    if not kerio_series_events:
        print("\nNo KERIOSERIE events found!")
        return
    
    print("\n=== KERIOSERIE Analysis ===")
    print(f"Found {len(kerio_series_events)} instances")
    
    # Analyze UIDs
    uids = set(e['uid'] for e in kerio_series_events)
    print("\nUnique UIDs used:")
    for uid in uids:
        print(f"  {uid}")
    
    # Check for recurring event properties
    has_rrule = any(e['rrule'] for e in kerio_series_events)
    has_recurrence_id = any(e['recurrence_id'] for e in kerio_series_events)
    print(f"\nHas RRULE: {has_rrule}")
    print(f"Has RECURRENCE-ID: {has_recurrence_id}")
    
    # Show example event data
    print("\nFirst instance details:")
    first_event = kerio_series_events[0]
    print(f"Summary: {first_event['summary']}")
    print(f"UID: {first_event['uid']}")
    print(f"Start: {first_event['start']}")
    print(f"RRULE: {first_event['rrule']}")
    print(f"RECURRENCE-ID: {first_event['recurrence_id']}")
    print("\nRaw iCal data:")
    print(first_event['raw_data'])

if __name__ == "__main__":
    analyze_kerio_events() 