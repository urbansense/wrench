from typing import Any

import pytest
from pydantic import BaseModel

from wrench.pipeline.component import Component, ComponentMeta, DataModel
from wrench.pipeline.exceptions import PipelineDefinitionError


class TestDataModel(DataModel):
    value: str


class ValidComponent(Component):
    async def run(self) -> TestDataModel:
        return TestDataModel(value="test")


class ComponentWithParams(Component):
    async def run(self, param1: str, param2: int = 0) -> TestDataModel:
        return TestDataModel(value=f"{param1}-{param2}")


def test_valid_component():
    """Test that a valid component can be created without errors."""
    component = ValidComponent()
    assert isinstance(component, Component)
    assert hasattr(component, "component_inputs")
    assert hasattr(component, "component_outputs")
    # Check the component_outputs is filled correctly
    assert "value" in component.component_outputs
    assert component.component_outputs["value"]["annotation"] is str


def test_componentmeta_validation():
    """Test ComponentMeta validation logic directly."""
    # Create a dict with a run method that has an invalid return type
    attrs = {
        "run": lambda self: None,
        "__annotations__": {"run": Any},  # Invalid return type (not annotated)
    }

    # Test non-annotated return type
    with pytest.raises(PipelineDefinitionError) as excinfo:
        ComponentMeta.__new__(
            ComponentMeta, "TestComponentNoAnnotation", (Component,), attrs
        )
    assert "The run method return type must be annotated in" in str(excinfo.value)

    # Test non-DataModel return type
    attrs["__annotations__"]["run"] = (
        BaseModel  # Invalid return (not a DataModel subclass)
    )
    with pytest.raises(PipelineDefinitionError) as excinfo:
        ComponentMeta.__new__(
            ComponentMeta, "TestComponentInvalidReturn", (Component,), attrs
        )
    assert "The run method return type must be annotated in" in str(excinfo.value)


def test_component_with_parameters():
    """Test that component parameters are correctly extracted."""
    component = ComponentWithParams()
    assert "param1" in component.component_inputs
    assert "param2" in component.component_inputs
    assert component.component_inputs["param1"]["has_default"] is False
    assert component.component_inputs["param2"]["has_default"] is True
    assert component.component_inputs["param1"]["annotation"] is str
    assert component.component_inputs["param2"]["annotation"] is int


@pytest.mark.asyncio
async def test_component_execution():
    """Test that component can be executed and returns expected result."""
    component = ComponentWithParams()
    result = await component.run(param1="hello", param2=42)
    assert isinstance(result, TestDataModel)
    assert result.value == "hello-42"
