from wrench.grouper.base import BaseGrouper
from wrench.models import Device, Group


class StubGrouper(BaseGrouper):
    """Groups devices by putting each device in its own group named after its id."""

    def group_devices(self, devices: list[Device], **kwargs) -> list[Group]:
        groups: list[Group] = []
        for device in devices:
            groups.append(Group(name=f"group-{device.id}", devices=[device]))
        return groups


class SingleGroupGrouper(BaseGrouper):
    """Groups all devices into one group."""

    def __init__(self, group_name="all"):
        self._group_name = group_name

    def group_devices(self, devices: list[Device], **kwargs) -> list[Group]:
        if not devices:
            return []
        return [Group(name=self._group_name, devices=list(devices))]


class TestMergeGroups:
    def test_merge_new_group_appended(self, make_device):
        grouper = StubGrouper()
        d1 = make_device(id="d-1")
        d2 = make_device(id="d-2")
        existing = [Group(name="group-d-1", devices=[d1])]
        new = [Group(name="group-d-2", devices=[d2])]
        grouper._merge_groups(existing, new)
        assert len(existing) == 2
        names = {g.name for g in existing}
        assert names == {"group-d-1", "group-d-2"}

    def test_merge_existing_group_updates_devices(self, make_device):
        grouper = StubGrouper()
        d1 = make_device(id="d-1", name="Original")
        d1_updated = make_device(id="d-1", name="Updated")
        existing = [Group(name="g1", devices=[d1])]
        new = [Group(name="g1", devices=[d1_updated])]
        grouper._merge_groups(existing, new)
        assert len(existing) == 1
        # The device should have been replaced
        assert existing[0].devices[0].name == "Updated"

    def test_merge_same_name_different_devices_appends_as_new(self, make_device):
        """Groups use Pydantic default equality (all fields), so groups with
        the same name but different devices are treated as distinct."""
        grouper = StubGrouper()
        d1 = make_device(id="d-1")
        d2 = make_device(id="d-2")
        existing = [Group(name="g1", devices=[d1])]
        new = [Group(name="g1", devices=[d2])]
        grouper._merge_groups(existing, new)
        # Since the groups are not equal (different devices), the new one is appended
        assert len(existing) == 2

    def test_merge_empty_new_groups(self, make_device):
        grouper = StubGrouper()
        d1 = make_device(id="d-1")
        existing = [Group(name="g1", devices=[d1])]
        grouper._merge_groups(existing, [])
        assert len(existing) == 1

    def test_merge_into_empty_existing(self, make_device):
        grouper = StubGrouper()
        d1 = make_device(id="d-1")
        existing: list[Group] = []
        new = [Group(name="g1", devices=[d1])]
        grouper._merge_groups(existing, new)
        assert len(existing) == 1

    def test_merge_equal_groups_merges_in_place(self, make_device):
        """When groups are fully equal (Pydantic default __eq__),
        the merge path fires and updates devices in-place."""
        grouper = StubGrouper()
        d1 = make_device(id="d-1")
        existing = [Group(name="g1", devices=[d1])]
        new = [Group(name="g1", devices=[d1])]
        grouper._merge_groups(existing, new)
        assert len(existing) == 1

    def test_merge_different_parent_classes_treated_as_new(self, make_device):
        """Groups with same name but different parent_classes are not equal
        per Pydantic default comparison, so they get appended."""
        grouper = StubGrouper()
        d1 = make_device(id="d-1")
        existing = [Group(name="g1", devices=[d1], parent_classes={"ClassA"})]
        new = [Group(name="g1", devices=[d1], parent_classes={"ClassB"})]
        grouper._merge_groups(existing, new)
        assert len(existing) == 2


class TestRemoveItems:
    def test_remove_device_from_group(self, make_device):
        grouper = StubGrouper()
        d1 = make_device(id="d-1")
        d2 = make_device(id="d-2")
        groups = [Group(name="g1", devices=[d1, d2])]
        affected = grouper._remove_items(groups, [d1])
        assert affected == {"g1"}
        assert len(groups[0].devices) == 1
        assert groups[0].devices[0].id == "d-2"

    def test_remove_device_not_in_any_group(self, make_device):
        grouper = StubGrouper()
        d1 = make_device(id="d-1")
        d_other = make_device(id="d-other")
        groups = [Group(name="g1", devices=[d1])]
        affected = grouper._remove_items(groups, [d_other])
        assert affected == set()
        assert len(groups[0].devices) == 1

    def test_remove_from_multiple_groups(self, make_device):
        grouper = StubGrouper()
        d1 = make_device(id="d-1")
        d2 = make_device(id="d-2")
        groups = [
            Group(name="g1", devices=[d1, d2]),
            Group(name="g2", devices=[d1]),
        ]
        affected = grouper._remove_items(groups, [d1])
        assert affected == {"g1", "g2"}
        assert len(groups[0].devices) == 1
        assert len(groups[1].devices) == 0

    def test_remove_all_devices_from_group(self, make_device):
        grouper = StubGrouper()
        d1 = make_device(id="d-1")
        groups = [Group(name="g1", devices=[d1])]
        affected = grouper._remove_items(groups, [d1])
        assert affected == {"g1"}
        assert len(groups[0].devices) == 0

    def test_remove_empty_delete_list(self, make_device):
        grouper = StubGrouper()
        d1 = make_device(id="d-1")
        groups = [Group(name="g1", devices=[d1])]
        affected = grouper._remove_items(groups, [])
        assert affected == set()
        assert len(groups[0].devices) == 1


class TestProcessOperations:
    def test_new_devices_create_new_groups(self, make_device):
        grouper = StubGrouper()
        d1 = make_device(id="d-1")
        all_groups, affected = grouper.process_operations(
            existing_groups=[],
            new_devices=[d1],
            updated_devices=[],
            deleted_devices=[],
        )
        assert len(all_groups) == 1
        assert all_groups[0].name == "group-d-1"
        assert len(affected) == 1

    def test_updated_devices_merged_into_groups(self, make_device):
        grouper = SingleGroupGrouper(group_name="all")
        d1 = make_device(id="d-1", name="Original")
        existing = [Group(name="all", devices=[d1])]
        d1_updated = make_device(id="d-1", name="Updated")
        all_groups, affected = grouper.process_operations(
            existing_groups=existing,
            new_devices=[],
            updated_devices=[d1_updated],
            deleted_devices=[],
        )
        assert len(affected) == 1
        assert affected[0].name == "all"

    def test_deleted_devices_removed(self, make_device):
        grouper = StubGrouper()
        d1 = make_device(id="d-1")
        d2 = make_device(id="d-2")
        existing = [
            Group(name="group-d-1", devices=[d1]),
            Group(name="group-d-2", devices=[d2]),
        ]
        all_groups, affected = grouper.process_operations(
            existing_groups=existing,
            new_devices=[],
            updated_devices=[],
            deleted_devices=[d1],
        )
        assert len(all_groups) == 2  # Groups still exist
        assert len(affected) == 1
        assert affected[0].name == "group-d-1"
        assert len(affected[0].devices) == 0

    def test_no_changes_returns_empty_affected(self, make_device):
        grouper = StubGrouper()
        d1 = make_device(id="d-1")
        existing = [Group(name="group-d-1", devices=[d1])]
        all_groups, affected = grouper.process_operations(
            existing_groups=existing,
            new_devices=[],
            updated_devices=[],
            deleted_devices=[],
        )
        assert len(all_groups) == 1
        assert len(affected) == 0

    def test_combined_add_and_delete(self, make_device):
        grouper = StubGrouper()
        d1 = make_device(id="d-1")
        d2 = make_device(id="d-2")
        existing = [Group(name="group-d-1", devices=[d1])]
        all_groups, affected = grouper.process_operations(
            existing_groups=existing,
            new_devices=[d2],
            updated_devices=[],
            deleted_devices=[d1],
        )
        assert len(all_groups) == 2
        affected_names = {g.name for g in affected}
        assert "group-d-2" in affected_names
        assert "group-d-1" in affected_names
