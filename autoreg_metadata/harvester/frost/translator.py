import requests

from .models import Thing
from autoreg_metadata.harvester.base import TranslationService


class FrostTranslationService(TranslationService):
    """
    FrostTranslationService takes in a LibreTranslate base URL endpoint and can translate incoming SensorThings API Thing Entity into English.

    Attributes:
        url (str): The base URL endpoint for the LibreTranslate API.
        source_lang (str): The source language of the text to be translated. Defaults to "auto" if not provided.
        headers (dict): The headers to be used in the API request.

    Methods:
        translate(translated_thing: Thing) -> Thing:
            Translates the given Thing entity into English, including its name, description, properties, and datastreams.

        translate_value(value):
            Recursively translates values that are strings, lists, or dictionaries.

        translate_text(text: str):
            Translates the input text from `source_lang` into English by calling the LibreTranslate API Endpoint.
    """
    """FrostTranslationService takes in a LibreTranslate base URL endpoint and can translate incoming SensorThings API Thing Entity into english"""

    def __init__(self, url: str, source_lang):
        self.url = url
        self.source_lang = "auto" if not source_lang else source_lang
        self.headers = {"Content-Type": "application/json"}

    def translate(self, translated_thing: Thing) -> Thing:
        """
        Translates the attributes of a Thing object, including its name, description,
        properties, and datastreams, into another language or format.

        Args:
            translated_thing (Thing): The Thing object to be translated.

        Returns:
            Thing: A new Thing object with translated attributes.
        """

        # translate thing
        translated_thing = translated_thing.model_copy(deep=True)

        translated_thing.name = self.translate_text(translated_thing.name)
        translated_thing.description = self.translate_text(
            translated_thing.description)

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
                        self.translate_value(
                            ds.properties) if ds.properties else None
                    ),
                    "sensor": updated_sensor,
                }
            )

            translated_thing.datastreams[idx] = updated_ds

        return translated_thing

    def translate_value(self, value):
        """
        Recursively translate values that are strings, lists, or dictionaries.

        Args:
            value (str, list, dict): The value to be translated. It can be a string,
                                     a list of values, or a dictionary with string keys
                                     and values of any type.

        Returns:
            The translated value. If the input is a string, it returns the translated string.
            If the input is a list, it returns a list with each item translated.
            If the input is a dictionary, it returns a dictionary with translated keys and values.
            If the input is of any other type, it returns the input value unchanged.
        """
        """Recursively translate values that are strings or lists"""
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
        Translates the input text into English by calling the LibreTranslate API Endpoint.

        Args:
            text (str): The text to be translated.

        Returns:
            str: The translated text in English.

        Raises:
            requests.exceptions.RequestException: If there is an issue with the API request.
        """
        """Translates the input text into english by calling the LibreTranslate API Endpoint"""
        payload = {"q": text, "source": self.source_lang, "target": "en"}

        response = requests.post(
            f"{self.url}/translate", json=payload, headers=self.headers, timeout=60
        )
        return response.json()["translatedText"]
