import logging
import time
from typing import List, Optional, Callable, Tuple
import requests

from models import Thing, Location
from translator import FrostTranslationService

from pipeline.models import EnrichedMetadata, Coordinate

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
        self.logger = logging.getLogger(__name__)

        # Apply any configuration options
        for option in options:
            option(self)

    def fetch(self, limit: int = -1) -> List[Thing]:
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
                url,
                limit,
                Thing,
                self._process_things,
            )

        except requests.RequestException as e:
            self.logger.error("Error fetching Things: %s", e)
            return []

    def enrich(self, em: EnrichedMetadata) -> EnrichedMetadata:
        return EnrichedMetadata(
            geographical_extent=self._get_geographic_extent())

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

    def _get_geographic_extent(self) -> Tuple[Coordinate, Coordinate]:
        min_lat = float('inf')
        max_lat = float('-inf')
        min_lng = float('inf')
        max_lng = float('-inf')
        try:
            url = f"{self.base_url}/Locations"

            locations = self._paginate_data(
                url=url,
                model_class=Location,
            )

            for loc in locations:
                lng, lat = loc.location.coordinates
                min_lat = min(min_lat, lat)
                max_lat = max(max_lat, lat)
                min_lng = min(min_lng, lng)
                max_lng = max(max_lng, lng)

            return Coordinate(min_lng, min_lat), Coordinate(max_lng, max_lat)

        except requests.RequestException as e:
            self.logger.error("Error fetching locations: %s", e)

    def _paginate_data[T](
        self,
        url: str,
        model_class: type[T],
        limit: int = 5,
        fn: Optional[Callable[[List[T]], List[T]]] = None
    ) -> List[T]:
        page_count = 1
        items: List[T] = []
        while url:
            self.logger.info("Fetching page %s", page_count)

            response = requests.get(url, timeout=60)
            response.raise_for_status()

            data = response.json()
            if "value" in data:
                for _, value in enumerate(data["value"]):
                    if limit != -1 and len(items) >= limit:
                        return fn(items) if fn else items

                    item = model_class.model_validate(value)
                    items.append(item)

                page_count += 1
                self.logger.debug(
                    f"Added {len(data['value'])} items from page {page_count}"
                )

            url = data.get("@iot.nextLink")
            if url:
                time.sleep(0.1)
        return fn(items) if fn else items


# Optional configuration functions


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


if __name__ == "__main__":

    harvester = FrostHarvester(
        "https://iot.hamburg.de/v1.1",
        with_translator("http://10.162.246.107:5000"))

    em = EnrichedMetadata()

    em = harvester.enrich(em)
    print(em.geographical_extent)
