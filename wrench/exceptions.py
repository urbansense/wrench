class AutoregError(Exception):
    """Base exception for autoreg_metadata"""
    pass


class HarvesterError(AutoregError):
    """Raised when harvesting operations fail"""
    pass


class ClassifierError(AutoregError):
    """Raised when classification operations fail"""
    pass


class CataloggerError(AutoregError):
    """Raised when catalogging operations fail"""
    pass
