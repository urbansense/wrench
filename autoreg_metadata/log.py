import logging


def setup_logging(level=logging.INFO):
    """Configure package-wide logging"""
    logger = logging.getLogger("autoreg_metadata")
    # Clear any existing handlers
    logger.handlers.clear()

    # Enhanced formatter with file, line number, and function name
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(pathname)s:%(lineno)d - %(funcName)s() - %(message)s'
    )

    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(level)

    # Prevent propagation to avoid duplicate logs
    logger.propagate = False
    return logger


logger = setup_logging()
