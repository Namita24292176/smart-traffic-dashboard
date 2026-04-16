from flask import Flask, render_template, jsonify
import boto3
from boto3.dynamodb.conditions import Key
from decimal import Decimal
import json
import os

application = Flask(__name__)

# ✅ IMPORTANT: Correct region
TABLE_NAME = os.getenv("SENSOR_TABLE", "SmartTrafficReadings")
REGION     = os.getenv("AWS_REGION", "eu-north-1")

print("USING TABLE:", TABLE_NAME)
print("USING REGION:", REGION)

dynamodb = boto3.resource("dynamodb", region_name=REGION)
table    = dynamodb.Table(TABLE_NAME)

SENSOR_IDS = ["VC-001", "SR-001", "TL-001", "AQ-001", "PD-001"]


# JSON encoder for Decimal
class _Enc(json.JSONEncoder):
    def default(self, o):
        return float(o) if isinstance(o, Decimal) else super().default(o)

application.json_encoder = _Enc


# ✅ STRONG DEBUG QUERY
def query_recent(sensor_id):
    try:
        # Try query first
        resp = table.query(
            KeyConditionExpression=Key("pk").eq(sensor_id),
            ScanIndexForward=True,
            Limit=300
        )

        items = resp.get("Items", [])
        print(f"[QUERY] {sensor_id} → {len(items)} items")

        # ✅ If query fails, fallback to scan
        if len(items) == 0:
            print("Query returned 0 → scanning full table...")
            scan_resp = table.scan()
            all_items = scan_resp.get("Items", [])

            print("TOTAL ITEMS IN TABLE:", len(all_items))

            filtered = [i for i in all_items if i.get("pk") == sensor_id]

            print(f"[SCAN FILTERED] {sensor_id} → {len(filtered)} items")

            return filtered

        return items

    except Exception as e:
        print("ERROR:", str(e))
        return []


# ROUTES
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
        "count": len(items),
        "readings": items
    })


@application.route("/api/summary")
def summary():
    result = {}

    for sid in SENSOR_IDS:
        items = query_recent(sid)

        result[sid] = {
            "count": len(items),
            "latest": items[-1] if items else None
        }

    return jsonify(result)


@application.route("/api/anomalies")
def anomalies():
    found = []

    for sid in SENSOR_IDS:
        items = query_recent(sid)
        found += [r for r in items if r.get("anomaly")]

    found.sort(key=lambda x: x["sk"], reverse=True)

    return jsonify({"anomalies": found[:50]})


# ENTRY POINT
if __name__ == "__main__":
    application.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))