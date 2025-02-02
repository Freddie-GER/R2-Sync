"""Main entry point for the calendar sync tool."""

import argparse
import logging
import os
from pathlib import Path
import sys
import time
from typing import NoReturn

from dotenv import dotenv_values

from .config import Config, ServerConfig
from .discovery import discover_calendars
from .sync_manager import SyncManager

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,  # Set to DEBUG for more detailed logging
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('calendar_sync.log')
    ]
)

logger = logging.getLogger(__name__)


def find_dotenv() -> str:
    """Find the .env file by walking up the directory tree."""
    current_dir = Path.cwd()
    logger.debug(f"Looking for .env file starting from: {current_dir}")
    
    while current_dir != current_dir.parent:
        env_file = current_dir / '.env'
        env_example = current_dir / '.env.example'
        
        logger.debug(f"Checking directory: {current_dir}")
        logger.debug(f"  .env exists: {env_file.exists()}")
        logger.debug(f"  .env.example exists: {env_example.exists()}")
        
        if env_file.exists():
            logger.info(f"Found .env file at: {env_file}")
            return str(env_file)
        current_dir = current_dir.parent
    
    logger.warning("No .env file found, falling back to .env in current directory")
    return '.env'


def main() -> NoReturn:
    """Main entry point for the calendar sync tool."""
    parser = argparse.ArgumentParser(description='Calendar Sync Tool')
    parser.add_argument(
        '--discover',
        action='store_true',
        help='Discover available calendars on both servers'
    )
    args = parser.parse_args()

    try:
        # Load environment variables
        env_path = find_dotenv()
        logger.debug(f"Loading environment variables from: {env_path}")
        
        # Load environment variables directly
        env_values = dotenv_values(env_path)
        logger.debug("Environment variables found:")
        for key, value in env_values.items():
            logger.debug(f"  {key}: {value}")
            os.environ[key] = value
        
        # Load configuration
        config = Config.load()
        logging.getLogger().setLevel(config.log_level)
        
        if args.discover:
            # For discovery, we only need server configs
            logger.info("Starting calendar discovery...")
            discover_calendars(config.nextcloud, config.kerio)
            sys.exit(0)
        
        # Create sync manager for sync mode
        sync_manager = SyncManager(config)
        logger.info("Calendar sync tool started")
        
        while True:
            try:
                sync_manager.sync_calendars()
                
                # Wait for next sync interval
                logger.info(f"Waiting {config.sync_interval_minutes} minutes until next sync")
                time.sleep(config.sync_interval_minutes * 60)
            except KeyboardInterrupt:
                logger.info("Received shutdown signal")
                break
            except Exception as e:
                logger.error(f"Sync failed: {str(e)}")
                logger.info("Retrying in 5 minutes")
                time.sleep(300)
    except Exception as e:
        logger.error(f"Failed to start sync tool: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main() 