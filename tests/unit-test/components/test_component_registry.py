import pytest

from wrench.components.registry import ComponentRegistry


def test_component_registry_register():
    """Test registering components with the registry."""
    # Mock component class
    mock_component_class = object()

    # Register component
    ComponentRegistry.register("harvester", "mock", mock_component_class)

    # Verify it was registered
    assert ComponentRegistry.get("harvester", "mock") == mock_component_class


def test_component_registry_unknown_type():
    """Test handling of unknown component types."""
    with pytest.raises(ValueError, match="Unknown component type"):
        ComponentRegistry.register("unknown_type", "test", object())

    with pytest.raises(ValueError, match="Unknown component type"):
        ComponentRegistry.get("unknown_type", "test")


def test_component_registry_unknown_name():
    """Test handling of unknown component names."""
    with pytest.raises(ValueError, match="Unknown harvester 'nonexistent'"):
        ComponentRegistry.get("harvester", "nonexistent")
