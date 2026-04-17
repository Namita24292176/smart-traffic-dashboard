# Smart Traffic Dashboard
SMART TRAFFIC MONITORING SYSTEM
Fog–Edge–Cloud IoT Architecture

---

1. PROJECT OVERVIEW

---

This project implements a Smart Traffic Monitoring System using a Fog–Edge–Cloud architecture. It simulates multiple IoT sensors, processes data locally at the edge and fog layers, and sends batched data to an AWS cloud backend for storage and visualization.

---

2. PREREQUISITES

---

Before installation, ensure the following are installed:

* Python 3.10+
* Docker
* AWS CLI (configured with credentials)
* Git

---

3. PROJECT STRUCTURE

---

edge/        → Sensor simulation and edge device
fog/         → Fog node processing
broker/      → Mosquitto configuration
cloud/       → AWS Lambda functions
templates/   → Frontend HTML
application.py → Flask dashboard

---

4. INSTALLATION STEPS

---

## STEP 1: Clone Repository

git clone https://github.com/Namita24292176/smart-traffic-dashboard.git

## STEP 2: Create Virtual Environment

python -m venv venv
source venv/bin/activate

## STEP 3: Install Dependencies

pip install -r requirements.txt

---

5. RUN MQTT BROKER (Mosquitto)

---

## STEP 4: Start Broker using Docker

cd broker
docker run -it -p 1883:1883 eclipse-mosquitto

---

6. RUN EDGE DEVICE (SENSORS)

---

## STEP 5: Start Edge Device

cd edge
python edge_device.py

This will:

* Start 5 sensor threads
* Publish data to MQTT topics

---

7. RUN FOG NODE

---

## STEP 6: Start Fog Node

cd fog
python fog_node.py

This will:

* Subscribe to all MQTT topics
* Perform anomaly detection
* Batch data
* Send HTTPS requests to AWS

---

8. RUN DASHBOARD

---

## STEP 7: Start Flask Dashboard

python application.py

Dashboard Features:

* Real-time sensor visualization
* Anomaly display

---

9. DATA FLOW SUMMARY

---

Sensors → Edge Device → MQTT Broker → Fog Node → AWS Cloud → DynamoDB → Dashboard

---

10. NOTES

---

* Ensure AWS credentials are configured
* MQTT broker must be running before edge/fog nodes
* Internet connection required for cloud communication

---

## END OF README
