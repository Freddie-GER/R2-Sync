# CalDAV Instance-Based Calendar Sync

A robust calendar synchronization tool that handles both single events and recurring series between CalDAV calendars. This implementation treats all events as individual instances, avoiding the complexity of RRULE handling and working reliably with different CalDAV server implementations.

## Features

- Syncs single events and recurring series between CalDAV calendars
- Handles deletions in both directions
- Detects and removes duplicate events
- Uses UIDs and instance-specific dates for reliable matching
- Works with both Nextcloud and Kerio CalDAV servers
- Preserves all event properties and details

## Requirements

- Python 3.6+
- `caldav` library
- `icalendar` library
- `pytz` library
- `python-dotenv` library

Install required packages:
```bash
pip install caldav icalendar pytz python-dotenv
```

## Setup

1. Clone this repository
2. Copy the configuration template:
   ```bash
   cp config.env.example config.env
   ```
3. Edit `config.env` and fill in your calendar credentials:
   ```env
   # Nextcloud configuration
   NEXTCLOUD_URL=https://your-nextcloud-server/remote.php/dav
   NEXTCLOUD_USERNAME=your_username
   NEXTCLOUD_PASSWORD=your_password
   NEXTCLOUD_CALENDAR=calendar_name

   # Kerio configuration
   KERIO_URL=https://your-kerio-server/caldav/
   KERIO_USERNAME=your_email
   KERIO_PASSWORD=your_password
   KERIO_CALENDAR=calendar_name
   ```

## Usage

Run the sync:
```bash
python run_instance_sync.py
```

The script will:
1. Connect to both calendars
2. Clean up any duplicate events
3. Sync all events from source to target
4. Handle deletions (remove events in target that no longer exist in source)

## How It Works

This implementation takes a unique approach to calendar synchronization:

1. **Instance-Based Sync**: Instead of dealing with recurring event rules (RRULEs), it treats every event occurrence as an individual instance. This works reliably across different CalDAV servers that might handle recurring events differently.

2. **Event Matching**: 
   - For recurring events: Matches instances using UID and RECURRENCE-ID
   - For single events: Matches using UID, summary, and exact datetime

3. **Duplicate Detection**: Identifies duplicates by comparing:
   - Event summary (title)
   - Full datetime (date AND time)
   - Keeps the older version (lower sequence number)

4. **Deletion Handling**: When events are deleted from the source calendar, they are automatically removed from the target calendar.

## Limitations

- The sync is one-way (source → target)
- Syncs events within a 120-day window (30 days past to 90 days future)
- Both calendars must support the CalDAV protocol

## Troubleshooting

Common issues:

1. **Connection Errors**:
   - Verify your calendar URLs are correct
   - Check your username and password
   - Ensure you have network access to both servers

2. **Calendar Not Found**:
   - Verify the calendar names in your config match exactly
   - Check case sensitivity

3. **Sync Issues**:
   - Check the logs for specific error messages
   - Verify both calendars are accessible
   - Ensure you have write permissions on the target calendar

## Contributing

Feel free to submit issues and enhancement requests! 