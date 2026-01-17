"""Example: Creating custom ground truth with advanced rules."""

from tools.core.ground_truth import GroundTruthBuilder
from wrench.harvester.sensorthings import SensorThingsHarvester

# Initialize
harvester = SensorThingsHarvester(base_url="https://daten-api.osnabrueck.de/v1.1")
builder = GroundTruthBuilder(harvester)

# Fetch devices
devices = builder.fetch_devices()

# 1. Simple keyword matching (default field='keywords')
builder.add_keyword_rule("Parking", ["Parkplatz"])

# 2. Check different property field
builder.add_keyword_rule("Traffic Counting", ["Verkehrszaehlung"], field="topic")


# 3. Custom rule with complex logic
def has_multiple_sensors(device):
    """Devices with more than 2 sensors."""
    return len(device.sensors) > 2


builder.add_rule("Multi-Sensor Devices", has_multiple_sensors)


# 4. Custom rule combining multiple conditions
def is_weather_station(device):
    """Check if device is a weather station based on properties and sensors."""
    if not device.properties:
        return False

    # Check keywords
    if "keywords" in device.properties:
        keywords = device.properties["keywords"]
        if isinstance(keywords, str):
            keywords = [keywords]
        if "Wetter" in keywords or "Weather" in keywords:
            return True

    # Check sensor types
    sensor_names = [s.name.lower() for s in device.sensors]
    weather_indicators = ["temperature", "humidity", "pressure", "wind"]
    return any(indicator in " ".join(sensor_names) for indicator in weather_indicators)


builder.add_rule("Weather Stations", is_weather_station)


# 5. Custom rule checking observed properties
def monitors_temperature(device):
    """Devices that monitor temperature."""
    obs_props = [op.name.lower() for op in device.observed_properties]
    return any("temp" in prop or "celsius" in prop for prop in obs_props)


builder.add_rule("Temperature Monitoring", monitors_temperature)


# 6. Custom rule based on location
def in_city_center(device):
    """Devices located in city center (example coordinates)."""
    if not device.locations:
        return False

    # Example: check if within bounding box
    lat = device.locations[0].geometry.coordinates[1]
    lon = device.locations[0].geometry.coordinates[0]

    # Osnabrück city center approximate bounds
    return (52.27 <= lat <= 52.29) and (8.04 <= lon <= 8.06)


builder.add_rule("City Center Devices", in_city_center)

# Get statistics
stats = builder.get_statistics()
print(f"Total devices: {stats['total_devices']}")
print(f"Assigned: {stats['assigned_devices']}")
print(f"Unassigned: {stats['unassigned_devices']}")
print("\nCategories:")
for cat, count in stats["category_distribution"].items():
    print(f"  {cat}: {count}")

# Save
builder.save("custom_ground_truth.json")
