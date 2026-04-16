from flask import Flask, render_template, jsonify
import boto3
from boto3.dynamodb.conditions import Key
from decimal import Decimal
from datetime import datetime, timezone, timedelta
import json
import os

application = Flask(__name__)

TABLE_NAME = os.getenv("SENSOR_TABLE", "SmartTrafficReadings")
REGION     = os.getenv("AWS_REGION", "eu-north-1")

print("USING TABLE:", TABLE_NAME)
print("USING REGION:", REGION)

dynamodb = boto3.resource("dynamodb", region_name=REGION)
table    = dynamodb.Table(TABLE_NAME)

SENSOR_IDS = ["VC-001", "SR-001", "TL-001", "AQ-001", "PD-001"]


class _Enc(json.JSONEncoder):
    def default(self, o):
        return float(o) if isinstance(o, Decimal) else super().default(o)

application.json_encoder = _Enc


def query_recent(sensor_id, minutes=60):
    """
    Query by partition key only (works with both old sk=timestamp
    and new sk=timestamp#uuid format), return last 200 items.
    """
    try:
        resp  = table.query(
            KeyConditionExpression=Key("pk").eq(sensor_id),
            ScanIndexForward=False,   # newest first
            Limit=200
        )
        items = resp.get("Items", [])
        print(f"[QUERY] {sensor_id} → {len(items)} items")
        return list(reversed(items))  # flip back to oldest-first for charts
    except Exception as exc:
        print(f"[ERROR] query_recent({sensor_id}): {exc}")
        return []


def get_latest(sensor_id):
    """Get single most recent reading for summary card."""
    try:
        resp = table.query(
            KeyConditionExpression=Key("pk").eq(sensor_id),
            ScanIndexForward=False,
            Limit=1
        )
        items = resp.get("Items", [])
        return items[0] if items else None
    except Exception as exc:
        print(f"[ERROR] get_latest({sensor_id}): {exc}")
        return None


#Routes 

@application.route("/")
def index():
    return render_template("index.html")


@application.route("/api/sensor/<sensor_id>")
def sensor_data(sensor_id):
    if sensor_id not in SENSOR_IDS:
        return jsonify({"error": "unknown sensor"}), 404
    items = query_recent(sensor_id)
    return jsonify({
        "sensor_id": sensor_id,
        "count":     len(items),
        "readings":  items
    })


@application.route("/api/summary")
def summary():
    result = {}
    for sid in SENSOR_IDS:
        latest       = get_latest(sid)
        result[sid]  = {
            "count":  None,
            "latest": latest
        }
    return jsonify(result)


@application.route("/api/anomalies")
def anomalies():
    found = []
    for sid in SENSOR_IDS:
        items  = query_recent(sid, minutes=60)
        found += [r for r in items if r.get("anomaly")]
    found.sort(key=lambda x: x["sk"], reverse=True)
    return jsonify({"anomalies": found[:50]})


@application.route("/api/health")
def health():
    """Quick health check — confirms table connection works."""
    try:
        resp = table.scan(Select="COUNT", Limit=1)
        return jsonify({"status": "ok", "table": TABLE_NAME, "region": REGION})
    except Exception as exc:
        return jsonify({"status": "error", "detail": str(exc)}), 500


if __name__ == "__main__":
    application.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))