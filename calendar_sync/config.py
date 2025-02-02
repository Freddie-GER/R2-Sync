"""Configuration management for the calendar sync tool."""

import json
import logging
import os
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional

from dotenv import load_dotenv

logger = logging.getLogger(__name__)


class SyncMode(Enum):
    """Synchronization mode for calendar pairs."""
    TWO_WAY = "two_way"
    ONE_WAY = "one_way"


@dataclass
class CalendarPair:
    """Configuration for a pair of calendars to sync."""
    source_calendar: str
    target_calendar: str
    sync_mode: SyncMode
    privacy: bool = False

    @classmethod
    def from_string(cls, pair_string: str) -> "CalendarPair":
        """Create a CalendarPair from a configuration string."""
        parts = pair_string.split(":")
        if len(parts) < 3:
            raise ValueError(
                "Calendar pair must be in format: "
                "source:target:mode[:privacy]"
            )
        
        source, target, mode = parts[:3]
        privacy = parts[3].lower() == "true" if len(parts) > 3 else False
        
        try:
            sync_mode = SyncMode(mode.lower())
        except ValueError:
            raise ValueError(f"Invalid sync mode: {mode}")
        
        if privacy and sync_mode == SyncMode.TWO_WAY:
            raise ValueError("Privacy mode is only valid for one-way sync")
        
        return cls(source, target, sync_mode, privacy)


@dataclass
class ServerConfig:
    """Configuration for a CalDAV server."""
    url: str
    username: str
    password: str


@dataclass
class Config:
    """Main configuration container."""
    nextcloud: ServerConfig
    kerio: ServerConfig
    calendar_pairs: List[CalendarPair]
    sync_interval_minutes: int
    log_level: str
    privacy_event_title: str
    privacy_event_prefix: str

    @classmethod
    def load(cls) -> "Config":
        """Load configuration from environment variables."""
        def get_env(key: str, required: bool = True) -> Optional[str]:
            value = os.getenv(key)
            logger.debug(f"Config.load() - Loading {key}: {value}")
            if required and not value:
                raise ValueError(f"Missing required environment variable: {key}")
            return value

        # Load server configurations
        nextcloud = ServerConfig(
            url=get_env("NEXTCLOUD_URL"),
            username=get_env("NEXTCLOUD_USERNAME"),
            password=get_env("NEXTCLOUD_PASSWORD")
        )

        kerio = ServerConfig(
            url=get_env("KERIO_URL"),
            username=get_env("KERIO_USERNAME"),
            password=get_env("KERIO_PASSWORD")
        )

        # Load calendar pairs
        pairs_str = get_env("CALENDAR_PAIRS", required=True)
        try:
            pairs_list = json.loads(pairs_str)
            calendar_pairs = [CalendarPair.from_string(pair) for pair in pairs_list]
        except json.JSONDecodeError as e:
            raise ValueError(f"CALENDAR_PAIRS must be a valid JSON array: {e}")
        except Exception as e:
            raise ValueError(f"Failed to parse calendar pairs: {e}")

        return cls(
            nextcloud=nextcloud,
            kerio=kerio,
            calendar_pairs=calendar_pairs,
            sync_interval_minutes=int(get_env("SYNC_INTERVAL_MINUTES", False) or "30"),
            log_level=get_env("LOG_LEVEL", False) or "INFO",
            privacy_event_title=get_env("PRIVACY_EVENT_TITLE", False) or "Busy",
            privacy_event_prefix=get_env("PRIVACY_EVENT_PREFIX", False) or "PRIVACY-SYNC-"
        ) 