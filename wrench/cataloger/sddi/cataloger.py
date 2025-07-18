from datetime import datetime

from ckanapi import RemoteCKAN
from ckanapi.errors import NotFound, ValidationError

from wrench.cataloger.base import BaseCataloger
from wrench.models import CommonMetadata

from .models import DeviceGroup, OnlineService

DEFAULT_OWNER = "lehrstuhl-fur-geoinformatik"


class SDDICataloger(BaseCataloger):
    """
    Interact with a SDDI CKAN server to register and manage datasets.

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
        self._registries = set()

    def register(
        self,
        service: CommonMetadata,
        groups: list[CommonMetadata],
        managed_entries: list[str] | None,
    ) -> list[str]:
        online_service = self._create_online_service(service)
        device_groups = self._create_device_groups(groups)
        if managed_entries:
            self._registries = set(managed_entries)

        try:
            if online_service.name in self._registries:
                self._update_api_service(online_service)
                self.logger.info("Successfully updated API Service")
            else:
                self._register_api_service(online_service)
                self.logger.info("Successfully registered API Service")
        except NotFound:
            self.logger.error(
                """No entries found for %s, please clear the .pipeline_store cache and
                    rerun the pipeline""",
                online_service.name,
            )
        except ValidationError as e:
            self.logger.error(
                "CKAN validation error for service %s: %s",
                online_service.name,
                str(e),
            )
            raise

        if groups:
            try:
                for d in device_groups:
                    self.logger.debug("Processing device group: %s", d.name)
                    try:
                        if d.name in self._registries:
                            self._update_device_group(d)
                            self.logger.debug(
                                "Successfully updated Device Group: %s", d.name
                            )
                        else:
                            self._register_device_group(d)
                            self.logger.debug(
                                "Successfully registered Device Group: %s", d.name
                            )
                            self._register_relationship(
                                api_service_name=online_service.name,
                                device_group_name=d.name,
                            )
                            self.logger.info(
                                "Created relationships for device_group %s", d.name
                            )
                    except ValidationError as e:
                        self.logger.error(
                            "CKAN validation error for device group %s: %s",
                            d.name,
                            str(e),
                        )
                        # Continue processing other groups instead of failing completely
                        continue
            except NotFound:
                self.logger.error(
                    """No entries found for %s, please clear the .pipeline_store cache
                        and rerun the pipeline""",
                    d.name,
                )

        return list(self._registries)

    def _get_package(self, package_id: str):
        pkg = self.ckan_server.call_action(
            action="package_show", data_dict={"id": package_id}
        )
        return pkg

    def _register_api_service(self, api_service: OnlineService):
        self._registries.add(api_service.name)
        pkg = self.ckan_server.call_action(
            action="package_create", data_dict=api_service.model_dump()
        )
        return pkg

    def _register_device_group(self, device_group: DeviceGroup):
        self._registries.add(device_group.name)
        pkg = self.ckan_server.call_action(
            action="package_create",
            data_dict=device_group.model_dump(),
        )
        return pkg

    def _update_api_service(self, api_service: OnlineService):
        pkg = self.ckan_server.call_action(
            action="package_patch",
            data_dict={**api_service.model_dump(), "id": api_service.name},
        )
        return pkg

    def _update_device_group(self, device_group: DeviceGroup):
        pkg = self.ckan_server.call_action(
            action="package_patch",
            data_dict={**device_group.model_dump(), "id": device_group.name},
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
            url=metadata.endpoint_urls[0],
            name=metadata.identifier,
            notes=metadata.description,
            owner_org=metadata.owner or DEFAULT_OWNER,
            title=metadata.title,
            tags=[{"name": tag for tag in metadata.tags}],
            spatial=metadata.spatial_extent,
        )

    def _create_device_groups(
        self, metadata: list[CommonMetadata]
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
            start_date, latest_date = "", ""

            if group.temporal_extent:
                start_date = group.temporal_extent.start_time.strftime("%Y-%m-%d")
                latest_date = group.temporal_extent.latest_time.strftime("%Y-%m-%d")

            if group.temporal_extent.latest_time.date() == datetime.today().date():
                latest_date = ""

            device_group = DeviceGroup(
                url=group.endpoint_urls[0],
                name=group.identifier,
                notes=group.description,
                owner_org=group.owner or DEFAULT_OWNER,
                begin_collection_date=start_date,
                end_collection_date=latest_date,
                title=group.title,
                tags=[{"name": tag} for tag in group.tags],
                spatial=group.spatial_extent,
                resources=[
                    {
                        "name": f"URL-{i} for {group.title}",
                        "description": f"URL provides data for group: {group.title}",
                        "format": "JSON",
                        "url": url,
                    }
                    for i, url in enumerate(group.endpoint_urls)
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
