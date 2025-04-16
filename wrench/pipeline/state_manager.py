from typing import Any

from wrench.log import logger
from wrench.pipeline.stores import ResultStore


class PipelineStateManager:
    """Manages versioned state for pipeline components."""

    def __init__(self, store: ResultStore):
        self.store = store
        self.logger = logger.getChild(self.__class__.__name__)

    async def initialize(self):
        """Load current state version."""
        self.current_version = await self.store.get("pipeline:state:current_version")
        if self.current_version:
            self.logger.debug(f"Initialized with state version: {self.current_version}")
        else:
            self.logger.debug("No existing state version found")

    async def get_component_state(self, component_name: str) -> dict[str, Any]:
        """Get state for a component from current version."""
        if not hasattr(self, "current_version") or not self.current_version:
            return {}

        self.logger.debug("Getting state from version: %s", self.current_version)
        key = f"state:v{self.current_version}:{component_name}"
        return await self.store.get(key) or {}

    async def prepare_new_version(self, run_id: str):
        """Prepare for a new state version."""
        # Use run_id as version identifier for traceability
        self.pending_version = run_id
        self.pending_states = {}
        self.logger.debug(f"Prepared new state version for run {run_id}")

    async def stage_component_state(self, component_name: str, state: dict[str, Any]):
        """Stage component state for the new version (in memory)."""
        if not hasattr(self, "pending_version"):
            raise ValueError("Must call prepare_new_version before staging state")

        # Store in memory until commit
        self.pending_states[component_name] = state

    async def commit_version(self):
        """Commit the pending state version to storage."""
        if not hasattr(self, "pending_version") or not self.pending_states:
            self.logger.warning("No pending state to commit")
            return

        # Save all component states
        for component_name, state in self.pending_states.items():
            key = f"state:v{self.pending_version}:{component_name}"
            await self.store.add(key, state, overwrite=True)

        # Update current version pointer
        previous_version = getattr(self, "current_version", None)
        await self.store.add(
            "pipeline:state:current_version", self.pending_version, overwrite=True
        )
        await self.store.add(
            "pipeline:state:previous_version", previous_version, overwrite=True
        )

        self.logger.info(
            f"Committed state version {self.pending_version} "
            f"with {len(self.pending_states)} components"
        )

        # Update current version
        self.current_version = self.pending_version

        # Clear pending data
        delattr(self, "pending_version")
        delattr(self, "pending_states")

    async def discard_pending(self):
        """Discard pending state changes."""
        if hasattr(self, "pending_version"):
            self.logger.info(f"Discarded pending state version {self.pending_version}")
            delattr(self, "pending_version")
            delattr(self, "pending_states")
