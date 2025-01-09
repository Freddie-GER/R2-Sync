"""
Runner script for CalDAV Instance-Based Calendar Sync
"""

import os
import caldav
from caldav_instance_sync import CalendarSync
from dotenv import load_dotenv

# Load configuration from env file
load_dotenv('config.env')

# Calendar configurations
nextcloud_url = os.getenv('NEXTCLOUD_URL')
nextcloud_username = os.getenv('NEXTCLOUD_USERNAME')
nextcloud_password = os.getenv('NEXTCLOUD_PASSWORD')
nextcloud_calendar_name = os.getenv('NEXTCLOUD_CALENDAR')

kerio_url = os.getenv('KERIO_URL')
kerio_username = os.getenv('KERIO_USERNAME')
kerio_password = os.getenv('KERIO_PASSWORD')
kerio_calendar_name = os.getenv('KERIO_CALENDAR')

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
    # Connect to calendars
    nextcloud_cal = connect_calendar(nextcloud_url, nextcloud_username, nextcloud_password, nextcloud_calendar_name)
    kerio_cal = connect_calendar(kerio_url, kerio_username, kerio_password, kerio_calendar_name)
    
    # Create sync object and run sync
    sync = CalendarSync(source_calendar=nextcloud_cal, target_calendar=kerio_cal)
    sync.sync()

if __name__ == "__main__":
    main() 