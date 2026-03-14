import pytest

from wrench.components.harvester import Harvester
from wrench.exceptions import HarvesterError
from wrench.harvester.base import BaseHarvester
from wrench.pipeline.types import OperationType


class StubHarvester(BaseHarvester):
    def __init__(self, devices=None):
        super().__init__()
        self._devices = devices or []

    def return_devices(self):
        return self._devices


class FailingHarvester(BaseHarvester):
    def __init__(self):
        super().__init__()

    def return_devices(self):
        raise RuntimeError("Connection refused")


class TestHarvesterComponentFirstRun:
    async def test_first_run_all_add_operations(self, make_device):
        devices = [make_device(id=f"d-{i}") for i in range(3)]
        component = Harvester(StubHarvester(devices))
        result = await component.run()
        assert len(result.operations) == 3
        assert all(op.type == OperationType.ADD for op in result.operations)
        assert len(result.devices) == 3

    async def test_first_run_sets_state(self, make_device):
        devices = [make_device(id="d-1")]
        component = Harvester(StubHarvester(devices))
        await component.run()
        assert "previous_devices" in component.state

    async def test_first_run_empty_devices(self):
        component = Harvester(StubHarvester([]))
        result = await component.run()
        assert len(result.operations) == 0
        assert len(result.devices) == 0

    async def test_first_run_does_not_stop_pipeline(self, make_device):
        devices = [make_device(id="d-1")]
        component = Harvester(StubHarvester(devices))
        result = await component.run()
        assert result.stop_pipeline is False


class TestHarvesterComponentIncremental:
    async def test_no_changes_stops_pipeline(self, make_device):
        device = make_device(id="d-1", name="Same")
        component = Harvester(StubHarvester([device]))
        await component.run()

        # Second run with identical devices and the saved state
        component2 = Harvester(StubHarvester([device]))
        component2.state = component.state
        result = await component2.run()
        assert result.stop_pipeline is True
        assert len(result.operations) == 0

    async def test_new_device_detected_as_add(self, make_device):
        d1 = make_device(id="d-1")
        component_initial = Harvester(StubHarvester([d1]))
        await component_initial.run()

        d2 = make_device(id="d-2")
        component_updated = Harvester(StubHarvester([d1, d2]))
        component_updated.state = component_initial.state
        result = await component_updated.run()
        add_ops = [op for op in result.operations if op.type == OperationType.ADD]
        assert len(add_ops) == 1
        assert add_ops[0].device.id == "d-2"

    async def test_removed_device_detected_as_delete(self, make_device):
        d1 = make_device(id="d-1")
        d2 = make_device(id="d-2")
        component_initial = Harvester(StubHarvester([d1, d2]))
        await component_initial.run()

        component_updated = Harvester(StubHarvester([d1]))
        component_updated.state = component_initial.state
        result = await component_updated.run()
        delete_ops = [op for op in result.operations if op.type == OperationType.DELETE]
        assert len(delete_ops) == 1
        assert delete_ops[0].device.id == "d-2"

    async def test_modified_device_detected_as_update(self, make_device):
        d1 = make_device(id="d-1", name="Original")
        component_initial = Harvester(StubHarvester([d1]))
        await component_initial.run()

        d1_modified = make_device(id="d-1", name="Modified Name")
        component_updated = Harvester(StubHarvester([d1_modified]))
        component_updated.state = component_initial.state
        result = await component_updated.run()
        update_ops = [op for op in result.operations if op.type == OperationType.UPDATE]
        assert len(update_ops) == 1
        assert update_ops[0].device.id == "d-1"


class TestHarvesterComponentErrorHandling:
    async def test_harvester_error_raised_on_failure(self):
        component = Harvester(FailingHarvester())
        with pytest.raises(HarvesterError, match="Failed to retrieve"):
            await component.run()


class TestHarvesterHashContent:
    def test_hash_consistency(self, make_device):
        component = Harvester(StubHarvester([]))
        device = make_device(id="d-1")
        h1 = component._hash_content(device.model_dump())
        h2 = component._hash_content(device.model_dump())
        assert h1 == h2

    def test_hash_different_for_different_content(self, make_device):
        component = Harvester(StubHarvester([]))
        d1 = make_device(id="d-1", name="A")
        d2 = make_device(id="d-1", name="B")
        h1 = component._hash_content(d1.model_dump())
        h2 = component._hash_content(d2.model_dump())
        assert h1 != h2
