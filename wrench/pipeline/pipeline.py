import asyncio
import time
import uuid
from typing import Any, Optional

from wrench.log import logger
from wrench.pipeline.run_tracker import PipelineRunStatus, PipelineRunTracker
from wrench.pipeline.state_manager import PipelineStateManager

from .component import Component
from .exceptions import (
    ComponentNotFoundError,
    PipelineDefinitionError,
    PipelineError,
    PipelineStatusUpdateError,
    ValidationError,
)
from .pipeline_graph import PipelineEdge, PipelineGraph, PipelineNode, PipelineResult
from .stores import InMemoryStore, ResultStore
from .types import (
    PipelineDefinition,
    RunResult,
    RunStatus,
)


class TaskNode(PipelineNode):
    """Node representing a runnable component in the pipeline graph."""

    def __init__(self, name: str, component: Component):
        """
        Initializes a node component in the pipeline graph.

        Args:
            name (str): Name of the node.
            component (Component): Component to be contained in the node.
        """
        super().__init__(name)
        self.component = component
        self.logger = logger.getChild(self.__class__.__name__)

    async def run(self, **inputs: Any) -> RunResult:
        """Execute the component with the given inputs."""
        try:
            result = await self.component.run(**inputs)
            if result.stop_pipeline:
                return RunResult(status=RunStatus.STOP_PIPELINE, result=result)
            return RunResult(status=RunStatus.DONE, result=result)
        except Exception as e:
            self.logger.exception(f"Error executing component {self.name}: {str(e)}")
            return RunResult(status=RunStatus.FAILED, error=e)


class Pipeline(PipelineGraph[TaskNode, PipelineEdge]):
    """
    Pipeline implementation with component validation and execution.

    Features:
    - Component graph with validation
    - Type validation between connected components
    - Status tracking
    - Result storage
    """

    def __init__(self, store: Optional[ResultStore] = None):
        """
        Initializes a Pipeline with given store.

        Args:
            store (Optional[ResultStore]) : Store to be used to store pipeline results.
        """
        super().__init__()
        self.store = store or InMemoryStore()  # default store
        self.run_tracker = PipelineRunTracker(self.store)
        self.state_manager = PipelineStateManager(self.store)
        self.is_validated = False
        self.param_mapping: dict[str, dict[str, dict[str, str]]] = {}
        self.missing_inputs: dict[str, list[str]] = {}

        self.logger = logger.getChild(self.__class__.__name__)

    def add_component(self, name: str, component: Component) -> None:
        """Add a component to the pipeline."""
        if not isinstance(component, Component):
            raise TypeError(
                f"Component must be an instance of Component, got {type(component)}"
            )

        node = TaskNode(name, component)
        self.add_node(node)
        self.is_validated = False

    def set_component(self, name: str, component: Component) -> None:
        """Replace an existing component with a new one."""
        if not isinstance(component, Component):
            raise TypeError(
                f"Component must be an instance of Component, got {type(component)}"
            )

        node = TaskNode(name, component)
        self.set_node(node)
        self.is_validated = False

    def connect(
        self,
        start_component: str,
        end_component: str,
        input_config: dict[str, str] | None = None,
    ) -> None:
        """
        Connect components in the pipeline.

        Args:
            start_component (str): Name of the source component
            end_component (str): Name of the target component
            input_config (dict[str,str] | None): Mapping of target inputs
                to source outputs
        """
        if start_component not in self._nodes:
            raise ComponentNotFoundError(f"Component '{start_component}' not found")
        if end_component not in self._nodes:
            raise ComponentNotFoundError(f"Component '{end_component}' not found")

        edge = PipelineEdge(
            start_component, end_component, {"input_config": input_config or {}}
        )

        try:
            self.add_edge(edge)
        except ValueError as e:
            raise PipelineDefinitionError(str(e))

        self.is_validated = False

    @classmethod
    def from_definition(
        cls, definition: PipelineDefinition, store: ResultStore | None = None
    ) -> "Pipeline":
        """Create a pipeline from a PipelineDefinition."""
        pipeline = cls(store=store)

        # Add all components
        for comp_def in definition.components:
            pipeline.add_component(comp_def.name, comp_def.component)

        # Add all connections
        for conn in definition.connections:
            pipeline.connect(conn.start, conn.end, conn.input_config)

        return pipeline

    def validate(self) -> None:
        """
        Validate the entire pipeline.

        Checks:
        - No cycles in the graph
        - All required inputs are provided
        - Input and output types are compatible
        """
        if self.is_validated:
            return

        # Check for cycles
        if self.is_cyclic():
            raise PipelineDefinitionError("Pipeline contains cycles")

        # Validate each component's connections
        for node in self._nodes.values():
            self._validate_component_connections(node)

        self.is_validated = True

    def _validate_component_connections(self, node: TaskNode) -> None:
        """
        Validate connections for a single component.

        Checks if outputs from previous nodes have fulfill
        all required inputs of the current node.
        """
        component = node.component
        required_inputs = {
            name: info
            for name, info in component.component_inputs.items()
            if not info["has_default"]
        }

        # Get inputs from connections
        provided_inputs: set[str] = set()
        prev_edges = self.previous_edges(node.name)

        component_mapping: dict[str, Any] = {}

        for edge in prev_edges:
            inputs, components = self._validate_input_mapping(node, component, edge)

            provided_inputs = provided_inputs | inputs
            component_mapping = component_mapping | components

        # Store the mapping for this component
        self.param_mapping[node.name] = component_mapping

        # Check for missing required inputs
        missing = set(required_inputs.keys()) - provided_inputs
        self.missing_inputs[node.name] = list(missing)

    def _validate_input_mapping(
        self,
        node: TaskNode,
        component: Component,
        edge: PipelineEdge,
    ) -> tuple[set, dict]:
        provided_inputs: set[str] = set()
        component_mapping: dict[str, Any] = {}

        input_config: dict[str, str] = edge.data.get("input_config", {})

        for target_param, source_path in input_config.items():
            # Check target parameter exists
            if target_param not in component.component_inputs:
                raise ValidationError(
                    f"""Parameter '{target_param}' is not a valid input for component
                        '{node.name}'"""
                )

            # Check if already mapped
            if target_param in component_mapping:
                raise ValidationError(
                    f"Parameter '{target_param}' is already mapped for '{node.name}'"
                )

            # Handle dot notation for output fields
            if "." in source_path:
                source_component, output_field = source_path.split(".", 1)

                # Check source component exists
                if source_component not in self._nodes:
                    raise ValidationError(
                        f"Source component '{source_component}' does not exist"
                    )

                    # Check output field exists in source component
                source_node = self._nodes[source_component]
                if output_field not in source_node.component.component_outputs:
                    raise ValidationError(
                        f"""Output field '{output_field}' does not exist in component
                              '{source_component}'"""
                    )

                    # Check types are compatible
                source_type = source_node.component.component_outputs[output_field][
                    "annotation"
                ]
                target_type = component.component_inputs[target_param]["annotation"]

                if not self._check_type_compatibility(source_type, target_type):  # type: ignore
                    raise ValidationError(
                        f"Type mismatch: {source_component}.{output_field}"
                        f"({source_type}) is not compatible with "
                        f"{node.name}.{target_param} ({target_type})"
                    )

                component_mapping[target_param] = {
                    "component": source_component,
                    "param": output_field,
                }
            else:
                # Whole component result mapping
                source_component = source_path

                # Check source component exists
                if source_component not in self._nodes:
                    raise ValidationError(
                        f"Source component '{source_component}' does not exist"
                    )

                component_mapping[target_param] = {"component": source_component}

            provided_inputs.add(target_param)

        return provided_inputs, component_mapping

    def _check_type_compatibility(self, source_type: type, target_type: type) -> bool:
        """Check if the source type is compatible with the target type."""
        # For now, use simple issubclass check
        # This could be enhanced with more sophisticated type checking
        try:
            return issubclass(source_type, target_type)
        except TypeError:
            # Handle complex types
            return True

    def validate_run_inputs(self, inputs: dict[str, Any]) -> None:
        """Validate that all missing required inputs are provided in the run inputs."""
        if not self.is_validated:
            self.validate()

        for component_name, missing in self.missing_inputs.items():
            component_inputs = inputs.get(component_name, {})
            for param in missing:
                if param not in component_inputs:
                    raise ValidationError(
                        f"""Required parameter '{param}' for component
                         '{component_name}' not provided"""
                    )

    async def run(self, inputs: dict[str, Any] | None = None) -> PipelineResult:
        """Execute the pipeline."""
        pipeline_start_time = time.time()
        inputs = inputs or {}
        run_id = str(uuid.uuid4())

        self.logger.info(f"Starting pipeline run {run_id}")

        # Initialization phase
        await self._initialize_run(run_id, inputs)

        # Execution phase
        run_status = await self._execute_pipeline(run_id, inputs)

        # Completion phase based on run status
        match run_status:
            case PipelineRunStatus.COMPLETED:
                self.logger.info("Pipeline run %s completed successfully", run_id)
                await self.state_manager.commit_version()
                await self.run_tracker.record_run_completion(run_id)
            case PipelineRunStatus.STOPPED:
                self.logger.info("Pipeline run %s stopped early (requested)", run_id)
                await self.state_manager.discard_pending()
                await self.run_tracker.record_run_completion(run_id, stopped_early=True)
            case PipelineRunStatus.FAILED:
                self.logger.error("Pipeline run %s failed", run_id)
                await self.state_manager.discard_pending()
                await self.run_tracker.record_run_failure(
                    run_id, "One or more components failed"
                )
            case _:
                raise PipelineError("undefined PipelineRunStatus")

        success = run_status in (PipelineRunStatus.COMPLETED, PipelineRunStatus.STOPPED)
        final_results = await self._collect_results(run_id)

        pipeline_execution_time = time.time() - pipeline_start_time
        self.logger.info(
            f"Pipeline run {run_id} completed in {pipeline_execution_time:.2f} seconds"
        )

        return PipelineResult(
            run_id=run_id,
            results=final_results,
            success=success,
            stopped_early=(run_status == PipelineRunStatus.STOPPED),
            status=run_status,
        )

    async def get_node_status(self, run_id: str, node_name: str) -> RunStatus:
        """Get the current status of a node in a specific run."""
        status_str = await self.store.get_status_for_component(run_id, node_name)
        return RunStatus(status_str) if status_str else RunStatus.PENDING

    async def set_node_status(
        self, run_id: str, node_name: str, status: RunStatus
    ) -> None:
        """Set the status of a node in a specific run."""
        current_status = await self.get_node_status(run_id, node_name)

        # Check if the status transition is valid
        if status not in current_status.possible_next_status():
            raise PipelineStatusUpdateError(
                f"Invalid status transition: {current_status} -> {status}"
            )

        await self.store.add_status_for_component(run_id, node_name, status.value)

    async def _initialize_run(self, run_id: str, inputs: dict[str, Any]) -> None:
        """Initialize pipeline run."""
        self.validate()
        self.validate_run_inputs(inputs)

        self.logger.info(f"Starting pipeline run {run_id}")
        await self.state_manager.initialize()
        await self.state_manager.prepare_new_version(run_id)
        await self.run_tracker.record_run_start(run_id, inputs)

        # Initialize component statuses
        for node in self._nodes.values():
            await self.store.add_status_for_component(
                run_id, node.name, RunStatus.PENDING.value
            )

    async def _execute_pipeline(
        self, run_id: str, inputs: dict[str, Any]
    ) -> PipelineRunStatus:
        """
        Execute pipeline components and return status.

        Returns:
            PipelineRunStatus: Status of the pipeline run
        """
        try:
            async with asyncio.TaskGroup() as tg:
                # Start root tasks
                for node in self.roots():
                    tg.create_task(self._execute_node(run_id, node.name, inputs, tg))

            for node_name in self._nodes:
                status = await self.get_node_status(run_id, node_name)
                if status == RunStatus.FAILED:
                    self.logger.error(f"Component {node_name} failed")
                    return PipelineRunStatus.FAILED
                elif status == RunStatus.STOP_PIPELINE:
                    self.logger.info(f"Pipeline stopped by component {node_name}")
                    return PipelineRunStatus.STOPPED

            return PipelineRunStatus.COMPLETED

        except Exception as e:
            self.logger.error(f"Pipeline execution error: {str(e)}")
            return PipelineRunStatus.FAILED

    async def _collect_results(self, run_id: str) -> dict[str, Any]:
        """Collect results from leaf nodes."""
        final_results = {}
        for node in self.leaves():
            result = await self.store.get_result_for_component(run_id, node.name)
            if result:
                final_results[node.name] = result
        return final_results

    async def _execute_node(
        self,
        run_id: str,
        node_name: str,
        global_inputs: dict[str, Any],
        tg: asyncio.TaskGroup,
    ) -> None:
        # Check dependencies
        for edge in self.previous_edges(node_name):
            dep_status = await self.get_node_status(run_id, edge.start)
            if dep_status != RunStatus.DONE:
                # Dependency not ready yet
                return

        # Set status to running
        try:
            await self.set_node_status(run_id, node_name, RunStatus.RUNNING)
        except PipelineStatusUpdateError:
            # Another instance is already running this node
            return

        node = self._nodes[node_name]
        self.logger.info(f"Executing node {node_name}")

        try:
            # Prepare inputs
            node_inputs = await self._prepare_node_inputs(
                run_id, node_name, global_inputs
            )

            # Load component state
            component_state = await self.state_manager.get_component_state(node_name)
            node_inputs["state"] = component_state

            # Run the component
            self.logger.debug("Running component %s", node_name)
            run_result = await node.run(**node_inputs)

            # Store results
            if run_result.result is not None:
                await self.store.add_result_for_component(
                    run_id, node_name, run_result.result.model_dump(mode="json")
                )

            # Stage component state if provided
            if (
                hasattr(run_result.result, "state")
                and run_result.result.state is not None
            ):
                await self.state_manager.stage_component_state(
                    node_name, run_result.result.model_dump(mode="json")["state"]
                )

            # Update status
            await self.set_node_status(run_id, node_name, run_result.status)

            # If successful, schedule child nodes
            if run_result.status == RunStatus.DONE:
                for edge in self.next_edges(node_name):
                    tg.create_task(
                        self._execute_node(run_id, edge.end, global_inputs, tg)
                    )
            elif run_result.status == RunStatus.STOP_PIPELINE:
                self.logger.info(f"Node {node_name} requested pipeline stop")
            else:
                self.logger.warning(
                    f"Node {node_name} completed with status {run_result.status}"
                )

        except Exception as e:
            # Handle failure
            self.logger.exception(f"Error executing node {node_name}: {str(e)}")
            await self.set_node_status(run_id, node_name, RunStatus.FAILED)
            await self.store.add_result_for_component(
                run_id, node_name, {"error": str(e)}
            )
            raise

    async def _prepare_node_inputs(
        self, run_id: str, node_name: str, global_inputs: dict[str, Any]
    ) -> dict[str, Any]:
        """Prepare inputs for a node execution."""
        node_inputs = {}

        # Add component-specific inputs from global inputs
        if node_name in global_inputs:
            node_inputs.update(global_inputs[node_name])

        # Add inputs from parent nodes
        node_mapping = self.param_mapping.get(node_name, {})
        for param_name, mapping in node_mapping.items():
            source_component = mapping["component"]
            source_param = mapping.get("param")

            # Get the source component result
            source_result = await self.store.get_result_for_component(
                run_id, source_component
            )

            if source_result is None:
                continue

            if source_param:
                # Map specific field
                if source_param in source_result:
                    node_inputs[param_name] = source_result[source_param]
            else:
                # Map entire result
                node_inputs[param_name] = source_result
        return node_inputs
