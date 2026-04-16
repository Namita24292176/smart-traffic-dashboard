import threading
import time
import json
import logging
import paho.mqtt.client as mqtt

from sensors import (
    VehicleCounterSensor, SpeedRadarSensor,
    TrafficLightSensor, AirQualitySensor, PedestrianSensor
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [EDGE] %(message)s"
)

# Broker connection
BROKER_HOST = "127.0.0.1"
BROKER_PORT = 1883

# MQTT topic per sensor type
TOPIC_MAP = {
    "VehicleCounterSensor":  "traffic/vehicle_count",
    "SpeedRadarSensor":      "traffic/speed",
    "TrafficLightSensor":    "traffic/light_status",
    "AirQualitySensor":      "traffic/air_quality",
    "PedestrianSensor":      "traffic/pedestrian",
}

#Sensor configuration: change rate_seconds freely
SENSORS = [
    VehicleCounterSensor("VC-001", "O'Connell St", rate_seconds=5.0),
    SpeedRadarSensor("SR-001", "N11 KM12", rate_seconds=5.0),
    TrafficLightSensor("TL-001", "College Green", rate_seconds=5.0),
    AirQualitySensor("AQ-001", "Dame Street", rate_seconds=10.0),
    PedestrianSensor("PD-001", "Grafton Street", rate_seconds=5.0),
]

def sensor_loop(sensor, client):
    """Run one sensor forever, publishing on every tick."""
    topic = TOPIC_MAP[sensor.sensor_type]
    while True:
        try:
            msg = json.dumps(sensor.payload())
            result = client.publish(topic, msg, qos=1)
            result.wait_for_publish(timeout=5)
            logging.info(f"Published {sensor.sensor_id} → {topic}")
        except Exception as exc:
            logging.error(f"Publish error {sensor.sensor_id}: {exc}")
        time.sleep(sensor.rate)


def on_connect(client, userdata, flags, rc):
    codes = {0: "Connected", 1: "Bad protocol", 2: "Client ID rejected",
             3: "Server unavailable", 4: "Bad credentials", 5: "Not authorised"}
    logging.info(f"Broker: {codes.get(rc, f'Unknown rc={rc}')}")
    if rc != 0:
        raise ConnectionError(f"Cannot connect to broker: rc={rc}")


if __name__ == "__main__":
    client = mqtt.Client(client_id="edge-device-001", protocol=mqtt.MQTTv311)
    client.on_connect = on_connect
    client.connect(BROKER_HOST, BROKER_PORT, keepalive=60)
    client.loop_start()

    logging.info(f"Edge device starting — {len(SENSORS)} sensors")
    threads = []
    for s in SENSORS:
        t = threading.Thread(target=sensor_loop, args=(s, client), daemon=True)
        t.start()
        threads.append(t)
        logging.info(f"  Started {s.sensor_id} ({s.sensor_type}) @ {s.rate}s")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logging.info("Edge device stopped")
        client.loop_stop()
        client.disconnect()