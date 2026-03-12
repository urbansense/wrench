# Creating a new component

Wrench is built around four extensible component types. Each has an abstract
base class you subclass. Follow the steps below for the type you want to add.

---

## Adding a new Harvester

A Harvester connects to a data source and returns a list of `Device` objects.

**1. Create the directory structure:**

```
wrench/harvester/your_source/
  __init__.py
  harvester.py
  models.py          # source-specific Pydantic models (optional)
  config.py          # configuration dataclass (optional)
```

**2. Subclass `BaseHarvester`:**

```python
# wrench/harvester/your_source/harvester.py

from wrench.harvester.base import BaseHarvester
from wrench.models import Device


class YourSourceHarvester(BaseHarvester):
    def __init__(self, base_url: str, **kwargs) -> None:
        # Always call super().__init__() — it sets up self.logger.
        super().__init__()
        self.base_url = base_url

    def return_devices(self) -> list[Device]:
        """Fetch data from the source and return a list of Device objects.

        Returns:
            list[Device]: All devices currently available at the source.
        """
        raw_items = self._fetch_from_source()
        return [self._to_device(item) for item in raw_items]

    def _fetch_from_source(self) -> list[dict]:
        """Call the external API or read from a file/DB."""
        ...

    def _to_device(self, raw: dict) -> Device:
        """Convert a source-specific record into a Device."""
        ...
```

**3. Register the harvester** in `wrench/harvester/__init__.py`:

```python
from .your_source import YourSourceHarvester

HARVESTERS: dict[str, type[BaseHarvester]] = {
    "sensorthings": SensorThingsHarvester,
    "your_source": YourSourceHarvester,   # add this line
}
```

**4. Export from `__init__.py`** (add to `__all__`).

**5. Add tests** under `tests/unit-test/harvester/your_source/`.

---

## Adding a new Grouper

A Grouper receives a list of `Device` objects and returns a list of `Group`
objects.

**1. Create the directory structure:**

```
wrench/grouper/your_algorithm/
  __init__.py
  grouper.py
  models.py          # algorithm-specific Pydantic models (optional)
```

**2. Subclass `BaseGrouper`:**

```python
# wrench/grouper/your_algorithm/grouper.py

from wrench.grouper.base import BaseGrouper
from wrench.models import Device, Group


class YourAlgorithmGrouper(BaseGrouper):
    def __init__(self, n_groups: int = 5) -> None:
        self.n_groups = n_groups

    def group_devices(self, devices: list[Device], **kwargs) -> list[Group]:
        """Assign devices to groups using your algorithm.

        Args:
            devices: Devices to group, as returned by the harvester.
            **kwargs: Optional arguments; unused kwargs must be accepted.

        Returns:
            list[Group]: One Group per discovered topic or category.
                         Each Group must have a unique `name`.
        """
        # Implement your grouping logic here.
        # Assign parent_classes for hierarchical classification (optional).
        ...
        return [
            Group(
                name="Example Group",
                devices=some_subset,
                parent_classes={"Environment"},
            )
        ]
```

`BaseGrouper` provides `process_operations()`, `_merge_groups()`, and
`_remove_items()` for handling incremental add/update/delete runs. You do not
need to override them unless you require custom merge behaviour.

**3. Register the grouper** in `wrench/grouper/__init__.py`:

```python
from .your_algorithm import YourAlgorithmGrouper

GROUPERS: dict[str, type[BaseGrouper]] = {
    "kinetic": KINETIC,
    "your_algorithm": YourAlgorithmGrouper,   # add this line
}
```

**4. Export from `__init__.py`** (add to `__all__`).

**5. Add tests** under `tests/unit-test/grouper/your_algorithm/`.

---

## Adding a new MetadataEnricher

A MetadataEnricher builds `CommonMetadata` for the overall service and for
each device group. It is source-specific because spatial extent calculation
and URL construction differ by data source type.

**1. Create the directory structure:**

```
wrench/metadataenricher/your_source/
  __init__.py
  enricher.py
  spatial.py         # spatial extent helpers (optional)
```

**2. Subclass `BaseMetadataEnricher`:**

```python
# wrench/metadataenricher/your_source/enricher.py

from typing import Any

from wrench.metadataenricher.base import BaseMetadataEnricher
from wrench.models import Device
from wrench.utils.config import LLMConfig


class YourSourceMetadataEnricher(BaseMetadataEnricher):
    def __init__(
        self, base_url: str, title: str, description: str, llm_config: LLMConfig
    ) -> None:
        # Always call super().__init__() — it stores title, description, and
        # initialises self.content_generator when llm_config is provided.
        super().__init__(title=title, description=description, llm_config=llm_config)
        self.base_url = base_url.rstrip("/")

    # ------------------------------------------------------------------
    # Required abstract methods
    # ------------------------------------------------------------------

    def _get_source_type(self) -> str:
        """Return a short identifier for this source type."""
        return "your_source"

    def _build_service_urls(self, devices: list[Device]) -> list[str]:
        """Return the top-level endpoint URL(s) for the service."""
        return [self.base_url]

    def _build_group_urls(self, devices: list[Device]) -> list[str]:
        """Return URLs that narrow the service to a specific group of devices."""
        ids = ",".join(device.id for device in devices)
        return [f"{self.base_url}/Things?$filter=id in ({ids})"]

    def _calculate_service_spatial_extent(self, devices: list[Device]) -> Any:
        """Calculate the bounding extent for all service devices.

        Returns any object whose str() is valid GeoJSON or WKT.
        """
        return "{}"

    def _calculate_group_spatial_extent(self, devices: list[Device]) -> Any:
        """Calculate the bounding extent for a single group's devices."""
        return "{}"
```

`BaseMetadataEnricher` provides `build_service_metadata()`,
`build_group_metadata()`, and `_calculate_timeframe()` — override these only
if you need to change how metadata objects are assembled.

**3. Register the enricher** in `wrench/metadataenricher/__init__.py`:

```python
from .your_source import YourSourceMetadataEnricher

METADATA_ENRICHERS: dict[str, type[BaseMetadataEnricher]] = {
    "sensorthings": SensorThingsMetadataEnricher,
    "your_source": YourSourceMetadataEnricher,   # add this line
}
```

**4. Export from `__init__.py`** (add to `__all__`).

**5. Add tests** under `tests/unit-test/metadataenricher/your_source/`.

---

## Adding a new Cataloger

A Cataloger receives enriched `CommonMetadata` and registers it in a data
catalog.

**1. Create the directory structure:**

```
wrench/cataloger/your_catalog/
  __init__.py
  cataloger.py
  models.py          # catalog-specific Pydantic models (optional)
  config.py          # configuration model (optional)
```

**2. Subclass `BaseCataloger`:**

```python
# wrench/cataloger/your_catalog/cataloger.py

from wrench.cataloger.base import BaseCataloger
from wrench.models import CommonMetadata


class YourCataloger(BaseCataloger):
    def __init__(self, base_url: str, api_key: str, **kwargs) -> None:
        # super().__init__() stores endpoint and api_key, and sets up self.logger.
        super().__init__(endpoint=base_url, api_key=api_key)
        # Initialize your catalog client here.

    def register(
        self,
        service: CommonMetadata,
        groups: list[CommonMetadata],
        managed_entries: list[str] | None,
    ) -> list[str]:
        """Register the service and its groups in the catalog.

        Args:
            service: Metadata for the top-level service.
            groups: Metadata for each device group.
            managed_entries: Identifiers previously registered by this cataloger.
                             Use these to distinguish creates from updates.

        Returns:
            list[str]: Identifiers of all entries now managed by this cataloger.
                       The pipeline passes this back as `managed_entries` on the
                       next run.
        """
        registered: list[str] = list(managed_entries or [])

        if service.identifier not in registered:
            self._create_entry(service)
            registered.append(service.identifier)
        else:
            self._update_entry(service)

        for group in groups:
            if group.identifier not in registered:
                self._create_entry(group)
                registered.append(group.identifier)
            else:
                self._update_entry(group)

        return registered

    def _create_entry(self, metadata: CommonMetadata) -> None:
        """Create a new entry in the catalog."""
        ...

    def _update_entry(self, metadata: CommonMetadata) -> None:
        """Update an existing entry in the catalog."""
        ...
```

**3. Register the cataloger** in `wrench/cataloger/__init__.py`:

```python
from .your_catalog import YourCataloger

CATALOGERS: dict[str, type[BaseCataloger]] = {
    "noop": NoopCataloger,
    "sddi": SDDICataloger,
    "your_catalog": YourCataloger,   # add this line
}
```

**4. Export from `__init__.py`** (add to `__all__`).

**5. Add tests** under `tests/unit-test/cataloger/your_catalog/`.
