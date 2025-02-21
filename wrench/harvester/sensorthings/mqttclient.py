import paho.mqtt.client as mqtt

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)


def on_connect(client, userdata, flags, reason_code, properties):
    """
    Callback function for when the client receives a CONNACK response from the server.

    This function is called when the client successfully connects to the MQTT broker.
    It prints the connection result code and subscribes to the "$SYS/#" topic.

    Args:
        client (paho.mqtt.client.Client): The client instance for this callback.
        userdata (any): The private user data as set in Client() or userdata_set().
        flags (dict): Response flags sent by the broker.
        reason_code (int): The connection result code.
        properties (paho.mqtt.properties.Properties): The properties associated with the connection.
    """
    print(f"Connected with result code {reason_code}")
    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
    client.subscribe("$SYS/#")


# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
    """
    Callback function that is called when a message is received from the MQTT broker.

    Args:
        client (paho.mqtt.client.Client): The client instance for this callback.
        userdata (any): The private user data as set in Client() or userdata_set().
        msg (paho.mqtt.client.MQTTMessage): An instance of MQTTMessage,
                    which contains the topic and payload of the received message.

    Returns:
        None
    """
    print(msg.topic + " " + str(msg.payload))


client.on_connect = on_connect

client.on_message = on_message

client.connect()

client.loop_forever()
