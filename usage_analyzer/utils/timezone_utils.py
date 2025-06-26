"""Comprehensive timezone utilities for Claude Monitor."""

import sys
from datetime import datetime, timezone
from typing import Optional, Union, Dict, Any, List
import logging
from functools import lru_cache

# Conditional import for modern Python support
if sys.version_info >= (3, 9):
    from zoneinfo import ZoneInfo, available_timezones
    MODERN_TIMEZONE = True
else:
    import pytz
    MODERN_TIMEZONE = False


class TimezoneHandler:
    """Centralized timezone handling with fallbacks."""
    
    def __init__(self, default_tz: str = "UTC"):
        self.default_tz = default_tz
        self.logger = logging.getLogger(__name__)
        self._validate_default_timezone()
    
    def _validate_default_timezone(self) -> None:
        """Validate default timezone on initialization."""
        if not self.validate_timezone(self.default_tz):
            self.logger.warning(f"Invalid default timezone {self.default_tz}, falling back to UTC")
            self.default_tz = "UTC"
    
    def parse_timestamp(self, timestamp_str: str) -> datetime:
        """Parse timestamp with robust format support.
        
        Supports:
        - ISO format with 'Z' suffix
        - ISO format with timezone offset
        - ISO format without timezone (assumes UTC)
        - Unix timestamps
        """
        if not timestamp_str:
            raise ValueError("Empty timestamp string")
        
        # Try different parsing strategies
        try:
            # Strategy 1: ISO format with 'Z' (UTC)
            if timestamp_str.endswith('Z'):
                return datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            
            # Strategy 2: ISO format with timezone
            elif '+' in timestamp_str or timestamp_str.count('-') > 2:
                return datetime.fromisoformat(timestamp_str)
            
            # Strategy 3: Unix timestamp
            elif timestamp_str.isdigit() or (timestamp_str.startswith('-') and timestamp_str[1:].isdigit()):
                return datetime.fromtimestamp(int(timestamp_str), tz=timezone.utc)
            
            # Strategy 4: ISO format without timezone (assume UTC)
            else:
                dt = datetime.fromisoformat(timestamp_str)
                if dt.tzinfo is None:
                    self.logger.debug(f"Assuming UTC for naive timestamp: {timestamp_str}")
                    return dt.replace(tzinfo=timezone.utc)
                return dt
                
        except Exception as e:
            self.logger.error(f"Failed to parse timestamp '{timestamp_str}': {e}")
            raise ValueError(f"Unable to parse timestamp: {timestamp_str}") from e
    
    def ensure_utc(self, dt: datetime) -> datetime:
        """Ensure datetime is in UTC with proper conversion."""
        if dt.tzinfo is None:
            # Naive datetime - assume UTC
            self.logger.debug(f"Converting naive datetime to UTC: {dt}")
            return dt.replace(tzinfo=timezone.utc)
        elif dt.tzinfo == timezone.utc or (hasattr(dt.tzinfo, 'zone') and dt.tzinfo.zone == 'UTC'):
            # Already UTC
            return dt
        else:
            # Convert to UTC
            self.logger.debug(f"Converting {dt.tzinfo} datetime to UTC")
            return dt.astimezone(timezone.utc)
    
    def convert_to_timezone(self, dt: datetime, tz_name: str) -> datetime:
        """Convert datetime to specified timezone with error handling."""
        if not self.validate_timezone(tz_name):
            self.logger.warning(f"Invalid timezone {tz_name}, using {self.default_tz}")
            tz_name = self.default_tz
        
        # Ensure we have a timezone-aware datetime
        dt_utc = self.ensure_utc(dt)
        
        try:
            tz = self.get_timezone(tz_name)
            if MODERN_TIMEZONE:
                return dt_utc.astimezone(tz)
            else:
                # pytz approach
                return dt_utc.astimezone(tz)
        except Exception as e:
            self.logger.error(f"Failed to convert to timezone {tz_name}: {e}")
            return dt_utc  # Return UTC on failure
    
    @lru_cache(maxsize=32)
    def validate_timezone(self, tz_name: str) -> bool:
        """Validate timezone name with caching."""
        if not tz_name:
            return False
        
        try:
            self.get_timezone(tz_name)
            return True
        except Exception:
            return False
    
    @lru_cache(maxsize=32)
    def get_timezone(self, tz_name: str) -> Union['ZoneInfo', 'pytz.tzinfo.tzinfo']:
        """Get timezone object with modern/legacy support and caching."""
        if MODERN_TIMEZONE:
            try:
                return ZoneInfo(tz_name)
            except Exception as e:
                self.logger.debug(f"Failed to get ZoneInfo for {tz_name}: {e}")
                raise ValueError(f"Invalid timezone: {tz_name}") from e
        else:
            try:
                return pytz.timezone(tz_name)
            except Exception as e:
                self.logger.debug(f"Failed to get pytz timezone for {tz_name}: {e}")
                raise ValueError(f"Invalid timezone: {tz_name}") from e
    
    def get_available_timezones(self) -> List[str]:
        """Get list of available timezone names."""
        if MODERN_TIMEZONE:
            return sorted(available_timezones())
        else:
            return sorted(pytz.all_timezones)
    
    def localize_naive_datetime(self, dt: datetime, tz_name: str) -> datetime:
        """Localize a naive datetime to specified timezone."""
        if dt.tzinfo is not None:
            self.logger.warning("Datetime already has timezone info, converting instead")
            return self.convert_to_timezone(dt, tz_name)
        
        tz = self.get_timezone(tz_name)
        if MODERN_TIMEZONE:
            return dt.replace(tzinfo=tz)
        else:
            # pytz requires localize for naive datetimes
            return tz.localize(dt)
    
    def debug_timezone_info(self, dt: datetime) -> Dict[str, Any]:
        """Comprehensive timezone debugging information."""
        info = {
            'datetime': str(dt),
            'tzinfo': str(dt.tzinfo) if dt.tzinfo else 'None (naive)',
            'is_aware': dt.tzinfo is not None,
            'utc_offset': str(dt.utcoffset()) if dt.tzinfo else 'N/A',
            'dst': str(dt.dst()) if dt.tzinfo else 'N/A',
            'timezone_name': dt.tzinfo.tzname(dt) if dt.tzinfo and hasattr(dt.tzinfo, 'tzname') else 'N/A',
            'iso_format': dt.isoformat(),
            'timestamp': dt.timestamp() if dt.tzinfo else 'N/A (naive)',
        }
        
        if hasattr(dt.tzinfo, 'zone'):
            info['pytz_zone'] = dt.tzinfo.zone
        
        return info


def safe_timezone_conversion(dt: datetime, target_tz: str, fallback_tz: str = "UTC") -> datetime:
    """Convert timezone with fallback strategies.
    
    This is a convenience function for one-off conversions without creating a handler instance.
    """
    handler = TimezoneHandler(default_tz=fallback_tz)
    return handler.convert_to_timezone(dt, target_tz)


def detect_system_timezone() -> Optional[str]:
    """Detect system timezone with fallbacks."""
    import os
    import platform
    
    # Strategy 1: Environment variable
    tz_env = os.environ.get('TZ')
    if tz_env:
        handler = TimezoneHandler()
        if handler.validate_timezone(tz_env):
            return tz_env
    
    # Strategy 2: Platform-specific detection
    system = platform.system()
    
    if system == 'Darwin':  # macOS
        try:
            import subprocess
            result = subprocess.run(['defaults', 'read', '/Library/Preferences/.GlobalPreferences', 
                                   'com.apple.timezone.auto'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                tz = result.stdout.strip()
                handler = TimezoneHandler()
                if handler.validate_timezone(tz):
                    return tz
        except Exception:
            pass
    
    elif system == 'Linux':
        # Try reading /etc/timezone
        try:
            with open('/etc/timezone', 'r') as f:
                tz = f.read().strip()
                handler = TimezoneHandler()
                if handler.validate_timezone(tz):
                    return tz
        except Exception:
            pass
        
        # Try reading /etc/localtime symlink
        try:
            import os
            if os.path.islink('/etc/localtime'):
                tz_path = os.readlink('/etc/localtime')
                # Extract timezone from path like /usr/share/zoneinfo/Europe/Warsaw
                if '/zoneinfo/' in tz_path:
                    tz = tz_path.split('/zoneinfo/')[-1]
                    handler = TimezoneHandler()
                    if handler.validate_timezone(tz):
                        return tz
        except Exception:
            pass
    
    elif system == 'Windows':
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, 
                              r'SYSTEM\CurrentControlSet\Control\TimeZoneInformation') as key:
                tz_win, _ = winreg.QueryValueEx(key, 'TimeZoneKeyName')
                # Windows timezone names need mapping to IANA names
                # This is a simplified approach - full mapping would be more complex
                handler = TimezoneHandler()
                if handler.validate_timezone(tz_win):
                    return tz_win
        except Exception:
            pass
    
    # Unable to detect
    return None