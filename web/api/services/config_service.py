"""
Configuration service for managing user settings.

This module provides business logic for configuration management.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from ..exceptions import ValidationException
from ..models.schemas import ConfigurationSettings, ConfigurationUpdate


class ConfigService:
    """Service for configuration management."""

    def __init__(self):
        """Initialize configuration service."""
        self.config_file = Path.home() / ".claude_monitor" / "web_config.json"
        self.config_file.parent.mkdir(exist_ok=True)
        self._defaults_applied = False

    async def get_configuration(self) -> ConfigurationSettings:
        """
        Get current configuration.

        Returns:
            Current configuration settings
        """
        config_data = self._load_config()

        # Apply defaults if needed
        if not config_data:
            config_data = self._get_default_config()
            self._defaults_applied = True

        return ConfigurationSettings(**config_data)

    async def update_configuration(
        self, config_update: ConfigurationUpdate
    ) -> ConfigurationSettings:
        """
        Update configuration with provided values.

        Args:
            config_update: Configuration update data

        Returns:
            Updated configuration
        """
        # Load current config
        current_config = self._load_config()
        if not current_config:
            current_config = self._get_default_config()

        # Apply updates
        update_data = config_update.model_dump(exclude_none=True)
        current_config.update(update_data)

        # Add metadata
        current_config["last_updated"] = datetime.now().isoformat()

        # Save updated config
        self._save_config(current_config)

        return ConfigurationSettings(**current_config)

    async def reset_to_defaults(self) -> ConfigurationSettings:
        """
        Reset configuration to default values.

        Returns:
            Default configuration
        """
        default_config = self._get_default_config()
        default_config["last_updated"] = datetime.now().isoformat()

        self._save_config(default_config)

        return ConfigurationSettings(**default_config)

    async def validate_configuration_update(
        self, config_update: ConfigurationUpdate
    ) -> None:
        """
        Validate configuration update.

        Args:
            config_update: Configuration update to validate

        Raises:
            ValidationException: If validation fails
        """
        update_data = config_update.model_dump(exclude_none=True)

        # Validate plan and custom limit relationship
        if "plan" in update_data and update_data["plan"] == "custom_max":
            if "custom_token_limit" not in update_data:
                # Check if current config has custom limit
                current_config = self._load_config()
                if not current_config or not current_config.get("custom_token_limit"):
                    raise ValidationException(
                        "custom_token_limit is required when plan is 'custom_max'"
                    )

        # Validate timezone format
        if "timezone" in update_data:
            timezone_str = update_data["timezone"]
            try:
                import pytz

                pytz.timezone(timezone_str)
            except Exception:
                raise ValidationException(f"Invalid timezone: {timezone_str}")

        # Validate refresh interval
        if "refresh_interval" in update_data:
            interval = update_data["refresh_interval"]
            if not 1 <= interval <= 300:
                raise ValidationException(
                    "refresh_interval must be between 1 and 300 seconds"
                )

        # Validate custom token limit
        if "custom_token_limit" in update_data:
            limit = update_data["custom_token_limit"]
            if limit is not None and not 1000 <= limit <= 1000000:
                raise ValidationException(
                    "custom_token_limit must be between 1,000 and 1,000,000"
                )

    def has_defaults_applied(self) -> bool:
        """
        Check if defaults were applied in last get operation.

        Returns:
            True if defaults were applied
        """
        return self._defaults_applied

    def _load_config(self) -> Optional[Dict[str, Any]]:
        """
        Load configuration from file.

        Returns:
            Configuration data or None if file doesn't exist
        """
        try:
            if self.config_file.exists():
                with open(self.config_file, "r") as f:
                    return json.load(f)
            return None
        except Exception:
            return None

    def _save_config(self, config_data: Dict[str, Any]) -> None:
        """
        Save configuration to file.

        Args:
            config_data: Configuration data to save
        """
        try:
            with open(self.config_file, "w") as f:
                json.dump(config_data, f, indent=2)
        except Exception as e:
            raise Exception(f"Failed to save configuration: {str(e)}")

    def _get_default_config(self) -> Dict[str, Any]:
        """
        Get default configuration values.

        Returns:
            Default configuration
        """
        return {
            "plan": "pro",
            "timezone": "UTC",
            "theme": "auto",
            "notifications_enabled": True,
            "refresh_interval": 30,
            "custom_token_limit": None,
            "created_at": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat(),
        }
