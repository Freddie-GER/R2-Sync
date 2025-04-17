# Calendar Sync Tool

A robust Python-based calendar synchronization tool that enables secure and flexible synchronization between Nextcloud, Kerio CalDAV servers, and Google Calendar.

## Features

- Two-way calendar synchronization between Nextcloud and Kerio
- One-way synchronization with privacy mode (showing only "Busy" status)
- Google Calendar integration for one-way synchronization
- Configurable through environment variables
- Secure handling of sensitive calendar data
- Support for multiple calendar pairs
- Calendar discovery mode for easy setup

## Requirements

- Python 3.9+
- Access to Nextcloud and Kerio CalDAV servers
- Google Calendar API credentials (for Google Calendar integration)
- Required Python packages (installed automatically via setup.py)

## Installation

There are two ways to install the Calendar Sync Tool:

### Method 1: Development Installation

1. Clone the repository:
```bash
git clone https://github.com/Freddie-GER/R2-Sync.git
cd R2-Sync
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
- Create a `r2-sync` command-line tool
- Make the package available in your Python environment

## Deployment Options (Alpha)

For headless server deployment, we provide several options in the `deploy` directory:

### Ubuntu Server Deployment

We offer two deployment methods for Ubuntu servers:
1. **Direct installation** with systemd service
2. **Docker-based** containerized deployment

See the `deploy/INSTALL_UBUNTU.md` file for detailed instructions.

> **Note**: These deployment options are currently in alpha state and may require adjustments for your specific environment.

### Automated Setup Script

For easier deployment, you can use the provided setup script:

```bash
# Make the script executable
chmod +x deploy/setup_ubuntu.sh

# Run the setup script
./deploy/setup_ubuntu.sh
```

The script will guide you through the installation process.

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
    "meetings@nextcloud:external@kerio:one_way:true",
    "personal@nextcloud:your-calendar@google:one_way:true"
]

# Optional Settings
SYNC_INTERVAL_MINUTES=5  # Default is 5 minutes
LOG_LEVEL=INFO          # Default is INFO
PRIVACY_EVENT_TITLE=Busy  # Default is "Busy"
PRIVACY_EVENT_PREFIX=PRIVACY-SYNC-  # Default prefix for privacy events
```

### Google Calendar Configuration

For Google Calendar integration:

1. Create a project in the [Google Cloud Console](https://console.cloud.google.com/)
2. Enable the Google Calendar API
3. Create OAuth 2.0 credentials (Desktop application)
4. Download the credentials JSON file and save it as `client_secret_*.json` in your project directory
5. The first run will prompt for authentication to generate the token file

## Usage

### Running the Sync Tool

If installed via requirements.txt:
```bash
python -m calendar_sync
```

If installed as a package:
```bash
r2-sync
```

### Discovery Mode

To help set up your calendar pairs, use discovery mode:

```bash
# If installed via requirements.txt:
python -m calendar_sync --discover

# If installed as a package:
r2-sync --discover
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
- Google API credentials and tokens are stored locally and should be protected

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Changelog

### 2.1.0 (2025-03-13)

- Implemented mass-deletion approach for privacy events on both Google and Kerio calendars
- Improved error handling for 404 responses during event deletion
- Enhanced logging to better report deletion statuses
- Fixed issues with privacy event synchronization and cleanup
- Updated Google Calendar integration to handle event deletion more effectively

### 2.0.0 (2025-02-16)

- Implemented busy event filtering in two-way sync to exclude events with the title "Busy" from syncing, thus preventing privacy events from being synced from Kerio back to Nextcloud.
- Updated the deletion logic for busy (privacy) events on both Google and Kerio calendars to handle events more gracefully.
- Improved logging to better report deletion statuses (e.g., handling 404 responses as informational).
- Updated the requirements file to reflect updated dependency versions for google-api-python-client, caldav, python-dotenv, and others. 