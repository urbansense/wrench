from typing import Any

from autoreg_metadata.adapter.base import MetadataAdapter
from autoreg_metadata.catalogger.ckan.models import APIService
from autoreg_metadata.common.models import EndpointMetadata
from autoreg_metadata.harvester.frost.models import Thing


class FrostToCKANAdapter(MetadataAdapter[tuple[EndpointMetadata, list[Thing]], tuple[APIService, dict[str, list[str]]]]):
    """
    Adapter to convert from FROST harvester metadata format to CKAN catalogger format.
    """

    def adapt(self, metadata: tuple[EndpointMetadata, list[Thing]], **kwargs: Any) -> tuple[APIService, dict[str, list[str]]]:
        """
        Convert FROST metadata to CKAN format.

        Args:
            metadata: Tuple of (EndpointMetadata, list of Thing objects) from FROST harvester
            **kwargs: Must include:
                - author_email: str
                - license_id: str
                - owner_org: str

        Returns:
            Tuple of (APIService, device groups dict) for CKAN catalogger
        """
        endpoint_meta, things = metadata

        # Validate required kwargs
        required_fields = ['author_email', 'license_id', 'owner_org']
        missing_fields = [
            field for field in required_fields if field not in kwargs]
        if missing_fields:
            raise ValueError(f"Missing required fields: {
                             ', '.join(missing_fields)}")

        # Create APIService object
        api_service = APIService(
            api_url=endpoint_meta.endpoint_url,
            author=endpoint_meta.author or "Unknown",
            author_email=kwargs['author_email'],
            name=self._generate_name(endpoint_meta.endpoint_url),
            language=endpoint_meta.language or "en",
            license_id=kwargs['license_id'],
            notes=self._generate_notes(endpoint_meta),
            owner_org=kwargs['owner_org'],
            tags=self._generate_tags(endpoint_meta),
            title=self._generate_title(endpoint_meta.endpoint_url)
        )

        # Create device groups dictionary
        device_groups = self._create_device_groups(things)

        return api_service, device_groups

    def _generate_name(self, url: str) -> str:
        """Generate a URL-friendly name from the endpoint URL"""
        # Remove protocol and special characters, convert to lowercase
        name = url.split('://')[-1].replace('/', '-').replace('.', '-').lower()
        # Ensure name starts with a letter
        if not name[0].isalpha():
            name = f"api-{name}"
        return name[:100]  # Limit length

    def _generate_notes(self, metadata: EndpointMetadata) -> str:
        """Generate description from metadata"""
        notes = [f"API Endpoint: {metadata.endpoint_url}"]

        if metadata.timeframe:
            notes.append(
                f"Time Range: {metadata.timeframe.start_time.date()} to {
                    metadata.timeframe.latest_time.date()}"
            )

        if metadata.geographical_extent:
            sw, ne = metadata.geographical_extent
            notes.append(
                f"Geographic Coverage: SW({sw.latitude}, {sw.longitude}) to NE({
                    ne.latitude}, {ne.longitude})"
            )

        if metadata.sensor_types:
            notes.append(f"Sensor Types: {', '.join(metadata.sensor_types)}")

        if metadata.measurements:
            notes.append(f"Measurements: {', '.join(metadata.measurements)}")

        return "\n".join(notes)

    def _generate_tags(self, metadata: EndpointMetadata) -> list[str]:
        """Generate tags from metadata"""
        tags = ["api", "iot", "sensor-data"]

        if metadata.sensor_types:
            tags.extend(metadata.sensor_types)
        if metadata.measurements:
            tags.extend(metadata.measurements)

        # Clean and deduplicate tags
        clean_tags = []
        seen = set()
        for tag in tags:
            clean_tag = tag.lower().replace(' ', '-')[:100]
            if clean_tag not in seen:
                clean_tags.append(clean_tag)
                seen.add(clean_tag)

        return clean_tags[:50]  # Limit number of tags

    def _generate_title(self, url: str) -> str:
        """Generate a human-readable title from the endpoint URL"""
        # Remove protocol and path
        domain = url.split('://')[-1].split('/')[0]
        return f"IoT API Service - {domain}"

    def _create_device_groups(self, things: list[Thing]) -> dict[str, list[str]]:
        """
        Create device groups dictionary from Thing objects.
        Groups sensors by their observed property/measurement type.
        """
        device_groups: dict[str, list[str]] = {}

        for thing in things:
            for datastream in thing.datastreams:
                if datastream.observed_property:
                    # Use observed property name as group key
                    group_key = datastream.observed_property.name.lower().replace(' ', '_')

                    if group_key not in device_groups:
                        device_groups[group_key] = []

                    # Add thing ID to group
                    device_groups[group_key].append(str(thing.id))

        return device_groups
