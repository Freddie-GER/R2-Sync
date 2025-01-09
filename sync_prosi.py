import caldav
import datetime
import pytz
import sys
from icalendar import Calendar, Event
from tzlocal import get_localzone
import json
from pathlib import Path

# Calendar configurations
nextcloud_url = "https://cloud.reppekus.com/remote.php/dav"
nextcloud_username = "AFR"
nextcloud_password = "jusfeq-qejqo1-woDzov"
nextcloud_calendar_name = "ProSi"

kerio_url = "https://kerio1.kampmail.de/caldav/"
kerio_username = "frederike.reppekus@pro-sicherheit.net"
kerio_password = "c411faCj8"
kerio_calendar_name = "ProSi"

def get_calendar(url, username, password, calendar_name):
    client = caldav.DAVClient(url=url, username=username, password=password)
    principal = client.principal()
    calendars = principal.calendars()
    
    for calendar in calendars:
        if calendar.name.lower() == calendar_name.lower():
            return calendar
    return None

def normalize_event(event_data):
    # Parse the iCalendar data
    cal = Calendar.from_ical(event_data)
    for component in cal.walk('VEVENT'):
        # Convert to local timezone if not already
        local_tz = get_localzone()
        
        start = component.get('dtstart').dt
        if not component.get('dtend'):
            # If no end time, use start time + 1 hour
            end = start + datetime.timedelta(hours=1)
        else:
            end = component.get('dtend').dt
        
        # Handle all-day events
        is_all_day = isinstance(start, datetime.date) and not isinstance(start, datetime.datetime)
        
        # Ensure timezone info for datetime events
        if isinstance(start, datetime.datetime):
            if start.tzinfo is None:
                start = local_tz.localize(start)
            else:
                # Convert to local timezone
                start = start.astimezone(local_tz)
                
        if isinstance(end, datetime.datetime):
            if end.tzinfo is None:
                end = local_tz.localize(end)
            else:
                # Convert to local timezone
                end = end.astimezone(local_tz)
            
        # Get last modified time or use current time
        last_modified = component.get('last-modified')
        if not last_modified:
            last_modified = component.get('dtstamp', datetime.datetime.now(pytz.UTC))
        if isinstance(last_modified, str):
            try:
                last_modified = datetime.datetime.fromisoformat(last_modified)
            except:
                last_modified = datetime.datetime.now(pytz.UTC)
                
        # Handle recurring event
        recurrence_id = component.get('recurrence-id')
        rrule = component.get('rrule')
        uid = str(component.get('uid', ''))
        summary = str(component.get('summary', '')).strip()
        location = str(component.get('location', '')).strip()
        description = str(component.get('description', '')).strip()
        
        # Check if this is a recurring event or part of a series
        is_recurring = bool(rrule) or recurrence_id is not None
        
        # For recurring events, use UID + recurrence ID (if any) as the key
        if is_recurring:
            if recurrence_id:
                # For recurring instances, include the recurrence ID
                recurrence_str = recurrence_id.dt.isoformat() if hasattr(recurrence_id, 'dt') else str(recurrence_id)
                dedup_key = f"{uid}_{summary}_{recurrence_str}"
            else:
                # For master events, just use UID and summary
                dedup_key = f"{uid}_{summary}_master"
        else:
            # For regular events, use full details
            if is_all_day:
                start_str = start.isoformat()
                end_str = end.isoformat()
            else:
                start_str = start.isoformat() if isinstance(start, datetime.datetime) else start.isoformat()
                end_str = end.isoformat() if isinstance(end, datetime.datetime) else end.isoformat()
            
            dedup_key = f"{summary}_{start_str}_{end_str}_{location}_{description}"
        
        event_data = {
            'uid': uid,
            'summary': summary,
            'start': start,
            'end': end,
            'description': description,
            'location': location,
            'last_modified': last_modified,
            'is_recurring': is_recurring,
            'recurrence_id': recurrence_id,
            'rrule': rrule,
            'dedup_key': dedup_key,
            'is_all_day': is_all_day
        }
            
        return event_data
    return None

def clean_duplicates(calendar):
    """Remove duplicate events based on summary and start time"""
    now = datetime.datetime.now(pytz.UTC)
    start = now - datetime.timedelta(days=7)
    end = now + datetime.timedelta(days=30)
    
    events = list(calendar.date_search(start=start, end=end))
    seen_events = {}
    events_to_delete = []
    
    # First pass: collect all events and find the most recent version of each
    for event in events:
        try:
            normalized = normalize_event(event.data)
            if normalized:
                dedup_key = normalized['dedup_key']
                if dedup_key in seen_events:
                    # Keep the event with the most recent last_modified time
                    existing_event = seen_events[dedup_key]
                    existing_modified = existing_event['normalized'].get('last_modified')
                    current_modified = normalized.get('last_modified')
                    
                    # Convert both timestamps to UTC datetime for comparison
                    if isinstance(existing_modified, datetime.datetime):
                        if existing_modified.tzinfo is None:
                            existing_modified = pytz.UTC.localize(existing_modified)
                        else:
                            existing_modified = existing_modified.astimezone(pytz.UTC)
                    else:
                        existing_modified = datetime.datetime.now(pytz.UTC)
                        
                    if isinstance(current_modified, datetime.datetime):
                        if current_modified.tzinfo is None:
                            current_modified = pytz.UTC.localize(current_modified)
                        else:
                            current_modified = current_modified.astimezone(pytz.UTC)
                    else:
                        current_modified = datetime.datetime.now(pytz.UTC)
                    
                    # Now we can safely compare the timestamps
                    if current_modified > existing_modified:
                        # Current event is newer, mark the old one for deletion
                        events_to_delete.append(seen_events[dedup_key]['event'])
                        seen_events[dedup_key] = {'event': event, 'normalized': normalized}
                    else:
                        # Current event is older, mark it for deletion
                        events_to_delete.append(event)
                else:
                    seen_events[dedup_key] = {'event': event, 'normalized': normalized}
        except Exception as e:
            print(f"Error processing event during cleanup: {str(e)}")
            continue
    
    # Second pass: delete duplicate events
    for event in events_to_delete:
        try:
            normalized = normalize_event(event.data)
            if normalized:
                print(f"Removing duplicate event: {normalized['summary']}")
                event.delete()
        except Exception as e:
            print(f"Error deleting duplicate event: {str(e)}")
            continue

def create_recurring_series(events):
    """Create a recurring series from individual events"""
    if not events:
        return None
    
    # Get the first event as a template
    template = events[0]
    cal = Calendar.from_ical(template.data)
    for component in cal.walk('VEVENT'):
        # Create a new event based on the template
        vcal = Calendar()
        vevent = Event()
        
        # Copy basic properties
        vevent.add('summary', component.get('summary'))
        vevent.add('uid', component.get('uid'))
        vevent.add('description', component.get('description', ''))
        vevent.add('location', component.get('location', ''))
        
        # Set start and end time from the template
        vevent.add('dtstart', component.get('dtstart'))
        vevent.add('dtend', component.get('dtend'))
        
        # Add RRULE for second Friday of each month
        vevent.add('rrule', {
            'freq': 'monthly',
            'byday': '2FR'  # Second Friday of each month
        })
        
        vcal.add_component(vevent)
        return [vcal.to_ical().decode('utf-8')]
    return None

def get_master_event(calendar, uid):
    """Get the master event for a recurring series"""
    try:
        print(f"\nSearching for master event with UID: {uid}")
        # First try to find all events with this UID
        events = calendar.search(uid=uid)
        
        print(f"Found {len(events)} events with this UID")
        # Look for the master event (the one without RECURRENCE-ID)
        vkjk_events = []
        for event in events:
            try:
                cal = Calendar.from_ical(event.data)
                for component in cal.walk('VEVENT'):
                    summary = str(component.get('summary', '')).strip()
                    if "VKJK Jour Fixe" in summary:
                        print("\nFound VKJK event:")
                        print(f"Summary: {summary}")
                        print(f"UID: {component.get('uid')}")
                        print(f"RRULE: {component.get('rrule')}")
                        print(f"RECURRENCE-ID: {component.get('recurrence-id')}")
                        print(f"DTSTART: {component.get('dtstart')}")
                        
                        # The master event is the one without a RECURRENCE-ID
                        if not component.get('recurrence-id'):
                            print("Found master event (no RECURRENCE-ID)")
                            return event, component
                        else:
                            vkjk_events.append(event)
            except Exception as e:
                print(f"Error processing event in get_master_event: {str(e)}")
                continue
        
        # If we found multiple VKJK events but no master, create recurring series
        if vkjk_events:
            print("\nCreating recurring series from individual events")
            series_list = create_recurring_series(vkjk_events)
            if series_list:
                # Create both winter and summer series in the target calendar
                for ical_data in series_list:
                    cal = Calendar.from_ical(ical_data)
                    for component in cal.walk('VEVENT'):
                        print(f"Created recurring series with RRULE: {component.get('rrule')}")
                        return None, component
        
        # If still not found, try searching by date range
        print("\nNo master event found by UID, searching by date range...")
        start = datetime.datetime(2025, 1, 1, tzinfo=pytz.UTC)  # start of month
        end = datetime.datetime(2025, 12, 31, tzinfo=pytz.UTC)  # end of year
        
        events = calendar.date_search(start=start, end=end)
        for event in events:
            try:
                cal = Calendar.from_ical(event.data)
                for component in cal.walk('VEVENT'):
                    summary = str(component.get('summary', '')).strip()
                    if "VKJK Jour Fixe" in summary:
                        print("\nFound VKJK event in date range:")
                        print(f"Summary: {summary}")
                        print(f"UID: {component.get('uid')}")
                        print(f"RRULE: {component.get('rrule')}")
                        print(f"RECURRENCE-ID: {component.get('recurrence-id')}")
                        print(f"DTSTART: {component.get('dtstart')}")
                        
                        # If this event has an RRULE, it might be what we want
                        if component.get('rrule'):
                            print("Found event with RRULE")
                            return event, component
            except Exception as e:
                print(f"Error processing event in get_master_event: {str(e)}")
                continue
                
    except Exception as e:
        print(f"Error finding master event: {str(e)}")
    return None, None

def get_series_master(calendar, event_data):
    """Get the master event of a series based on an instance"""
    try:
        uid = event_data['uid']
        events = calendar.search(uid=uid)
        
        # Look for the master event (the one with RRULE but without RECURRENCE-ID)
        for event in events:
            cal = Calendar.from_ical(event.data)
            for component in cal.walk('VEVENT'):
                if component.get('rrule') and not component.get('recurrence-id'):
                    return event, component
        return None, None
    except Exception as e:
        print(f"Error finding series master: {str(e)}")
        return None, None

def get_all_instances(calendar, uid, start_date=None, end_date=None):
    """Get all instances of a series within a date range"""
    if start_date is None:
        start_date = datetime.datetime.now(pytz.UTC)
    if end_date is None:
        end_date = start_date + datetime.timedelta(days=365)  # Look ahead one year
    
    try:
        # First try to find all events with this UID
        all_events = calendar.search(uid=uid)
        instances = []
        
        # Also search by date range to catch all instances
        date_events = calendar.date_search(start=start_date, end=end_date)
        all_events.extend([e for e in date_events if e not in all_events])
        
        for event in all_events:
            try:
                normalized = normalize_event(event.data)
                if normalized and normalized['uid'] == uid:
                    instances.append(normalized)
            except Exception as e:
                print(f"Error processing event in get_all_instances: {str(e)}")
                continue
                
        return instances
    except Exception as e:
        print(f"Error getting instances: {str(e)}")
        return []

def infer_rrule_from_instances(instances):
    """Infer the recurrence rule from a set of event instances"""
    if not instances:
        return None
    
    # First, check all instances for an existing RRULE
    for instance in instances:
        if instance.get('rrule'):
            print(f"Found existing RRULE in instance: {instance['rrule']}")
            return instance['rrule']
    
    # Sort instances by start time
    sorted_instances = sorted(instances, key=lambda x: x['start'])
    
    # Collect all weekdays and their frequencies
    weekdays = {}
    for instance in sorted_instances:
        if isinstance(instance['start'], datetime.datetime):
            weekday = instance['start'].strftime('%a')[:2].upper()
            weekdays[weekday] = weekdays.get(weekday, 0) + 1
    
    print(f"Weekday frequencies: {weekdays}")
    
    # If we have any weekdays, create a weekly rule
    if weekdays:
        # Get all weekdays that appear at least twice
        recurring_weekdays = [day for day, count in weekdays.items() if count >= 2]
        if recurring_weekdays:
            print(f"Found recurring weekdays: {recurring_weekdays}")
            return {'freq': 'weekly', 'byday': recurring_weekdays}
    
    # If no weekly pattern found, check for monthly pattern
    monthly_days = {}
    for instance in sorted_instances:
        if isinstance(instance['start'], datetime.datetime):
            day = instance['start'].day
            monthly_days[day] = monthly_days.get(day, 0) + 1
    
    # Get days that appear at least twice
    recurring_days = [day for day, count in monthly_days.items() if count >= 2]
    if recurring_days:
        print(f"Found monthly pattern on days: {recurring_days}")
        return {'freq': 'monthly', 'bymonthday': recurring_days}
    
    return None

def load_sync_state():
    """Load the saved sync state from file"""
    state_file = Path('sync_state.json')
    if state_file.exists():
        try:
            with open(state_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading sync state: {str(e)}")
    return {
        'last_sync': None,
        'series': {},
        'deleted_uids': set(),  # Track explicitly deleted series
        'version': 1
    }

def save_sync_state(state):
    """Save the current sync state to file"""
    try:
        # Convert sets to lists for JSON serialization
        if 'deleted_uids' in state:
            state['deleted_uids'] = list(state['deleted_uids'])
        
        with open('sync_state.json', 'w') as f:
            json.dump(state, f, indent=2, default=str)
    except Exception as e:
        print(f"Error saving sync state: {str(e)}")

def collect_calendar_data(calendar, calendar_name):
    """Collect all calendar data into a dictionary"""
    now = datetime.datetime.now(pytz.UTC)
    start = now - datetime.timedelta(days=7)
    end = now + datetime.timedelta(days=365 * 2)
    
    print(f"\nCollecting events from {calendar_name}...")
    events = []
    series_events = []
    
    # First collect all events
    calendar_events = list(calendar.date_search(start=start, end=end))
    print(f"Found {len(calendar_events)} raw events")
    
    for event in calendar_events:
        try:
            events.append(event)
            # Process event for series
            normalized = normalize_event(event.data)
            if normalized:
                # Check if this is part of a series
                is_series = normalized['is_recurring'] or normalized.get('recurrence_id')
                if is_series:
                    series_events.append({
                        'event': event,
                        'normalized': normalized,
                        'is_master': bool(normalized.get('rrule') and not normalized.get('recurrence_id'))
                    })
        except Exception as e:
            print(f"Error collecting event: {str(e)}")
    
    # Now process series events
    series = {}
    for series_event in series_events:
        try:
            normalized = series_event['normalized']
            uid = normalized['uid']
            if uid not in series:
                series[uid] = {
                    'master': None,
                    'instances': [],
                    'summary': normalized['summary'],
                    'original_data': None
                }
                print(f"\nFound series in {calendar_name}: {normalized['summary']}")
                print(f"Start: {normalized['start']}")
                print(f"Is recurring: {normalized['is_recurring']}")
                print(f"Has recurrence ID: {normalized.get('recurrence_id') is not None}")
                print(f"RRULE: {normalized.get('rrule')}")
            
            if series_event['is_master']:
                series[uid]['master'] = series_event['event']
                series[uid]['original_data'] = series_event['event'].data
                print(f"Found master event for {normalized['summary']}")
            
            series[uid]['instances'].append(normalized)
        except Exception as e:
            print(f"Error processing series event: {str(e)}")
    
    print(f"Found {len(events)} events and {len(series)} series")
    return {'events': events, 'series': series}

def sync_calendars(initial_sync=False):
    try:
        # Load previous sync state
        sync_state = load_sync_state()
        previous_series = dict(sync_state['series'])  # Make a copy
        deleted_uids = set(sync_state.get('deleted_uids', []))
        
        print(f"Previous state: {len(previous_series)} series, {len(deleted_uids)} deleted UIDs")
        
        # Get both calendars
        nextcloud_cal = get_calendar(nextcloud_url, nextcloud_username, nextcloud_password, nextcloud_calendar_name)
        kerio_cal = get_calendar(kerio_url, kerio_username, kerio_password, kerio_calendar_name)
        
        if not nextcloud_cal or not kerio_cal:
            raise Exception("Could not find one or both calendars")
        
        # Clean up duplicates in both calendars first
        print("Cleaning up duplicates in Nextcloud calendar...")
        clean_duplicates(nextcloud_cal)
        print("Cleaning up duplicates in Kerio calendar...")
        clean_duplicates(kerio_cal)
        
        # Get current time range
        now = datetime.datetime.now(pytz.UTC)
        
        # Collect all calendar data
        nextcloud_data = collect_calendar_data(nextcloud_cal, "Nextcloud")
        kerio_data = collect_calendar_data(kerio_cal, "Kerio")
        
        nextcloud_events = nextcloud_data['events']
        kerio_events = kerio_data['events']
        nextcloud_series = nextcloud_data['series']
        kerio_series = kerio_data['series']
        
        # Now handle remaining series synchronization
        print("\nSyncing remaining series...")
        all_uids = list(set(list(nextcloud_series.keys()) + list(kerio_series.keys())))
        series_to_sync = []
        
        # Initialize new state
        new_state = {
            'series': {},
            'last_sync': now.isoformat(),
            'deleted_uids': deleted_uids,
            'version': 1
        }
        
        # First collect all series that need syncing
        for uid in all_uids:
            try:
                # Skip deleted series
                if uid in deleted_uids:
                    continue
                    
                # Track series state
                series_state = {
                    'uid': uid,
                    'in_nextcloud': uid in nextcloud_series,
                    'in_kerio': uid in kerio_series,
                    'summary': nextcloud_series[uid]['summary'] if uid in nextcloud_series else kerio_series[uid]['summary']
                }
                
                # Add to sync list
                series_to_sync.append({
                    'uid': uid,
                    'state': series_state,
                    'nextcloud_data': nextcloud_series.get(uid),
                    'kerio_data': kerio_series.get(uid)
                })
                
                # Update state for this series
                new_state['series'][uid] = series_state
            except Exception as e:
                print(f"Error preparing series {uid} for sync: {str(e)}")
                continue
        
        # Now process all series that need syncing
        for series in series_to_sync:
            try:
                uid = series['uid']
                nextcloud_data = series['nextcloud_data']
                kerio_data = series['kerio_data']
                
                # If series exists in Nextcloud but not Kerio, sync to Kerio
                if nextcloud_data and not kerio_data:
                    print(f"\nSyncing new series '{nextcloud_data['summary']}' from Nextcloud to Kerio...")
                    try:
                        # Get original data if available
                        original_data = nextcloud_data['original_data']
                        if original_data:
                            print("Using original event data")
                            kerio_cal.save_event(original_data)
                            print("Successfully saved series to Kerio")
                        else:
                            # Fallback to creating from instances
                            instances = nextcloud_data['instances']
                            master = nextcloud_data['master']
                            
                            print(f"Found {len(instances)} instances")
                            for idx, instance in enumerate(instances):
                                print(f"Instance {idx + 1}: {instance['summary']} on {instance['start']}")
                            
                            if master:
                                print("Using master event")
                                kerio_cal.save_event(master.data)
                            else:
                                print("No master event found, creating from instances")
                                # Create new master event from first instance
                                template = instances[0]
                                vcal = Calendar()
                                vevent = Event()
                                vevent.add('summary', template['summary'])
                                vevent.add('dtstart', template['start'])
                                vevent.add('dtend', template['end'])
                                vevent.add('uid', template['uid'])
                                if template.get('description'):
                                    vevent.add('description', template['description'])
                                if template.get('location'):
                                    vevent.add('location', template['location'])
                                
                                # Add RRULE if we can infer it
                                rrule = infer_rrule_from_instances(instances)
                                if rrule:
                                    print(f"Adding inferred RRULE: {rrule}")
                                    vevent.add('rrule', rrule)
                                
                                vcal.add_component(vevent)
                                kerio_cal.save_event(vcal.to_ical().decode('utf-8'))
                                print("Successfully saved series to Kerio")
                    except Exception as e:
                        print(f"Error syncing series to Kerio: {str(e)}")
                
                # If series exists in Kerio but not Nextcloud, sync to Nextcloud
                if kerio_data and not nextcloud_data:
                    print(f"\nSyncing new series '{kerio_data['summary']}' from Kerio to Nextcloud...")
                    try:
                        # Get original data if available
                        original_data = kerio_data['original_data']
                        if original_data:
                            print("Using original event data")
                            nextcloud_cal.save_event(original_data)
                            print("Successfully saved series to Nextcloud")
                        else:
                            # Fallback to creating from instances
                            instances = kerio_data['instances']
                            master = kerio_data['master']
                            
                            print(f"Found {len(instances)} instances")
                            for idx, instance in enumerate(instances):
                                print(f"Instance {idx + 1}: {instance['summary']} on {instance['start']}")
                            
                            if master:
                                print("Using master event")
                                nextcloud_cal.save_event(master.data)
                            else:
                                print("No master event found, creating from instances")
                                # Create new master event from first instance
                                template = instances[0]
                                vcal = Calendar()
                                vevent = Event()
                                vevent.add('summary', template['summary'])
                                vevent.add('dtstart', template['start'])
                                vevent.add('dtend', template['end'])
                                vevent.add('uid', template['uid'])
                                if template.get('description'):
                                    vevent.add('description', template['description'])
                                if template.get('location'):
                                    vevent.add('location', template['location'])
                                
                                # Add RRULE if we can infer it
                                rrule = infer_rrule_from_instances(instances)
                                if rrule:
                                    print(f"Adding inferred RRULE: {rrule}")
                                    vevent.add('rrule', rrule)
                                
                                vcal.add_component(vevent)
                                nextcloud_cal.save_event(vcal.to_ical().decode('utf-8'))
                                print("Successfully saved series to Nextcloud")
                    except Exception as e:
                        print(f"Error syncing series to Nextcloud: {str(e)}")
            except Exception as e:
                print(f"Error syncing series {uid}: {str(e)}")
                continue
        
        # Save the new state
        save_sync_state(new_state)
        
        return {
            'nextcloud_events': len(nextcloud_events),
            'kerio_events': len(kerio_events),
            'sync_time': now.isoformat()
        }
        
    except Exception as e:
        print(f"Error during sync: {str(e)}")
        return None

def test_calendar_permissions(calendar):
    """Test if we can write to the calendar"""
    try:
        # Create a test event
        vcal = Calendar()
        vevent = Event()
        vevent.add('summary', 'Permission Test Event')
        vevent.add('dtstart', datetime.datetime.now(pytz.UTC))
        vevent.add('dtend', datetime.datetime.now(pytz.UTC) + datetime.timedelta(hours=1))
        vcal.add_component(vevent)
        
        # Try to save and immediately delete it
        event = calendar.save_event(vcal.to_ical().decode('utf-8'))
        print("Successfully created test event")
        event.delete()
        print("Successfully deleted test event")
        return True
    except Exception as e:
        print(f"Calendar permission test failed: {str(e)}")
        return False

def force_delete_event(calendar, uid=None, summary=None, target_date=None):
    """Force delete an event by UID, summary, and/or specific date"""
    try:
        matching_events = []
        
        # First try by UID if provided
        if uid:
            events = calendar.search(uid=uid)
            if events:
                print(f"Found {len(events)} events with UID {uid}")
                matching_events.extend(events)
            else:
                print(f"No events found with UID {uid}")
        
        # Search by date range and summary
        if summary or target_date:
            if target_date:
                start = target_date - datetime.timedelta(days=1)
                end = target_date + datetime.timedelta(days=1)
                print(f"\nSearching for events around {target_date.date()}...")
            else:
                start = datetime.datetime.now(pytz.UTC)
                end = start + datetime.timedelta(days=365)
                print(f"\nSearching for events in date range...")
            
            date_events = calendar.date_search(start=start, end=end)
            for event in date_events:
                try:
                    normalized = normalize_event(event.data)
                    if not normalized:
                        continue
                        
                    matches = True
                    # Skip already cancelled events
                    if "(CANCELLED)" in normalized['summary']:
                        continue
                        
                    if summary and summary.lower() not in normalized['summary'].lower():
                        matches = False
                    
                    if target_date and isinstance(normalized['start'], datetime.datetime):
                        event_date = normalized['start'].date()
                        target_date_only = target_date.date()
                        if event_date != target_date_only:
                            matches = False
                    
                    if matches:
                        print(f"Found matching event: {normalized['summary']} on {normalized['start'].date()}")
                        matching_events.append(event)
                except Exception as e:
                    print(f"Error processing event: {str(e)}")
                    continue
        
        # Try to delete each matching event
        for event in matching_events:
            try:
                print("Attempting direct delete...")
                event.delete()
                print("Delete successful")
            except Exception as delete_error:
                print(f"Direct delete failed: {str(delete_error)}")
                try:
                    print("Attempting to overwrite event...")
                    # Parse the original event
                    normalized = normalize_event(event.data)
                    if normalized:
                        # Create a cancelled event with the same UID
                        vcal = Calendar()
                        vevent = Event()
                        # Remove any existing (CANCELLED) suffix before adding it once
                        clean_summary = normalized['summary'].replace(" (CANCELLED)", "")
                        vevent.add('summary', clean_summary + ' (CANCELLED)')
                        vevent.add('dtstart', normalized['start'])
                        vevent.add('dtend', normalized['end'])
                        vevent.add('uid', normalized['uid'])
                        vevent.add('status', 'CANCELLED')
                        vcal.add_component(vevent)
                        
                        # Try to overwrite the event
                        calendar.save_event(vcal.to_ical().decode('utf-8'))
                        print("Successfully overwrote event with cancelled status")
                except Exception as e:
                    print(f"Error overwriting event: {str(e)}")
                    continue
    except Exception as e:
        print(f"Error searching for events: {str(e)}")

if __name__ == "__main__":
    print("Performing bidirectional sync between Nextcloud and Kerio...")
    
    # Get calendars
    nextcloud_cal = get_calendar(nextcloud_url, nextcloud_username, nextcloud_password, nextcloud_calendar_name)
    kerio_cal = get_calendar(kerio_url, kerio_username, kerio_password, kerio_calendar_name)
    
    if not nextcloud_cal or not kerio_cal:
        print("Could not find one or both calendars")
        sys.exit(1)
    
    # Test calendar permissions
    print("\nTesting Nextcloud calendar permissions...")
    if not test_calendar_permissions(nextcloud_cal):
        print("WARNING: Cannot write to Nextcloud calendar!")
    
    print("\nTesting Kerio calendar permissions...")
    if not test_calendar_permissions(kerio_cal):
        print("WARNING: Cannot write to Kerio calendar!")
    
    # Try to force delete problematic events
    test_event_date = datetime.datetime(2025, 1, 15, tzinfo=pytz.UTC)
    print("\nAttempting to force delete Test Event on January 15th...")
    force_delete_event(nextcloud_cal, summary="Test Event", target_date=test_event_date)
    
    test_series_date = datetime.datetime(2025, 3, 3, tzinfo=pytz.UTC)
    print("\nAttempting to force delete Test Serie starting March 3rd...")
    force_delete_event(nextcloud_cal, summary="Test Serie", target_date=test_series_date)
    
    # Now run the normal sync
    result = sync_calendars()
    if result:
        print(f"Sync completed: {result}")
    else:
        print("Sync failed") 