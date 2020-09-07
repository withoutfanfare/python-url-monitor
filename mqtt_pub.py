import paho.mqtt.client as mqtt
import json
import logging

logging.basicConfig(filename='/tmp/debug.log', level=logging.DEBUG)

class pub:
    def __init__(self,MQTT_BROKER,MQTT_PORT,MQTT_KEEPALIVE_INTERVAL,MQTT_TOPIC,transport = ''):
        self.MQTT_TOPIC = MQTT_TOPIC
        self.MQTT_BROKER =MQTT_BROKER
        self.MQTT_PORT = MQTT_PORT
        self.MQTT_KEEPALIVE_INTERVAL = MQTT_KEEPALIVE_INTERVAL

        # Initiate MQTT Client
        if transport == 'websockets':
            self.mqttc = mqtt.Client(transport='websockets')
        else:
            self.mqttc = mqtt.Client()

        # Register Event Handlers
        self.mqttc.on_publish = self.on_publish
        self.mqttc.on_connect = self.on_connect

        self.connect()

    # Define on_connect event Handler
    def on_connect(self,mosq, obj, rc):
        logging.info("Connected")

    # Define on_publish event Handler
    def on_publish(self,client, userdata, mid):
        logging.info("Published")

    def publish(self,MQTT_MSG):
        # MQTT_MSG = json.dumps(MQTT_MSG)
        self.mqttc.publish(self.MQTT_TOPIC,MQTT_MSG)

    # Connect from MQTT_Broker
    def connect(self):
        self.mqttc.connect(self.MQTT_BROKER, self.MQTT_PORT, self.MQTT_KEEPALIVE_INTERVAL)

    # Disconnect from MQTT_Broker
    def disconnect(self):
        self.mqttc.disconnect()
