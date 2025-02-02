"""Calendar discovery tools."""

import logging
import requests
from typing import Dict, List, Tuple
from urllib.parse import urljoin
from requests.exceptions import RequestException

from .caldav_client import CalDAVClient
from .config import ServerConfig

logger = logging.getLogger(__name__)


class ServerType:
    """Known CalDAV server types and their characteristics."""
    NEXTCLOUD = "nextcloud"
    KERIO = "kerio"
    UNKNOWN = "unknown"


def detect_server_type(base_url: str, username: str, password: str) -> tuple[str, str]:
    """
    Detect the CalDAV server type and return its proper endpoint.
    
    Returns:
        tuple: (server_type, caldav_url)
    """
    logger.info(f"Starting server detection for URL: {base_url!r}")  # Use !r to see exact string
    logger.info(f"Username: {username!r}")
    
    # Clean up the base URL
    base_url = base_url.rstrip('/')
    logger.info(f"Cleaned URL: {base_url!r}")
    
    # Common CalDAV endpoints
    endpoints = {
        "": "",  # Base URL
        "/remote.php/dav/calendars": ServerType.NEXTCLOUD,
        "/remote.php/dav": ServerType.NEXTCLOUD,
        "/caldav": ServerType.KERIO,
    }
    
    session = requests.Session()
    session.auth = (username, password)
    
    for endpoint, server_type in endpoints.items():
        url = base_url + endpoint
        try:
            logger.info(f"Trying endpoint: {url!r}")
            response = session.get(url, verify=True)
            headers = response.headers
            
            # Check response patterns
            server_header = headers.get('Server', '').lower()
            powered_by = headers.get('X-Powered-By', '').lower()
            www_auth = headers.get('WWW-Authenticate', '').lower()
            
            logger.info(f"Response code: {response.status_code}")
            logger.info(f"Headers: {dict(headers)}")  # Convert to dict for better logging
            
            # Nextcloud detection
            if any([
                'nextcloud' in server_header,
                'nextcloud' in powered_by,
                'php' in powered_by and '/remote.php/dav' in endpoint,
                response.status_code == 200 and '/remote.php/dav' in endpoint,
                response.status_code == 401 and 'sabre' in www_auth
            ]):
                logger.info(f"Detected Nextcloud server at {url!r}")
                # Always use the /remote.php/dav/calendars endpoint for Nextcloud
                return ServerType.NEXTCLOUD, urljoin(base_url, '/remote.php/dav/calendars/' + username)
            
            # Kerio detection
            if any([
                'kerio' in server_header,
                'kerio' in www_auth,
                response.status_code == 401 and 'kerio' in response.text.lower()
            ]):
                logger.info(f"Detected Kerio server at {url!r}")
                return ServerType.KERIO, urljoin(base_url, '/caldav')
                
        except RequestException as e:
            logger.error(f"Failed to probe {url!r}: {str(e)}")
    
    # If we couldn't detect the server type but found /remote.php/dav, assume it's Nextcloud
    if any(response.status_code == 200 for response in [
        session.get(base_url + '/remote.php/dav', verify=True),
        session.get(base_url + '/remote.php/dav/calendars', verify=True)
    ]):
        logger.info("Found /remote.php/dav endpoint, assuming Nextcloud")
        return ServerType.NEXTCLOUD, urljoin(base_url, '/remote.php/dav/calendars/' + username)
    
    # If we couldn't detect the server type, try the base URL
    logger.warning(f"Could not detect server type, using base URL: {base_url!r}")
    return ServerType.UNKNOWN, base_url


def list_calendars(client: CalDAVClient) -> List[Dict[str, str]]:
    """List available calendars from a CalDAV client."""
    calendars = []
    for calendar in client.principal.calendars():
        calendars.append({
            'id': calendar.id,
            'name': calendar.name,
            'url': calendar.url,
        })
    return calendars


def discover_calendars(nextcloud_config: ServerConfig, kerio_config: ServerConfig) -> None:
    """Discover and print available calendars from both servers."""
    print("\nDiscovering calendars...")
    
    # Detect Nextcloud server type and endpoint
    print("\nProbing Nextcloud server...")
    logger.info(f"Nextcloud config: URL={nextcloud_config.url!r}, Username={nextcloud_config.username!r}")
    nc_type, nc_url = detect_server_type(
        nextcloud_config.url,
        nextcloud_config.username,
        nextcloud_config.password
    )
    
    # Create client with detected URL
    nextcloud_config.url = nc_url
    nextcloud = CalDAVClient(nextcloud_config)
    
    print(f"\nNextcloud Calendars (detected as {nc_type}):")
    print("-" * 50)
    for cal in list_calendars(nextcloud):
        print(f"ID: {cal['id']}")
        print(f"Name: {cal['name']}")
        print(f"URL: {cal['url']}")
        print(f"Use as: {cal['id']}@nextcloud")
        print("-" * 50)
    
    # Detect Kerio server type and endpoint
    print("\nProbing Kerio server...")
    logger.info(f"Kerio config: URL={kerio_config.url!r}, Username={kerio_config.username!r}")
    kerio_type, kerio_url = detect_server_type(
        kerio_config.url,
        kerio_config.username,
        kerio_config.password
    )
    
    # Create client with detected URL
    kerio_config.url = kerio_url
    kerio = CalDAVClient(kerio_config)
    
    print(f"\nKerio Calendars (detected as {kerio_type}):")
    print("-" * 50)
    for cal in list_calendars(kerio):
        print(f"ID: {cal['id']}")
        print(f"Name: {cal['name']}")
        print(f"URL: {cal['url']}")
        print(f"Use as: {cal['id']}@kerio")
        print("-" * 50) 