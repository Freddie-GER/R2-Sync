"""
Runner script for CalDAV Instance-Based Calendar Sync
"""

import os
import caldav
from caldav_instance_sync import CalendarSync
from busy_sync import BusySync
from dotenv import load_dotenv

# Load configuration from env file
load_dotenv('config.env')

# Calendar configurations
nextcloud_url = os.getenv('NEXTCLOUD_URL')
nextcloud_username = os.getenv('NEXTCLOUD_USERNAME')
nextcloud_password = os.getenv('NEXTCLOUD_PASSWORD')
nextcloud_prosi_calendar = os.getenv('NEXTCLOUD_PROSI_CALENDAR')

# Personal calendars for busy sync
nextcloud_private_calendar = os.getenv('NEXTCLOUD_PRIVATE_CALENDAR')
nextcloud_r2services_calendar = os.getenv('NEXTCLOUD_R2SERVICES_CALENDAR')
nextcloud_r2brain_calendar = os.getenv('NEXTCLOUD_R2BRAIN_CALENDAR')

# Kerio configuration
kerio_url = os.getenv('KERIO_URL')
kerio_username = os.getenv('KERIO_USERNAME')
kerio_password = os.getenv('KERIO_PASSWORD')
kerio_calendar = os.getenv('KERIO_CALENDAR')

def connect_calendar(url, username, password, calendar_name):
    """Connect to a CalDAV calendar"""
    if not all([url, username, password, calendar_name]):
        raise ValueError("Missing required configuration. Please check your config.env file.")
        
    client = caldav.DAVClient(url=url, username=username, password=password)
    principal = client.principal()
    calendars = principal.calendars()
    
    for calendar in calendars:
        if calendar.name.lower() == calendar_name.lower():
            return calendar
    raise Exception(f"Calendar {calendar_name} not found")

def main():
    # Connect to Nextcloud calendars
    nextcloud_client = caldav.DAVClient(url=nextcloud_url, username=nextcloud_username, password=nextcloud_password)
    nextcloud_principal = nextcloud_client.principal()
    nextcloud_calendars = nextcloud_principal.calendars()
    
    # Find all required calendars
    prosi_calendar = None
    private_calendar = None
    r2services_calendar = None
    r2brain_calendar = None
    
    for calendar in nextcloud_calendars:
        name = calendar.name.lower()
        if name == nextcloud_prosi_calendar.lower():
            prosi_calendar = calendar
        elif name == nextcloud_private_calendar.lower():
            private_calendar = calendar
        elif name == nextcloud_r2services_calendar.lower():
            r2services_calendar = calendar
        elif name == nextcloud_r2brain_calendar.lower():
            r2brain_calendar = calendar
    
    if not prosi_calendar:
        raise Exception(f"ProSi calendar {nextcloud_prosi_calendar} not found")
    
    # Connect to Kerio calendar
    kerio_cal = connect_calendar(kerio_url, kerio_username, kerio_password, kerio_calendar)
    
    # 1. Regular sync for ProSi calendar
    print("Starting regular sync for ProSi calendar...")
    sync = CalendarSync(source_calendar=prosi_calendar, target_calendar=kerio_cal)
    sync.sync()
    
    # 2. Busy sync for personal calendars
    print("\nStarting busy sync for personal calendars...")
    source_calendars = []
    
    # Add available personal calendars
    if private_calendar:
        source_calendars.append(private_calendar)
    if r2services_calendar:
        source_calendars.append(r2services_calendar)
    if r2brain_calendar:
        source_calendars.append(r2brain_calendar)
    
    if source_calendars:
        busy_sync = BusySync(source_calendars=source_calendars, target_calendar=kerio_cal)
        busy_sync.sync()
    else:
        print("No personal calendars found for busy sync")

if __name__ == "__main__":
    main() 