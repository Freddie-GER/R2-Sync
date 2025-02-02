# Calendar Sync Tool

A robust Python-based calendar synchronization tool that enables secure and flexible synchronization between Nextcloud and Kerio CalDAV servers.

## Features

- Two-way calendar synchronization between Nextcloud and Kerio
- One-way synchronization with privacy mode (showing only "Busy" status)
- Configurable through environment variables
- Secure handling of sensitive calendar data
- Support for multiple calendar pairs

## Requirements

- Python 3.9+
- Access to Nextcloud and Kerio CalDAV servers
- Required Python packages (see `requirements.txt`)

## Installation

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

4. Copy the example environment file and configure your settings:
```bash
cp .env.example .env
```

## Configuration

Edit the `.env` file with your calendar server details:

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
```

## Usage

Run the sync tool:
```bash
python -m calendar_sync
```

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