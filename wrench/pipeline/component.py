# Copyright The Neo4j Authors
# SPDX-License-Identifier: Apache-2.0

# This code has been copied from:
# https://github.com/neo4j/neo4j-graphrag-python/

# Some modifications have been made to the original code to better suit the
# needs of this project.

import inspect
from abc import ABC, ABCMeta, abstractmethod
from typing import Any

from pydantic import BaseModel, PrivateAttr
from typing_extensions import get_type_hints

from .exceptions import PipelineDefinitionError


class DataModel(BaseModel):
    """Input or Output data model for Components."""

    stop_pipeline: bool = False
    _performance_metrics: Any = PrivateAttr(default=None)


class ComponentMeta(ABCMeta):
    """Metaclass that extracts component interface from method signatures."""

    def __new__(cls, name: str, bases: tuple[type, ...], attrs: dict[str, Any]) -> type:
        run_method = attrs.get("run")
        if run_method is not None:
            # extract input and outputs from the run method signature
            sign = inspect.signature(run_method)
            attrs["component_inputs"] = {
                param.name: {
                    "has_default": param.default != inspect.Parameter.empty,
                    "annotation": param.annotation,
                }
                for param in sign.parameters.values()
                if param.name not in ("self", "kwargs")
            }

            # extract returned fields from the run method return type hint
            return_model = get_type_hints(run_method).get("return")  # type: ignore[arg-type]
            if return_model is None:
                raise PipelineDefinitionError(
                    f"The run method return type must be annotated in {name}"
                )

            # type hint must be subclass of DataModel
            if not issubclass(return_model, DataModel):
                raise PipelineDefinitionError(
                    f"The run method must return a subclass of DataModel in {name}"
                )

            attrs["component_outputs"] = {
                f: {
                    "has_default": field.is_required(),
                    "annotation": field.annotation,
                }
                for f, field in return_model.model_fields.items()
            }

        return type.__new__(cls, name, bases, attrs)


class Component(ABC, metaclass=ComponentMeta):
    """Interface that needs to be implemented by all components.

    Subclass this for stateless components whose ``run()`` method does not
    need to remember anything between pipeline runs.

    If your component needs to persist data across runs (e.g. to detect
    changes or skip unchanged items), subclass :class:`StatefulComponent`
    instead.

    Example — stateless component::

        class MyCataloger(Component):
            async def run(self, metadata: CommonMetadata) -> CatalogerStatus:
                self._client.register(metadata)
                return CatalogerStatus(success=True)
    """

    # these variables are filled by the metaclass
    # added here for the type checker
    # DO NOT CHANGE
    component_inputs: dict[str, dict[str, str | bool | type]]
    component_outputs: dict[str, dict[str, str | bool | type]]

    @abstractmethod
    async def run(self, **kwargs: Any) -> DataModel:
        pass


class StatefulComponent(Component):
    """Base class for components that persist state between pipeline runs.

    Subclass this instead of :class:`Component` when your ``run()`` method
    needs to remember data from one run to the next — for example, to detect
    changes or skip items that haven't changed.

    The pipeline automatically loads the component's previous state into
    ``self.state`` before each ``run()`` call, and saves whatever is in
    ``self.state`` afterwards.  On the very first run ``self.state`` is an
    empty dict.

    Example — stateful component::

        class MyHarvester(StatefulComponent):
            async def run(self) -> Items:
                previous = self.state.get("previous_devices", [])
                current  = self._source.fetch()
                ops      = compute_diff(previous, current)

                self.state["previous_devices"] = current   # persisted for next run
                return Items(devices=current, operations=ops)

    Stateless components should subclass :class:`Component` directly and
    simply omit any ``self.state`` access.
    """

    @property
    def state(self) -> dict[str, Any]:
        """State persisted from the previous pipeline run.

        Empty dict on the first run.  Mutate this dict inside ``run()`` to
        persist values for the next run.
        """
        if not hasattr(self, "_state"):
            self._state: dict[str, Any] = {}
        return self._state

    @state.setter
    def state(self, value: dict[str, Any]) -> None:
        self._state = value
