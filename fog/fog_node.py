import json
import logging
import os
import time
import threading

import paho.mqtt.client as mqtt
import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [FOG] %(message)s"
)

# ── CONFIG ───────────────────────────────────────────────
BROKER_HOST     = os.getenv("BROKER_HOST", "127.0.0.1")
BROKER_PORT     = int(os.getenv("BROKER_PORT", "1883"))
FOG_NODE_ID     = os.getenv("FOG_NODE_ID", "FOG-NODE-A")

CLOUD_ENDPOINT  = os.getenv(
    "CLOUD_ENDPOINT",
    "https://47f3soki74.execute-api.eu-north-1.amazonaws.com/Prod/ingest"
)

CLOUD_API_KEY   = os.getenv(
    "CLOUD_API_KEY",
    "j3jaKPHvif5LXfbpek2XF3tMqRyVVfkK7FRBdHn7"
)

# ✅ OPTIMIZED SETTINGS
BATCH_SIZE      = 10
BATCH_TIMEOUT_S = 25.0

SUBSCRIBE_TOPICS = [
    "traffic/vehicle_count",
    "traffic/speed",
    "traffic/light_status",
    "traffic/air_quality",
    "traffic/pedestrian",
]

# ── BUFFER ───────────────────────────────────────────────
batch_lock    = threading.Lock()
pending_batch = []
last_flush    = time.time()


# ── ANOMALY DETECTION ────────────────────────────────────
def detect_anomaly(reading):
    stype = reading.get("sensor_type", "")
    data  = reading.get("data", {})

    if stype == "SpeedRadarSensor" and data.get("max_speed_kmh", 0) > 100:
        return f"HIGH_SPEED:{data['max_speed_kmh']}kmh"

    if stype == "AirQualitySensor" and data.get("pm25_ugm3", 0) > 55:
        return f"HIGH_PM25:{data['pm25_ugm3']}"

    if stype == "VehicleCounterSensor" and data.get("vehicle_count", 0) > 45:
        return f"CONGESTION:{data['vehicle_count']} vehicles"

    return None


#DISPATCH
def dispatch(batch):
    payload = {
        "fog_node": FOG_NODE_ID,
        "batch_size": len(batch),
        "readings": batch
    }

    headers = {
        "Content-Type": "application/json",
        "x-api-key": CLOUD_API_KEY
    }

    try:
        time.sleep(5)

        resp = requests.post(
            CLOUD_ENDPOINT,
            json=payload,
            headers=headers,
            timeout=10
        )

        if resp.status_code == 429:
            logging.warning("🚨 RATE LIMITED → waiting 30 seconds...")
            time.sleep(30)
            return False

        resp.raise_for_status()
        logging.info(f"✅ Dispatched {len(batch)} readings → HTTP {resp.status_code}")
        return True

    except requests.exceptions.RequestException as exc:
        logging.error(f"❌ Dispatch failed: {exc}")
        return False


#FLUSH LOOP
def flush_loop():
    global pending_batch, last_flush

    while True:
        time.sleep(0.5)

        with batch_lock:
            elapsed = time.time() - last_flush

            if len(pending_batch) >= BATCH_SIZE or (
                pending_batch and elapsed >= BATCH_TIMEOUT_S
            ):
                to_send = pending_batch[:]
                pending_batch = []
                last_flush = time.time()
            else:
                to_send = []

        if to_send:
            success = dispatch(to_send)

            if not success:
                logging.warning("Retrying after backoff...")
                time.sleep(15)

                with batch_lock:
                    pending_batch = to_send + pending_batch


# MQTT CALLBACKS
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        logging.info("Fog node connected to broker")

        for topic in SUBSCRIBE_TOPICS:
            client.subscribe(topic, qos=1)
            logging.info(f"Subscribed: {topic}")
    else:
        logging.error(f"Broker connection failed rc={rc}")


def on_message(client, userdata, msg):
    global pending_batch

    try:
        reading = json.loads(msg.payload.decode("utf-8"))

        reading["fog_node"] = FOG_NODE_ID
        reading["anomaly"]  = detect_anomaly(reading)
        reading["topic"]    = msg.topic

        with batch_lock:
            pending_batch.append(reading)

        if reading["anomaly"]:
            logging.warning(
                f"ANOMALY {reading['sensor_id']}: {reading['anomaly']}"
            )

    except Exception as exc:
        logging.error(f"Message parse error: {exc}")


def on_disconnect(client, userdata, rc):
    if rc != 0:
        logging.warning(f"Unexpected disconnect rc={rc} — reconnecting...")


#MAIN
if __name__ == "__main__":
    logging.info(f"=== Fog Node {FOG_NODE_ID} starting ===")

    flush_thread = threading.Thread(target=flush_loop, daemon=True)
    flush_thread.start()

    client = mqtt.Client(client_id=FOG_NODE_ID, protocol=mqtt.MQTTv311)

    client.on_connect    = on_connect
    client.on_message    = on_message
    client.on_disconnect = on_disconnect

    client.connect(BROKER_HOST, BROKER_PORT, keepalive=60)

    try:
        client.loop_forever()
    except KeyboardInterrupt:
        logging.info("Fog node stopped")
        client.disconnect()