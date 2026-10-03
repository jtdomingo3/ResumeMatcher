"""
Logging configuration with integrated Secret Redaction Filter.
Ensures zero sensitive token exposure across all standard and library loggers.
"""

import logging
import sys
from backend.app.core.config import settings
from backend.app.core.redaction import SecretRedactionFilter


def setup_logging():
    """
    Configures root logger with safe formatting and the SecretRedactionFilter.
    """
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Remove existing handlers to avoid duplicates
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)

    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    console_handler.setFormatter(formatter)

    # Attach secret redaction filter
    console_handler.addFilter(SecretRedactionFilter())
    root_logger.addHandler(console_handler)

    # Also silence noisy third-party loggers if in INFO mode
    logging.getLogger("chromadb").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

    logging.info("Logging configured with SecretRedactionFilter enabled.")
