import logging
import os


def setup_logging(name=None, level=logging.INFO) -> logging.Logger:
    """
    Set up logging configuration.

    Args:
        name: The logger name (typically __name__ from the calling module)
        level: The logging level to use

    Returns:
        A configured logger instance
    """
    # Only configure the root logger once
    if not logging.getLogger().handlers:
        logging.basicConfig(
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            level=level,
        )

    # Return a logger with the provided name
    return logging.getLogger(name)


# For backward compatibility, maintain a module-level logger
LOG = setup_logging(__name__, level=os.getenv("LOG_LEVEL", "INFO").upper())
