# Sensor Registration Pipeline

### Architecture

The sensor registration pipeline is a full-fledged registration pipeline for ingesting and extracting metadata out of sensor data providers. The main purpose of this pipeline is to discover what kind of sensors exist in a sensor data provider, and group them accordingly before registering the provider information, enriched with extracted metadata into the final metadata catalog. It requires some components to be defined:

* [Harvester](../components.md#harvester)
* [Grouper](../components.md#grouper)
* [MetadataEnricher](../components.md#metadata-enricher)
* [Cataloger](../components.md#cataloger)

![sensor pipeline](../_static/sensor_pipeline_dark.png#only-dark)
![sensor pipeline](../_static/sensor_pipeline.png#only-light)

The components are interfaces which all concrete implementations must follow. This makes pipeline flexible to any kind of input and output targets, as long as implementations for these targets are defined in the framework. You can also add additional implementations by creating your own custom harvester/grouper/cataloger or even contribute your custom implementation to our repository.

The [SensorRegistrationPipeline](../API_reference/pipeline.md#wrench.pipeline.SensorRegistrationPipeline) accepts a [scheduler config](../scheduler.md) as an argument which when provided, will schedule pipeline runs continuously with the specified time intervals. The scheduling mechanism is best paired with state-aware components, which can detect changes between scheduled runs and update the final catalog entry according to the changes made.

### Example

Here's a full example on how you can use the SensorRegistrationPipeline.

Example:
```python
async def run_pipeline():
    """Tests pipeline."""
    # create a GeneratorConfig to use with MetadataEnricher
    generator_config = GeneratorConfig(llm_host="your_llm_host", model="your_model")

    # create a SensorThingsHarvester
    harvester = SensorThingsHarvester(base_url="https://sensorthingsapiservice.com/v1.1")

    # create a TELEClassGrouper
    grouper = TELEClassGrouper(config="./teleclass_config.yaml")

    # create a SensorThingsMetadataEnricher
    metadataenricher = SensorThingsMetadataEnricher(
        base_url="https://iot.hamburg.de/v1.1",
        title="Hamburg FROST Server",
        description="City of Hamburg FROST Server containing data collected from urban sensors around the city.",
        generator_config=generator_config,
    )

    # create an SDDICataloger
    cataloger = SDDICataloger(
        base_url="{your SDDI cataloger URL here}", api_key=os.getenv("CKAN_API_TOKEN")
    )

    # build the pipeline with a scheduler
    pipeline = SensorRegistrationPipeline(
        harvester=harvester,
        grouper=grouper,
        metadataenricher=metadataenricher,
        cataloger=cataloger,
        scheduler_config=SchedulerConfig(
            type={"scheduler_type": "cron", "cron_expression": "*/3 * * * *"} # run the pipeline every 3rd minute of the hour
        ),
    )

    result = await pipeline.run_async()

    return result
```

You can also define the pipeline from a configuration file such as YAML.

```yaml
# pipeline_config.yaml
template_: SensorPipeline
harvester_config:
  class_: sensorthings.SensorThingsHarvester
  params_:
    base_url: "https://sensorthingsapiservice/v1.1"
    pagination_config:
      page_delay: 0.1
      timeout: 30
      batch_size: 120
    translator_config:
      translator_type: libre_translate # for now, only supports libre_translate, more to come
      url: "http://your_libretranslate_endpoint/"
      source_lang: "de"
grouper_config:
  class_: teleclass.TELEClassGrouper
  params_:
    config: "./teleclass_config.yaml"
metadataenricher_config:
  class_: sensorthings.SensorThingsMetadataEnricher
  params_:
    base_url: "https://iot.hamburg.de/v1.1"
    title: "Hamburg FROST Server"
    description: "City of Hamburg FROST Server containing data collected from urban sensors around the city."
    generator_config:
      llm_host: "your_ollama_host_endpoint"
      model: "llama3.3:70b-instruct-q4_K_M"
cataloger_config:
  class_: sddi.SDDICataloger
  params_:
    base_url: "your_sddi_catalog_endpoint"
    api_key: ${CKAN_API_TOKEN}

```

and you can also schedule it by creating an instance of scheduler and passing in the runner to the scheduler

```python
pipeline_runner = PipelineRunner.from_config_file(
    ".//pipeline_config.yaml"
)

config = IntervalSchedulerConfig(interval="PT10M")

scheduler = config.create_scheduler(pipeline_runner)

try:
    scheduler.start()
    await asyncio.Event().wait()
except (KeyboardInterrupt, SystemExit):
    scheduler.shutdown()
```
