import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from geojson import Polygon

from wrench.harvester.base import BaseHarvester
from wrench.log import logger
from wrench.models import CommonMetadata, Item, TimeFrame

from .config import SensorThingsConfig
from .models import GenericLocation, Location, SensorThingsBase, Thing
from .translator import LibreTranslateService


class SensorThingsHarvester(BaseHarvester):
    """
    Harvests SensorThings API entities.

    Returns metadata and list of items contained in the
    API server
    """

    def __init__(
        self,
        config: SensorThingsConfig | str | Path,
        location_model: type[GenericLocation] = Location,
    ):
        """
        Initialize the harvester.

        Args:
            config (SensorThingsConfig | str | Path): Configuration for the harvester.
            location_model (type[GenericLocation], optional): Custom Location Model.

        Attributes:
            config (SensorThingsConfig): Harvester configuration.
            logger (Logger): Logger instance.
            translator (LibreTranslateService | None): Translator service if configured.
            location_model (type[GenericLocation]): Location model.
            things (list): Fetched things based on default limit.
        """
        # Load config if path is provided
        if isinstance(config, (str, Path)):
            config = SensorThingsConfig.from_yaml(config)

        self.config = config
        self.logger = logger.getChild(self.__class__.__name__)

        # Set up translator if configured
        translator_config = self.config.translator
        self.translator = (
            LibreTranslateService(translator_config.url, translator_config.source_lang)
            if translator_config
            else None
        )

        self.location_model = location_model

        self.things = self.fetch_things(limit=self.config.default_limit)

    def get_metadata(self) -> CommonMetadata:
        """
        Retrieves metadata for the SensorThings data.

        This method collects the locations of each 'thing' and calculates the geographic
        extent and timeframe for the data. It then returns a CommonMetadata object
        populated with this information.

        Returns:
            CommonMetadata: An object containing metadata such as endpoint URL, title,
                            identifier, description, spatial extent, temporal extent,
                            source type, and last updated time.
        """
        # get locations of each thing, put them into a set to avoid duplicates
        locations = {
            loc.get_coordinates()
            for thing in self.things
            if thing.location
            for loc in thing.location
        }

        geographic_extent = self._calculate_geographic_extent(locations)
        timeframe = self._calculate_timeframe(self.things)

        return CommonMetadata(
            endpoint_url=self.config.base_url,
            title=self.config.title,
            identifier=self.config.identifier,
            description=self.config.description,
            spatial_extent=str(geographic_extent),
            temporal_extent=timeframe,
            source_type="sensorthings",
            last_updated=timeframe.latest_time,
        )

    def get_items(self) -> list[Item]:
        """
        Retrieve the list of Thing objects.

        Returns:
            list[Thing]: A list of Thing objects.
        """
        return self.things

    def fetch_things(self, limit: int = -1) -> list[Thing]:
        """
        Fetches a list of Thing objects, optionally translating them if configured.

        Args:
            limit (int): Max number of Things to fetch. Defaults to -1 (no limit).

        Returns:
            list[Thing]: List of fetched Things, potentially translated.

        Raises:
            Exception: Logs error and returns original Thing if translation fails.
        """
        self.logger.debug("Fetching %d things", limit if limit != -1 else 0)
        things = self._fetch_paginated(
            "Things?$expand=Locations,Datastreams($expand=Sensor)",
            Thing,
            limit=limit,
        )

        if not self.translator:
            return things

        # Run translation if translator exists
        self.logger.debug("Translator was configured, starting translation")
        translated_things = []
        for thing in things:
            try:
                translated_thing = self.translator.translate(thing)
                translated_things.append(translated_thing)
            except Exception as e:
                self.logger.error("Translation failed for thing %s: %s", thing.id, e)
                translated_things.append(thing)

        return translated_things

    def fetch_locations(self, limit: int = -1) -> list[GenericLocation]:
        """
        Fetches a list of locations from the SensorThings API.

        Args:
            limit (int, optional): The maximum number of locations to fetch.
                                   If set to -1, fetches all available locations.
                                   Defaults to -1.

        Returns:
            list[GenericLocation]: A list of fetched locations.
        """
        self.logger.debug("Fetching %d locations", limit if limit != -1 else 0)
        return self._fetch_paginated("Locations", self.location_model, limit=limit)

    def _fetch_paginated[T: SensorThingsBase](
        self, endpoint: str, model_class: type[T], limit: int = -1
    ) -> list[T]:
        """
        Fetch paginated data from a SensorThings API endpoint.

        Args:
            endpoint: API endpoint path to fetch from
            model_class: Pydantic model class to validate response data
            limit: Maximum number of items to fetch (-1 for no limit)

        Returns:
            list[SensorThingsBase]: List of validated model instances
        """
        items: list[T] = []
        page_count = 1
        current_url = f"{self.config.base_url}/{endpoint}"
        remaining_items = limit if limit != -1 else None

        while current_url and (remaining_items is None or remaining_items > 0):
            self.logger.info("Fetching page %d", page_count)

            try:
                # Fetch and parse page data
                response = self._fetch_page(current_url)
                page_data = response.json()

                # Check for valid response structure
                if "value" not in page_data:
                    self.logger.warning(
                        "No 'value' field in response, stopping pagination"
                    )
                    break

                # Process items from current page
                new_items = self._process_page_items(
                    page_data["value"], model_class, remaining_items
                )
                items.extend(new_items)

                self.logger.info(
                    "Added %d items from page %d", len(new_items), page_count
                )

                # Update remaining items count
                if remaining_items is not None:
                    remaining_items -= len(new_items)
                    self.logger.debug("Remaining items to fetch: %d", remaining_items)

                # Prepare for next page
                current_url = page_data.get("@iot.nextLink")
                if current_url:
                    time.sleep(self.config.pagination.page_delay)

                page_count += 1

            except requests.RequestException as e:
                self.logger.error("Failed to fetch page %d: %s", page_count, e)
                break

        self.logger.info("Finished fetching data, retrieved %d items", len(items))
        return items

    def _fetch_page(self, url: str) -> requests.Response:
        """
        Fetch a single page of data from the API.

        Args:
            url: Full URL to fetch from

        Returns:
            Response object from successful request

        Raises:
            requests.RequestException: If request fails
        """
        response = requests.get(url, timeout=self.config.pagination.timeout)
        response.raise_for_status()
        return response

    def _process_page_items[T: SensorThingsBase](
        self,
        items: list[dict],
        model_class: type[T],
        remaining_limit: int | None = None,
    ) -> list[T]:
        """
        Process and validate items from a page.

        Args:
            items: Raw item data from API response
            model_class: Pydantic model class for validation
            remaining_limit: Maximum items to process (None for no limit)

        Returns:
            list[SensorThingsBase]: List of validated model instances
        """
        processed_items: list[T] = []

        for item in items:
            if remaining_limit is not None and len(processed_items) >= remaining_limit:
                break

            validated_item = model_class.model_validate(item)
            processed_items.append(validated_item)

        return processed_items

    def _calculate_geographic_extent(
        self, locations: set[tuple[float, float]]
    ) -> Polygon:
        """
        Calculate the geographic bounding box from a set of locations.

        Args:
            locations: Set of locations with coordinate data

        Returns:
            Polygon: GeoJSON polygon representing the bounding box
        """
        # Initialize bounds
        bounds = {
            "min_lat": float("inf"),
            "max_lat": float("-inf"),
            "min_lng": float("inf"),
            "max_lng": float("-inf"),
        }

        # Update bounds for each location
        for lng, lat in locations:
            bounds["min_lat"] = min(bounds["min_lat"], lat)
            bounds["max_lat"] = max(bounds["max_lat"], lat)
            bounds["min_lng"] = min(bounds["min_lng"], lng)
            bounds["max_lng"] = max(bounds["max_lng"], lng)

        # Create polygon coordinates
        coordinates = [
            (bounds["min_lat"], bounds["min_lng"]),
            (bounds["min_lat"], bounds["max_lng"]),
            (bounds["max_lat"], bounds["max_lng"]),
            (bounds["max_lat"], bounds["min_lng"]),
            (bounds["min_lat"], bounds["min_lng"]),  # Close the polygon
        ]

        return Polygon([coordinates])

    def _calculate_timeframe(self, things: list[Thing]) -> TimeFrame:
        """
        Calculate the overall timeframe spanning all sensor data.

        Args:
            things: List of Thing objects containing datastream information

        Returns:
            TimeFrame: Object containing the earliest start time and latest end time

        Notes:
            - Handles ISO format datetime strings from phenomenon_time
            - All times are converted to UTC timezone
            - Skips datastreams with no phenomenon_time
        """
        # Initialize timeframe boundaries
        time_bounds = {
            "earliest": datetime.max.replace(tzinfo=timezone.utc),
            "latest": datetime.min.replace(tzinfo=timezone.utc),
        }

        # Process each datastream's phenomenon time
        for thing in things:
            for datastream in thing.datastreams:
                if not datastream.phenomenon_time:
                    continue

                # Parse phenomenon time range
                start_str, end_str = datastream.phenomenon_time.split("/")
                timespan = {
                    "start": datetime.fromisoformat(start_str),
                    "end": datetime.fromisoformat(end_str),
                }

                # Update overall boundaries
                time_bounds["earliest"] = min(
                    time_bounds["earliest"], timespan["start"]
                )
                time_bounds["latest"] = max(time_bounds["latest"], timespan["end"])

        return TimeFrame(
            start_time=time_bounds["earliest"], latest_time=time_bounds["latest"]
        )
