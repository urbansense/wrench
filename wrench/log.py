import logging


def setup_logging(level=logging.DEBUG):
    """Configure package-wide logging."""
    logger = logging.getLogger("wrench")
    # Clear any existing handlers
    logger.handlers.clear()

    # Enhanced formatter with file, line number, and function name
    handler = logging.StreamHandler()
    fileHandler = logging.FileHandler("wrench.log")
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(level)
    logger.addHandler(fileHandler)

    # Prevent propagation to avoid duplicate logs
    logger.propagate = False
    return logger


logger = setup_logging()
