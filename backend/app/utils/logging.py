"""Logging configuration with file and console output."""

import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional


def setup_logging(level: str = "INFO", log_dir: Optional[str] = None) -> None:
    """
    Configure application logging with both console and file output.

    Args:
        level: Log level string (DEBUG, INFO, WARNING, ERROR)
        log_dir: Directory for log files (defaults to ./logs)
    """
    log_level = getattr(logging, level.upper(), logging.INFO)

    # Determine log directory
    if log_dir is None:
        # Use /app/logs in Docker, or ./logs locally
        log_dir = os.environ.get("LOG_DIR", "logs")

    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    # Log format
    log_format = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    # Create formatters
    formatter = logging.Formatter(log_format, datefmt=date_format)

    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Clear existing handlers
    root_logger.handlers.clear()

    # Console handler (stdout)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # Main application log file (rotating, 10MB max, keep 5 backups)
    app_log_file = log_path / "app.log"
    app_file_handler = RotatingFileHandler(
        app_log_file,
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=5,
        encoding="utf-8",
    )
    app_file_handler.setLevel(log_level)
    app_file_handler.setFormatter(formatter)
    root_logger.addHandler(app_file_handler)

    # Error log file (errors and above only)
    error_log_file = log_path / "error.log"
    error_file_handler = RotatingFileHandler(
        error_log_file,
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=5,
        encoding="utf-8",
    )
    error_file_handler.setLevel(logging.ERROR)
    error_file_handler.setFormatter(formatter)
    root_logger.addHandler(error_file_handler)

    # Report generation specific log
    report_log_file = log_path / "reports.log"
    report_handler = RotatingFileHandler(
        report_log_file,
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=5,
        encoding="utf-8",
    )
    report_handler.setLevel(log_level)
    report_handler.setFormatter(formatter)

    # Attach to report-related loggers
    report_logger = logging.getLogger("app.services.report_generator")
    report_logger.addHandler(report_handler)

    llm_logger = logging.getLogger("app.services.llm_service")
    llm_logger.addHandler(report_handler)

    # Reduce noise from third-party libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    logging.getLogger("watchfiles").setLevel(logging.WARNING)

    # Log startup message
    root_logger.info(f"Logging initialized - Level: {level}, Log directory: {log_path.absolute()}")


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for the given name."""
    return logging.getLogger(name)
