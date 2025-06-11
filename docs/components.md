# Components

Components are building blocks of pipeline, they can be connected with each other inside the pipeline definition.

To learn how to use a component within a pipeline and connect different components with each other, see the tutorial.

## Harvester

The Harvester is a component which fetches data from the defined IoT data source and standardizes the data into a list of Items. The Wrench framework provides an interface `BaseHarvester` with an abstract method `return_items` which all Harvesters must implement.

We provide the following Harvesters with the framework:

* [SensorThingsHarvester](./API_reference/harvester.md#wrench.harvester.SensorThingsHarvester)

## Grouper

The Grouper classifies or groups data coming from the harvester and returns a set of Groups containing the list of items assigned to the groups. The Wrench framework provides an interface `BaseGrouper` with an abstract method `group_items` which all Groupers must implement.

We provide the following Groupers with the framework:

* [TELEClassGrouper](./API_reference/grouper.md#wrench.grouper.TELEClassGrouper)

## Metadata Enricher

The MetadataEnricher builds both spatial and temporal metadata for the list of items returned by the harvester and also the list of grouped items returned by the grouper. The Wrench framework provides an interface `BaseMetadataEnricher` with the abstract methods `build_service_metadata` and `build_group_metadata`.

`build_service_metadata` builds the CommonMetadata for the items returned by the harvester, providing metadata for the API service itself, `build_group_metadata` builds the CommonMetadata for each Group returned by the grouper and provides metadata for each group.

We provide the following metadata enrichers with the framework:

* [SensorThingsMetadataEnricher](./API_reference/MetadataEnricher.md#wrench.metadataenricher.SensorThingsMetadataEnricher)

> Note that the MetadataEnricher must always be connected to the same type of Harvester, since typically the data model for each harvester type is different, connecting a MetadataEnricher to a different type of Harvester will not work.

## Cataloger

The Cataloger is responsible for cataloging both the service and the group metadata returned by the Metadata Enricher and enriches the Catalog with useful metadata information about the source data being referenced. The Wrench framework provides an interface `BaseCataloger` with the abstract methods `register`, accepting both the service and group metadata as input and builds entries for each of the service and groups. Framework-specific features such as connecting entries should be implemented in this register function to maximize the discoverability of the entries in the catalog.

We provide the following Catalogers with the framework:

* [SDDICataloger](./API_reference/cataloger.md#wrench.cataloger.SDDICataloger)
