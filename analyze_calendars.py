import caldav
import datetime
import pytz
from icalendar import Calendar
import json
from pprint import pprint

# Calendar configurations
nextcloud_url = "https://cloud.reppekus.com/remote.php/dav"
nextcloud_username = "AFR"
nextcloud_password = "jusfeq-qejqo1-woDzov"
nextcloud_calendar_name = "ProSi"

kerio_url = "https://kerio1.kampmail.de/caldav/"
kerio_username = "frederike.reppekus@pro-sicherheit.net"
kerio_password = "c411faCj8"
kerio_calendar_name = "ProSi"

def connect_calendar(url, username, password, calendar_name):
    print(f"\nConnecting to calendar at {url}")
    client = caldav.DAVClient(url=url, username=username, password=password)
    principal = client.principal()
    calendars = principal.calendars()
    
    for calendar in calendars:
        if calendar.name.lower() == calendar_name.lower():
            print(f"Found calendar: {calendar.name}")
            return calendar
    return None

def analyze_event(event_data, source):
    """Analyze a single event's data structure"""
    cal = Calendar.from_ical(event_data)
    events = []
    
    for component in cal.walk('VEVENT'):
        event_info = {
            'source': source,
            'uid': str(component.get('uid', '')),
            'summary': str(component.get('summary', '')),
            'start': component.get('dtstart'),
            'end': component.get('dtend'),
            'rrule': component.get('rrule'),
            'recurrence_id': component.get('recurrence-id'),
            'last_modified': component.get('last-modified'),
            'sequence': component.get('sequence'),
            'dtstamp': component.get('dtstamp'),
            'created': component.get('created'),
            'organizer': component.get('organizer'),
            'status': component.get('status'),
            'transp': component.get('transp'),
            'raw_data': event_data.decode('utf-8') if isinstance(event_data, bytes) else event_data
        }
        
        # Extract all custom properties (X- properties)
        for name, value in component.items():
            if str(name).startswith('X-'):
                event_info[str(name)] = str(value)
        
        events.append(event_info)
    return events

def analyze_calendars():
    # Connect to both calendars
    nextcloud_cal = connect_calendar(nextcloud_url, nextcloud_username, nextcloud_password, nextcloud_calendar_name)
    kerio_cal = connect_calendar(kerio_url, kerio_username, kerio_password, kerio_calendar_name)
    
    if not nextcloud_cal or not kerio_cal:
        print("Failed to connect to one or both calendars")
        return
    
    # Get events from last month to next month
    now = datetime.datetime.now(pytz.UTC)
    start = now - datetime.timedelta(days=30)
    end = now + datetime.timedelta(days=30)
    
    print("\nFetching Nextcloud events...")
    nextcloud_events = list(nextcloud_cal.date_search(start=start, end=end))
    print(f"Found {len(nextcloud_events)} events in Nextcloud")
    
    print("\nFetching Kerio events...")
    kerio_events = list(kerio_cal.date_search(start=start, end=end))
    print(f"Found {len(kerio_events)} events in Kerio")
    
    # Analyze events
    all_events = []
    
    print("\nAnalyzing Nextcloud events...")
    for event in nextcloud_events:
        try:
            analyzed = analyze_event(event.data, "Nextcloud")
            all_events.extend(analyzed)
        except Exception as e:
            print(f"Error analyzing Nextcloud event: {str(e)}")
    
    print("\nAnalyzing Kerio events...")
    for event in kerio_events:
        try:
            analyzed = analyze_event(event.data, "Kerio")
            all_events.extend(analyzed)
        except Exception as e:
            print(f"Error analyzing Kerio event: {str(e)}")
    
    # Group events by UID
    events_by_uid = {}
    for event in all_events:
        uid = event['uid']
        if uid not in events_by_uid:
            events_by_uid[uid] = {'Nextcloud': [], 'Kerio': []}
        events_by_uid[uid][event['source']].append(event)
    
    # Find and analyze VKJK Jour Fixe
    vkjk_events = None
    for uid, sources in events_by_uid.items():
        if sources['Nextcloud'] and 'VKJK Jour Fixe' in sources['Nextcloud'][0]['summary']:
            vkjk_events = sources
            break
    
    if not vkjk_events:
        print("\nVKJK Jour Fixe event not found!")
        return
    
    print("\n=== VKJK Jour Fixe Analysis ===")
    print(f"\nEvent UID: {vkjk_events['Nextcloud'][0]['uid']}")
    print(f"Summary: {vkjk_events['Nextcloud'][0]['summary']}")
    
    # Compare RRULE
    nc_rrule = vkjk_events['Nextcloud'][0].get('rrule')
    k_rrule = vkjk_events['Kerio'][0].get('rrule')
    print("\nRRULE comparison:")
    print(f"  Nextcloud: {nc_rrule}")
    print(f"  Kerio: {k_rrule}")
    
    # Compare instances
    print(f"\nInstances in Nextcloud: {len(vkjk_events['Nextcloud'])}")
    print(f"Instances in Kerio: {len(vkjk_events['Kerio'])}")
    
    print("\n=== Nextcloud Instances ===")
    for e in sorted(vkjk_events['Nextcloud'], key=lambda x: x['start'].dt if x['start'] else datetime.datetime.max):
        print(f"\nInstance:")
        print(f"  Recurrence ID: {e['recurrence_id']}")
        print(f"  Start: {e['start'].dt if e['start'] else 'None'}")
        print(f"  End: {e['end'].dt if e['end'] else 'None'}")
        print(f"  Last Modified: {e['last_modified']}")
        print(f"  Sequence: {e['sequence']}")
        print(f"  Status: {e['status']}")
        print(f"  Created: {e['created']}")
        print(f"  Organizer: {e['organizer']}")
        
        # Print custom properties
        custom_props = {k: v for k, v in e.items() if str(k).startswith('X-')}
        if custom_props:
            print("  Custom Properties:")
            for k, v in custom_props.items():
                print(f"    {k}: {v}")
    
    print("\n=== Kerio Instances ===")
    for e in sorted(vkjk_events['Kerio'], key=lambda x: x['start'].dt if x['start'] else datetime.datetime.max):
        print(f"\nInstance:")
        print(f"  Recurrence ID: {e['recurrence_id']}")
        print(f"  Start: {e['start'].dt if e['start'] else 'None'}")
        print(f"  End: {e['end'].dt if e['end'] else 'None'}")
        print(f"  Last Modified: {e['last_modified']}")
        print(f"  Sequence: {e['sequence']}")
        print(f"  Status: {e['status']}")
        print(f"  Created: {e['created']}")
        print(f"  Organizer: {e['organizer']}")
        
        # Print custom properties
        custom_props = {k: v for k, v in e.items() if str(k).startswith('X-')}
        if custom_props:
            print("  Custom Properties:")
            for k, v in custom_props.items():
                print(f"    {k}: {v}")
    
    # Show raw data of master events
    print("\n=== Master Event Raw Data ===")
    print("\nNextcloud:")
    master_nc = next((e for e in vkjk_events['Nextcloud'] if not e['recurrence_id']), None)
    if master_nc:
        print(master_nc['raw_data'])
    else:
        print("No master event found in Nextcloud!")
        
    print("\nKerio:")
    master_k = next((e for e in vkjk_events['Kerio'] if not e['recurrence_id']), None)
    if master_k:
        print(master_k['raw_data'])
    else:
        print("No master event found in Kerio!")

if __name__ == "__main__":
    analyze_calendars() 