"""
Logging configuration for the API.

This module provides structured logging setup with different levels and formats.
"""

import logging
import logging.config
import sys
from typing import Any, Dict

# Logging configuration
LOGGING_CONFIG: Dict[str, Any] = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
        "detailed": {
            "format": (
                "%(asctime)s [%(levelname)s] %(name)s:%(funcName)s:%(lineno)d: "
                "%(message)s"
            ),
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
        "json": {
            "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
            "format": (
                "%(asctime)s %(name)s %(levelname)s %(funcName)s %(lineno)d %(message)s"
            ),
        },
    },
    "handlers": {
        "console": {
            "level": "INFO",
            "class": "logging.StreamHandler",
            "formatter": "standard",
            "stream": sys.stdout,
        },
        "file": {
            "level": "DEBUG",
            "class": "logging.handlers.RotatingFileHandler",
            "formatter": "detailed",
            "filename": "logs/api.log",
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5,
        },
        "error_file": {
            "level": "ERROR",
            "class": "logging.handlers.RotatingFileHandler",
            "formatter": "detailed",
            "filename": "logs/api_errors.log",
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5,
        },
    },
    "loggers": {
        "api": {
            "level": "DEBUG",
            "handlers": ["console", "file", "error_file"],
            "propagate": False,
        },
        "fastapi": {
            "level": "INFO",
            "handlers": ["console", "file"],
            "propagate": False,
        },
        "uvicorn": {
            "level": "INFO",
            "handlers": ["console"],
            "propagate": False,
        },
    },
    "root": {
        "level": "INFO",
        "handlers": ["console"],
    },
}


def setup_logging(log_level: str = "INFO", enable_json: bool = False) -> None:
    """
    Setup logging configuration.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        enable_json: Whether to use JSON formatting
    """
    import os

    # Create logs directory if it doesn't exist
    os.makedirs("logs", exist_ok=True)

    # Copy config and modify if needed
    config = LOGGING_CONFIG.copy()

    if enable_json:
        # Switch to JSON formatter
        config["handlers"]["console"]["formatter"] = "json"
        config["handlers"]["file"]["formatter"] = "json"

    # Set log level
    config["loggers"]["api"]["level"] = log_level.upper()

    # Apply configuration
    logging.config.dictConfig(config)


def get_api_logger(name: str = "api") -> logging.Logger:
    """
    Get a configured logger for API components.

    Args:
        name: Logger name

    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)


class StructuredLogger:
    """Wrapper for structured logging with context."""

    def __init__(self, name: str = "api"):
        """
        Initialize structured logger.

        Args:
            name: Logger name
        """
        self.logger = get_api_logger(name)
        self.context = {}

    def set_context(self, **kwargs) -> None:
        """
        Set context for all subsequent log messages.

        Args:
            **kwargs: Context key-value pairs
        """
        self.context.update(kwargs)

    def clear_context(self) -> None:
        """Clear logging context."""
        self.context.clear()

    def _log_with_context(self, level: str, message: str, **extra) -> None:
        """
        Log message with context.

        Args:
            level: Log level
            message: Log message
            **extra: Additional context
        """
        # Merge context with extra
        log_context = {**self.context, **extra}

        # Log with context
        getattr(self.logger, level)(message, extra=log_context)

    def debug(self, message: str, **extra) -> None:
        """Log debug message."""
        self._log_with_context("debug", message, **extra)

    def info(self, message: str, **extra) -> None:
        """Log info message."""
        self._log_with_context("info", message, **extra)

    def warning(self, message: str, **extra) -> None:
        """Log warning message."""
        self._log_with_context("warning", message, **extra)

    def error(self, message: str, **extra) -> None:
        """Log error message."""
        self._log_with_context("error", message, **extra)

    def critical(self, message: str, **extra) -> None:
        """Log critical message."""
        self._log_with_context("critical", message, **extra)


# Global structured logger instance
api_logger = StructuredLogger("api")


def log_performance(func_name: str, duration_ms: float, **context) -> None:
    """
    Log performance metrics.

    Args:
        func_name: Function name
        duration_ms: Duration in milliseconds
        **context: Additional context
    """
    api_logger.info(
        f"Performance: {func_name}",
        duration_ms=duration_ms,
        function=func_name,
        **context,
    )


def log_business_event(event_type: str, event_data: Dict[str, Any]) -> None:
    """
    Log business events.

    Args:
        event_type: Type of business event
        event_data: Event data
    """
    api_logger.info(
        f"Business event: {event_type}", event_type=event_type, event_data=event_data
    )


def log_security_event(event_type: str, client_ip: str, **context) -> None:
    """
    Log security events.

    Args:
        event_type: Type of security event
        client_ip: Client IP address
        **context: Additional context
    """
    api_logger.warning(
        f"Security event: {event_type}",
        event_type=event_type,
        client_ip=client_ip,
        **context,
    )
