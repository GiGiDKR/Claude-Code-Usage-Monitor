"""
Configuration router for user settings and preferences.

This module provides endpoints for managing user configuration.
"""

from typing import Any, Dict

from fastapi import APIRouter, Depends

from ..exceptions import ConfigurationException, ValidationException
from ..models.schemas import APIResponse, ConfigurationUpdate
from ..services.config_service import ConfigService

router = APIRouter()


def get_config_service() -> ConfigService:
    """Dependency to get config service instance."""
    return ConfigService()


@router.get("/config", response_model=APIResponse, summary="Get Configuration")
async def get_configuration(
    config_service: ConfigService = Depends(get_config_service),
) -> APIResponse:
    """
    Get current user configuration settings.

    Returns all user preferences including:
    - Claude plan selection
    - Timezone settings
    - Theme preferences
    - Notification settings
    - Refresh intervals
    - Custom limits

    Args:
        config_service: Configuration service dependency

    Returns:
        APIResponse with current configuration
    """
    try:
        config_data = await config_service.get_configuration()

        return APIResponse(
            success=True,
            data=config_data,
            metadata={
                "config_source": "user_preferences",
                "default_applied": config_service.has_defaults_applied(),
            },
        )

    except Exception as e:
        raise ConfigurationException(f"Failed to get configuration: {str(e)}")


@router.post("/config", response_model=APIResponse, summary="Update Configuration")
async def update_configuration(
    config_update: ConfigurationUpdate,
    config_service: ConfigService = Depends(get_config_service),
) -> APIResponse:
    """
    Update user configuration settings.

    Allows partial updates - only specified fields will be changed.
    Validates all provided values before applying changes.

    Args:
        config_update: Configuration update data
        config_service: Configuration service dependency

    Returns:
        APIResponse with updated configuration
    """
    try:
        # Validate update data
        await config_service.validate_configuration_update(config_update)

        # Apply updates
        updated_config = await config_service.update_configuration(config_update)

        return APIResponse(
            success=True,
            data=updated_config,
            metadata={
                "updated_fields": [
                    field
                    for field, value in config_update.model_dump().items()
                    if value is not None
                ],
                "update_timestamp": updated_config.get("last_updated"),
            },
        )

    except ValidationException:
        raise
    except Exception as e:
        raise ConfigurationException(f"Failed to update configuration: {str(e)}")


@router.post("/config/reset", response_model=APIResponse, summary="Reset Configuration")
async def reset_configuration(
    config_service: ConfigService = Depends(get_config_service),
) -> APIResponse:
    """
    Reset configuration to default values.

    This will restore all settings to their default values.
    This action cannot be undone.

    Args:
        config_service: Configuration service dependency

    Returns:
        APIResponse with reset configuration
    """
    try:
        default_config = await config_service.reset_to_defaults()

        return APIResponse(
            success=True,
            data=default_config,
            metadata={
                "action": "reset_to_defaults",
                "previous_backup": "not_implemented",  # TODO: Implement backup
            },
        )

    except Exception as e:
        raise ConfigurationException(f"Failed to reset configuration: {str(e)}")


@router.get("/config/schema", summary="Get Configuration Schema")
async def get_configuration_schema() -> Dict[str, Any]:
    """
    Get the configuration schema with validation rules.

    Returns the complete schema for configuration fields including:
    - Field types
    - Validation rules
    - Default values
    - Allowed values/enums

    Returns:
        Configuration schema information
    """
    return {
        "fields": {
            "plan": {
                "type": "enum",
                "allowed_values": ["pro", "max5", "max20", "custom_max"],
                "default": "pro",
                "description": "Claude subscription plan type",
            },
            "timezone": {
                "type": "string",
                "pattern": r"^[A-Za-z]+/[A-Za-z_]+$",
                "default": "UTC",
                "description": "Timezone for date/time display",
                "examples": ["UTC", "America/New_York", "Europe/Paris"],
            },
            "theme": {
                "type": "enum",
                "allowed_values": ["light", "dark", "auto"],
                "default": "auto",
                "description": "UI theme preference",
            },
            "notifications_enabled": {
                "type": "boolean",
                "default": True,
                "description": "Enable/disable system notifications",
            },
            "refresh_interval": {
                "type": "integer",
                "minimum": 1,
                "maximum": 300,
                "default": 30,
                "description": "Data refresh interval in seconds",
            },
            "custom_token_limit": {
                "type": "integer",
                "minimum": 1000,
                "maximum": 1000000,
                "default": None,
                "description": "Custom token limit (optional)",
            },
        },
        "validation_rules": {
            "custom_token_limit": "Required when plan is 'custom_max'",
            "timezone": "Must be a valid timezone identifier",
            "refresh_interval": "Minimum 1 second, maximum 5 minutes",
        },
    }
