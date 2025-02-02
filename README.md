# Calendar Sync Tool

A robust Python-based calendar synchronization tool that enables secure and flexible synchronization between Nextcloud and Kerio CalDAV servers.

## Features

- Two-way calendar synchronization between Nextcloud and Kerio
- One-way synchronization with privacy mode (showing only "Busy" status)
- Configurable through environment variables
- Secure handling of sensitive calendar data
- Support for multiple calendar pairs
- Calendar discovery mode for easy setup

## Requirements

- Python 3.9+
- Access to Nextcloud and Kerio CalDAV servers
- Required Python packages (installed automatically via setup.py)

## Installation

There are two ways to install the Calendar Sync Tool:

### Method 1: Development Installation

1. Clone the repository:
```bash
git clone [your-repo-url]
cd calendar-sync
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

### Method 2: Package Installation

This method installs the tool as a command-line utility:

1. Clone the repository and navigate to it
2. Install using pip:
```bash
pip install .
```

This will:
- Install all required dependencies
- Create a `calendar-sync` command-line tool
- Make the package available in your Python environment

## Configuration

1. Copy the example environment file:
```bash
cp .env.example .env
```

2. Edit the `.env` file with your calendar server details:

```env
# Nextcloud Configuration
NEXTCLOUD_URL=https://your-nextcloud-server
NEXTCLOUD_USERNAME=your-username
NEXTCLOUD_PASSWORD=your-password

# Kerio Configuration
KERIO_URL=https://your-kerio-server
KERIO_USERNAME=your-username
KERIO_PASSWORD=your-password

# Calendar Pairs Configuration
# Format: source_calendar:target_calendar:sync_mode:privacy
# sync_mode can be 'two_way' or 'one_way'
# privacy is optional, set to 'true' for privacy mode
CALENDAR_PAIRS=[
    "personal@nextcloud:work@kerio:two_way:false",
    "meetings@nextcloud:external@kerio:one_way:true"
]

# Optional Settings
SYNC_INTERVAL_MINUTES=5  # Default is 5 minutes
LOG_LEVEL=INFO          # Default is INFO
PRIVACY_EVENT_TITLE=Busy  # Default is "Busy"
PRIVACY_EVENT_PREFIX=PRIVACY-SYNC-  # Default prefix for privacy events
```

## Usage

### Running the Sync Tool

If installed via requirements.txt:
```bash
python -m calendar_sync
```

If installed as a package:
```bash
calendar-sync
```

### Discovery Mode

To help set up your calendar pairs, use discovery mode:

```bash
# If installed via requirements.txt:
python -m calendar_sync --discover

# If installed as a package:
calendar-sync --discover
```

Discovery mode will:
1. Connect to your Nextcloud and Kerio servers
2. List all available calendars
3. Show the correct calendar IDs to use in your configuration
4. Help you verify your server connections

## Security Notes

- Privacy mode events are marked with specific identifiers and are excluded from two-way syncs
- Sensitive calendar data is never exposed in privacy mode
- All credentials are stored in environment variables, not in code

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details. 