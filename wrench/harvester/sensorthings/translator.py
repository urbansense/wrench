import requests

from wrench.harvester.base import TranslationService
from wrench.log import logger

from .models import Thing


class LibreTranslateService(TranslationService):
    """
    LibreTranslateService translates SensorThings API Thing Entity into English.

    Attributes:
        url (str): Base URL for the LibreTranslate API.
        source_lang (str): Source language of the text. Defaults to "auto".
        headers (dict): Headers for the API request.

    Methods:
        translate(translated_thing: Thing) -> Thing:
            Translates the given Thing entity into English.

        translate_value(value):
            Recursively translates values that are strings, lists, or dicts.

        translate_text(text: str):
            Translates text from `source_lang` into English using the API.
    """

    def __init__(self, url: str, source_lang):
        """
        Initializes the Translator object with the given URL and source language.

        Args:
            url (str): The URL to be used for translation.
            source_lang (str): The source language for translation.
                               If not provided, defaults to "auto".

        Attributes:
            url (str): The URL to be used for translation.
            source_lang (str): The source language for translation.
            headers (dict): The headers to be used for HTTP requests.
            logger (Logger): The logger instance for this class.
        """
        self.url = url
        self.source_lang = "auto" if not source_lang else source_lang
        self.headers = {"Content-Type": "application/json"}
        self.logger = logger.getChild(self.__class__.__name__)

    def translate[T: Thing](self, translated_thing: T) -> T:
        """
        Translates the attributes of a Thing object.

        Includes its name, description, properties,
        and datastreams, into another language or format.

        Args:
            translated_thing (Thing): The Thing object to be translated.

        Returns:
            Thing: A new Thing object with translated attributes.
        """
        # translate thing
        translated_thing = translated_thing.model_copy(deep=True)

        self.logger.debug("Starting translation for: %s", translated_thing.name)

        translated_thing.name = self.translate_text(translated_thing.name)
        translated_thing.description = self.translate_text(translated_thing.description)

        if translated_thing.properties:
            translated_props = {}
            for k, v in translated_thing.properties.items():
                translated_key = self.translate_text(k)
                translated_value = self.translate_value(v)
                translated_props[translated_key] = translated_value

            translated_thing.properties = translated_props

        # translate each datastream of thing
        for idx, ds in enumerate(translated_thing.datastreams):
            # translate sensors
            updated_sensor = ds.sensor.model_copy(
                update={
                    "name": self.translate_text(ds.sensor.name),
                    "description": self.translate_text(ds.sensor.description),
                    # other sensor fields to update
                }
            )
            updated_ds = ds.model_copy(
                update={
                    "name": self.translate_text(ds.name),
                    "description": self.translate_text(ds.description),
                    "unitOfMeasurement": self.translate_value(ds.unit_of_measurement),
                    "properties": (
                        self.translate_value(ds.properties) if ds.properties else None
                    ),
                    "sensor": updated_sensor,
                }
            )

            translated_thing.datastreams[idx] = updated_ds

        return translated_thing

    def translate_value(self, value):
        """
        Recursively translate values that are strings, lists, or dicts.

        Args:
            value (str, list, dict): The value to be translated.

        Returns:
            The translated value. If the input is a string, it returns
            the translated string. If the input is a list, it returns
            a list with each item translated. If the input is a dict,
            it returns a dict with translated keys and values.If the
            input is of any other type, it returns the input value unchanged.
        """
        if isinstance(value, str):
            return self.translate_text(value)
        elif isinstance(value, list):
            return [self.translate_value(item) for item in value]
        elif isinstance(value, dict):
            return {
                self.translate_text(k): self.translate_value(v)
                for k, v in value.items()
            }
        return value

    def translate_text(self, text: str):
        """
        Translates text into English with the LibreTranslate API.

        Args:
            text (str): The text to be translated.

        Returns:
            str: The translated text in English.

        Raises:
            requests.exceptions.RequestException:
            If there is an issue with the API request.
        """
        payload = {"q": text, "source": self.source_lang, "target": "en"}

        response = requests.post(
            f"{self.url}/translate", json=payload, headers=self.headers, timeout=60
        )
        return response.json()["translatedText"]
