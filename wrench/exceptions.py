class WrenchError(Exception):
    """Base exception for wrench."""

    pass


class HarvesterError(WrenchError):
    """Raised when harvesting operations fail."""

    pass


class ClassifierError(WrenchError):
    """Raised when classification operations fail."""

    pass


class CatalogerError(WrenchError):
    """Raised when catalogging operations fail."""

    pass
