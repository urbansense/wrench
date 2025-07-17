import re
from typing import Optional


def sanitize_ckan_name(
    name: str, max_length: int = 100, fallback_prefix: str = "unnamed"
) -> str:
    """
    Sanitize a name to be CKAN-compliant.

    CKAN names must be purely lowercase alphanumeric (ascii) characters
    and these symbols: -_

    Args:
        name: The input name to sanitize
        max_length: Maximum allowed length for the name (default 100)
        fallback_prefix: Prefix to use if name becomes empty after sanitization

    Returns:
        A CKAN-compliant name string

    Examples:
        >>> sanitize_ckan_name("Air Quality Sensors")
        'air_quality_sensors'
        >>> sanitize_ckan_name("Temperature & Humidity")
        'temperature_humidity'
        >>> sanitize_ckan_name("測試 Sensors (Group #1)")
        'sensors_group_1'
        >>> sanitize_ckan_name("!!!@@@")
        'unnamed_item'
    """
    if not name or not isinstance(name, str):
        return f"{fallback_prefix}_item"

    # Convert to lowercase and strip whitespace
    sanitized = name.lower().strip()

    # Replace common separators and punctuation with underscores
    sanitized = re.sub(r"[&+/\\|<>()[\]{}]", "_", sanitized)
    sanitized = re.sub(r'[.,;:!?@#$%^*=~`"\']', "_", sanitized)

    # Replace spaces and multiple whitespace with underscores
    sanitized = re.sub(r"\s+", "_", sanitized)

    # Remove any character that is not alphanumeric, hyphen, or underscore
    sanitized = re.sub(r"[^a-z0-9_-]", "", sanitized)

    # Replace multiple consecutive underscores/hyphens with single underscore
    sanitized = re.sub(r"[_-]+", "_", sanitized)

    # Remove leading/trailing underscores and hyphens
    sanitized = sanitized.strip("_-")

    # If empty after sanitization, use fallback
    if not sanitized:
        return f"{fallback_prefix}_item"

    # Ensure it doesn't start with a number (some systems don't like this)
    if sanitized[0].isdigit():
        sanitized = f"{fallback_prefix}_{sanitized}"

    # Truncate to max length
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length].rstrip("_-")

    return sanitized


def validate_ckan_name(name: str) -> tuple[bool, Optional[str]]:
    """
    Validate if a name is CKAN-compliant.

    Args:
        name: The name to validate

    Returns:
        Tuple of (is_valid, error_message)

    Examples:
        >>> validate_ckan_name("air_quality_sensors")
        (True, None)
        >>> validate_ckan_name("Air Quality!")
        (False, "Contains invalid characters: uppercase letters, special characters")
    """
    if not name or not isinstance(name, str):
        return False, "Name is empty or not a string"

    # Check for valid characters only
    if not re.match(r"^[a-z0-9_-]+$", name):
        invalid_chars = set(char for char in name if not re.match(r"[a-z0-9_-]", char))
        return False, f"Contains invalid characters: {', '.join(sorted(invalid_chars))}"

    # Check if starts with number
    if name[0].isdigit():
        return False, "Cannot start with a number"

    # Check for leading/trailing separators
    if name.startswith(("_", "-")) or name.endswith(("_", "-")):
        return False, "Cannot start or end with underscore or hyphen"

    return True, None
