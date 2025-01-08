import requests

from models import Thing


class FrostTranslationService:
    """FrostTranslationService takes in a LibreTranslate base URL endpoint and can translate incoming SensorThings API Thing Entity into english"""

    def __init__(self, url: str, source_lang):
        self.url = url
        self.source_lang = "auto" if not source_lang else source_lang
        self.headers = {"Content-Type": "application/json"}

    def translate(self, translated_thing: Thing) -> Thing:

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
        """Translates the input text into english by calling the LibreTranslate API Endpoint"""
        payload = {"q": text, "source": self.source_lang, "target": "en"}

        response = requests.post(
            f"{self.url}/translate", json=payload, headers=self.headers, timeout=60
        )
        return response.json()["translatedText"]
