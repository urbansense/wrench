from .models import APIService, DeviceGroup

import autoreg_metadata.catalogger.ckan.utils as ckanutils
from autoreg_metadata.log import logger
from autoreg_metadata.catalogger.base import BaseCatalogger
from autoreg_metadata.common.models import CommonMetadata

from ckanapi import RemoteCKAN


class CKANCatalogger(BaseCatalogger):
    """
    CKANCatalogger is a class responsible for interacting with a CKAN server to register and manage datasets.

    :param url: The URL of the CKAN server.
    :param api_key: The API key for authenticating with the CKAN server.
    """

    def __init__(self, url: str, api_key=str):
        super().__init__(endpoint=url, api_key=api_key)
        self.ckan_server = RemoteCKAN(
            address=self.endpoint, apikey=self.api_key)
        self.logger = logger.getChild(self.__class__.__name__)

    def register(self, metadata: CommonMetadata, data: dict[str, list]):
        try:
            api_service = ckanutils.create_api_service(metadata)
            self._register_api_service(api_service)

            if data:
                self._register_device_groups(api_service, data)

        except Exception as e:
            self.logger.error("Failed to register API Servce: %s", e)
            raise

    def _register_api_service(self, api_service: APIService):
        pkg = self.ckan_server.call_action(
            action='package_create',
            data_dict=api_service.model_dump()
        )
        print(pkg)
        return pkg

    def _register_device_groups(self, api_service: APIService, data: dict[str, list]):

        device_groups = []
        for key, _ in data.items():
            # Create base device group from API service
            device_group = DeviceGroup.from_api_service(api_service)

            # Update with device-specific fields
            device_group.name = key
            device_group.relationships_as_subject = [{
                "subject": key,
                "object": api_service.name,
                "type": "links_to"
            }]
            device_groups.append(device_group)

        for device in device_groups:
            pkg = self.ckan_server.call_action(
                action='package_create',
                data_dict=device
            )
            print(pkg)

    def delete_resource(self, dataset_name: str):
        self.ckan_server.call_action(
            action='dataset_purge',
            data_dict={
                "id": dataset_name
            }
        )
        print("successfully deleted resource")

    def get_owner_orgs(self) -> list[str]:
        return self.ckan_server.call_action(
            action='organization_list',
        )
