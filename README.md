# R2 Calendar Sync

A robust calendar synchronization tool that handles both regular calendar sync and privacy-preserving busy sync between CalDAV calendars (specifically Nextcloud and Kerio).

## Features

- **Dual Sync Mode**:
  - Regular 1:1 sync for work calendar (full event details)
  - Privacy-preserving busy sync for personal calendars (only shows as "busy")

- **Smart Event Handling**:
  - Supports both single events and recurring series
  - Handles event updates and deletions
  - Detects and removes duplicate events
  - Uses UIDs and instance-specific dates for reliable matching

- **Privacy Features**:
  - Converts personal calendar events to private "busy" blocks
  - No event details are transferred for private events
  - Maintains accurate availability information

- **Wide Compatibility**:
  - Works with Nextcloud CalDAV
  - Works with Kerio CalDAV
  - Extensible to other CalDAV servers

## Requirements

- Python 3.6+
- Required Python packages (see `requirements.txt`):
  - `caldav>=1.3.0`
  - `icalendar>=5.0.0`
  - `pytz>=2023.3`
  - `python-dotenv>=1.0.0`

## Setup

1. Clone this repository:
   ```bash
   git clone https://github.com/yourusername/r2-calendar-sync.git
   cd r2-calendar-sync
   ```

2. Install required packages:
   ```bash
   pip install -r requirements.txt
   ```

3. Copy the configuration template:
   ```bash
   cp config.env.example config.env
   ```

4. Edit `config.env` and fill in your calendar credentials:
   ```env
   # Nextcloud configuration
   NEXTCLOUD_URL=https://your-nextcloud-server/remote.php/dav
   NEXTCLOUD_USERNAME=your_username
   NEXTCLOUD_PASSWORD=your_password
   NEXTCLOUD_PROSI_CALENDAR=ProSi

   # Personal calendars for busy-only sync
   NEXTCLOUD_PRIVATE_CALENDAR=Privat
   NEXTCLOUD_R2SERVICES_CALENDAR=R2 Services
   NEXTCLOUD_R2BRAIN_CALENDAR=R2 Brainworks

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
1. Connect to all configured calendars
2. Perform regular 1:1 sync for the work calendar
3. Perform busy sync for personal calendars
4. Clean up any obsolete events

## How It Works

### Regular Sync
- Performs a full 1:1 sync of the work calendar
- Preserves all event details and properties
- Handles recurring events and series
- Manages deletions and updates

### Busy Sync
- Converts personal calendar events to private "busy" events
- Only shows time slots as occupied
- No private event details are transferred
- Maintains proper recurring event patterns

### Event Matching
- Uses unique identifiers (UIDs) to track events
- For recurring events: Matches instances using UID and date
- For single events: Matches using UID, summary, and datetime
- Handles timezone differences properly

## Limitations

- One-way sync only (source → target)
- Syncs events within a configurable time window (default: 1 year)
- Both calendar servers must support CalDAV
- Personal calendar events only show as "busy" in target calendar

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Original implementation by Frederike Reppekus
- Inspired by various CalDAV sync implementations
- Uses the excellent `caldav` Python library 