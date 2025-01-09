import caldav
from sync_caldav import CalendarSync

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