import logging
from datetime import datetime, timezone
import time
from typing import Callable, List, Optional, Tuple

import requests

from autoreg_metadata.pipeline.models import Coordinate, EnrichedMetadata, TimeFrame

from .models import Location, Thing, GenericLocation
from .translator import FrostTranslationService

HarvesterOption = Callable[['FrostHarvester'], None]


class FrostHarvester:
    """
    A class to interact with the FROST server and retrieve 'Things' and their associated 'Datastreams' and 'Sensor'.

    Args:
        base_url: The base URL of the FROST server.
        translator: Optional translation service for converting content to English.
        options: Configuration options for the harvester.
    """

    def __init__(
        self,
        base_url: str,
        *options: HarvesterOption
    ):
        self.base_url = base_url.rstrip("/")
        self.translator: Optional[FrostTranslationService] = None
        self.custom_location_model: GenericLocation = None
        self.logger = logging.getLogger(__name__)

        # Apply any configuration options
        for option in options:
            option(self)

    def enrich(self) -> Tuple[EnrichedMetadata, List[Thing]]:
        # fetch all things
        things = self.fetch_things(limit=5)
        return EnrichedMetadata(
            geographical_extent=self._get_geographic_extent(limit=5),
            timeframe=self._get_timeframe(things),
        ), things

    def fetch_things(self, limit: int = -1) -> List[Thing]:
        """
        Fetches Things along with their Datastreams and Sensors from the FROST server.
        Translates the content if a translator is configured.

        Args:
            limit: The maximum number of Things to fetch. Default is -1 (no limit).

        Returns:
            A list of Thing objects with their associated Datastreams.
        """
        try:
            url = f"{self.base_url}/Things?$expand=Datastreams($expand=Sensor)"

            return self._paginate_data(
                url=url,
                model_class=Thing,
                limit=limit,
                fn=self._process_things,
            )

        except requests.RequestException as e:
            self.logger.error("Error fetching Things: %s", e)
            return []

    def _process_things(self, things: List[Thing]) -> List[Thing]:
        """
        Process the list of things, applying translation if configured.

        Args:
            things: List of Thing objects to process

        Returns:
            Processed (and potentially translated) list of Thing objects
        """
        if not self.translator:
            return things

        self.logger.info("Translating %d things", len(things))
        translated_things = []

        for thing in things:
            try:
                translated_thing = self.translator.translate(thing)
                translated_things.append(translated_thing)
            except Exception as e:
                self.logger.error(
                    "Translation failed for thing %s: %s", thing.id, e)
                # Fall back to untranslated version
                translated_things.append(thing)

        return translated_things

    def _get_geographic_extent(self, limit=-1) -> Tuple[Coordinate, Coordinate]:
        min_lat = float('inf')
        max_lat = float('-inf')
        min_lng = float('inf')
        max_lng = float('-inf')

        model_class = self.custom_location_model if self.custom_location_model else Location

        try:
            url = f"{self.base_url}/Locations"

            locations = self._paginate_data(
                url=url,
                model_class=model_class,
                limit=limit
            )

            for loc in locations:
                lng, lat = loc.get_coordinates()
                min_lat = min(min_lat, lat)
                max_lat = max(max_lat, lat)
                min_lng = min(min_lng, lng)
                max_lng = max(max_lng, lng)

            return Coordinate(longitude=min_lng, latitude=min_lat), Coordinate(longitude=max_lng, latitude=max_lat)

        except requests.RequestException as e:
            self.logger.error("Error fetching locations: %s", e)

    def _get_timeframe(self, things: List[Thing]) -> Tuple[datetime, datetime]:
        earliest = datetime.max.replace(tzinfo=timezone.utc)
        latest = datetime.min.replace(tzinfo=timezone.utc)

        for thing in things:
            for ds in thing.datastreams:
                if ds.phenomenon_time:
                    timestamps = ds.phenomenon_time.split('/')
                    start = datetime.fromisoformat(timestamps[0])
                    end = datetime.fromisoformat(timestamps[1])
                    if earliest > start:
                        earliest = start
                    if latest < end:
                        latest = end

        return TimeFrame(start_time=earliest, latest_time=latest)

    def _paginate_data[T](
        self,
        url: str,
        model_class: type[T],
        limit: int = 5,
        fn: Optional[Callable[[List[T]], List[T]]] = None
    ) -> List[T]:
        """
        Paginate through data from a given URL and return a list of items of type T.

        Args:
            url (str): The initial URL to fetch data from.
            model_class (type[T]): The class type to which each item in the response should be validated.
            limit (int, optional): The maximum number of items to return. Defaults to 5. Use -1 for no limit.
            fn (Optional[Callable[[List[T]], List[T]]], optional): An optional function to process the list of items before returning. Defaults to None.

        Returns:
            List[T]: A list of items of type T.
        """
        page_count = 1
        items: List[T] = []
        # as long as @iot.nextLink still exists, run the loop
        while url:
            self.logger.info("Fetching page %s", page_count)

            response = requests.get(url, timeout=60)
            response.raise_for_status()

            data = response.json()
            if "value" in data:
                for _, value in enumerate(data["value"]):
                    # if limit is set, and length of items exceed limit, return early and avoid more pagination
                    if limit != -1 and len(items) >= limit:
                        return fn(items) if fn else items

                    item = model_class.model_validate(value)
                    items.append(item)

                page_count += 1
                self.logger.debug(
                    f"Added {len(data['value'])} items from page {page_count}"
                )
            # reset url to be the url in @iot.nextLink
            url = data.get("@iot.nextLink")
            if url:
                # sleep to prevent overloading the endpoint
                time.sleep(0.1)
        return fn(items) if fn else items


# Optional configuration functions with functional option pattern

def with_translator(url: str, source_lang: Optional[str] = None) -> HarvesterOption:
    """
    Configuration option to add a translator to the harvester.

    Args:
        url: The URL of the translation service
        source_lang: The source language to be translated from

    Returns:
        A configuration function that can be passed to FrostHarvester
    """
    def configure(harvester: FrostHarvester) -> None:
        harvester.translator = FrostTranslationService(url, source_lang)

    return configure


def with_location_model(location: GenericLocation) -> HarvesterOption:
    """
    Configuration option to pass in a custom Location data model for Location resources.

    Args:
        model: a model which inherits from GenericLocation

    Returns:
        A configuration function that can be passed to FrostHarvester
    """

    def configure(harvester: FrostHarvester) -> None:
        harvester.custom_location_model = location

    return configure
