from typing import Sequence

from ckanapi import RemoteCKAN

from wrench.cataloger.base import BaseCataloger
from wrench.models import CommonMetadata

from .models import DeviceGroup, OnlineService

DEFAULT_OWNER = "lehrstuhl-fur-geoinformatik"


class SDDICataloger(BaseCataloger):
    """
    SDDICataloger is a class responsible for interacting with a SDDI CKAN server to register and manage datasets.

    :param url: The URL of the SDDI CKAN server.
    :param api_key: The API key for authenticating with the SDDI CKAN server.
    """

    def __init__(
        self,
        base_url: str,
        api_key: str,
        owner_org: str = "lehrstuhl-fur-geoinformatik",
    ):
        """
        Initialize the register with the given configuration.

        Args:
            base_url (str): Base URL of the SDDI catalog to register to.
            api_key (str): API Key for registration authorization.
            owner_org (str): Owner organization to which the dataset will belong to.

        Raises:
            ValueError: If the provided configuration path is invalid or the
            configuration file cannot be loaded.

        """
        super().__init__(endpoint=base_url, api_key=api_key)

        self.ckan_server = RemoteCKAN(address=self.endpoint, apikey=self.api_key)
        self.owner_org = owner_org

    def register(self, service: CommonMetadata, groups: Sequence[CommonMetadata]):
        online_service = self._create_online_service(service)
        device_groups = self._create_device_groups(groups)

        try:
            self._register_api_service(online_service)

            self.logger.info("Successfully registered API Service")

            if groups:
                self._register_device_groups(device_groups)
                for d in device_groups:
                    self.logger.info(
                        "Creating relationships for device_group %s", d.name
                    )
                    self._register_relationship(
                        api_service_name=online_service.name,
                        device_group_name=d.name,
                    )

        except Exception as e:
            self.logger.error("Failed to register: %s", e)
            raise

    def _register_api_service(self, api_service: OnlineService):
        pkg = self.ckan_server.call_action(
            action="package_create", data_dict=api_service.model_dump()
        )
        return pkg

    def _register_device_groups(self, device_groups: list[DeviceGroup]):
        for device_group in device_groups:
            pkg = self.ckan_server.call_action(
                action="package_create",
                data_dict=device_group.model_dump(),
            )

        return pkg

    def _register_relationship(self, api_service_name: str, device_group_name: str):
        rel = self.ckan_server.call_action(
            action="package_relationship_create",
            data_dict={
                "subject": device_group_name,
                "object": api_service_name,
                "type": "links_to",
            },
        )
        return rel

    def delete_resource(self, dataset_name: str):
        self.ckan_server.call_action(
            action="dataset_purge", data_dict={"id": dataset_name}
        )
        self.logger.info("successfully deleted resource")

    def get_owner_orgs(self) -> list[str]:
        return self.ckan_server.call_action(
            action="organization_list",
        )

    def _create_online_service(self, metadata: CommonMetadata) -> OnlineService:
        return OnlineService(
            url=metadata.endpoint_url,
            name=metadata.identifier,
            notes=metadata.description,
            owner_org=metadata.owner or DEFAULT_OWNER,
            title=metadata.title,
            tags=[{"name": tag for tag in metadata.tags}],
            spatial=metadata.spatial_extent,
        )

    def _create_device_groups(
        self, metadata: Sequence[CommonMetadata]
    ) -> list[DeviceGroup]:
        DOMAIN_GROUPS = [
            "administration",
            "mobility",
            "environment",
            "agriculture",
            "urban-planning",
            "health",
            "energy",
            "information-technology",
            "tourism",
            "living",
            "education",
            "construction",
            "culture",
            "trade",
            "craft",
            "work",
        ]

        device_groups: list[DeviceGroup] = []

        for group in metadata:
            device_group = DeviceGroup(
                url=group.endpoint_url,
                name=group.identifier,
                notes=group.description,
                owner_org=group.owner or DEFAULT_OWNER,
                title=group.title,
                tags=[{"name": tag} for tag in group.tags],
                spatial=group.spatial_extent,
                resources=[
                    {
                        "name": f"URL for {group.title}",
                        "description": f"URL provides a list of all data associated "
                        f"with the category {group.title}",
                        "format": "JSON",
                        "url": group.endpoint_url,
                    }
                ],
            )
            device_group.groups.extend(
                [
                    {"name": domain}
                    for domain in group.thematic_groups
                    if domain in DOMAIN_GROUPS
                ]
            )
            device_groups.append(device_group)

        return device_groups
