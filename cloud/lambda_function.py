import json
import boto3
import os
import logging
import time
from decimal import Decimal

logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb   = boto3.resource("dynamodb")
TABLE_NAME = os.environ["SENSOR_TABLE"]
QUEUE_URL  = os.environ["SQS_QUEUE_URL"]


def lambda_handler(event, context):
    """
    Two invocation modes:
      API Gateway POST /ingest  →  queues the batch in SQS immediately
      SQS trigger               →  writes each reading to DynamoDB
    """
    if "Records" in event:
        # SQS-triggered processing
        written = 0
        for record in event["Records"]:
            try:
                body    = json.loads(record["body"])
                written += write_batch(body)
            except Exception as exc:
                logger.error(f"Record failed: {exc}")
                raise   # Let SQS retry this message
        return {"statusCode": 200, "written": written}

    # API Gateway invocation
    try:
        body = json.loads(event.get("body") or "{}")
    except json.JSONDecodeError:
        return _resp(400, {"error": "Invalid JSON body"})

    if not body.get("readings"):
        return _resp(400, {"error": "Missing 'readings' array"})

    sqs = boto3.client("sqs")
    sqs.send_message(
        QueueUrl    = QUEUE_URL,
        MessageBody = json.dumps(body)
    )
    logger.info(f"Queued {body.get('batch_size',0)} readings from {body.get('fog_node')}")
    return _resp(200, {"status": "queued", "batch_size": body.get("batch_size", 0)})


def write_batch(batch):
    table    = dynamodb.Table(TABLE_NAME)
    readings = batch.get("readings", [])
    fog_node = batch.get("fog_node", "UNKNOWN")
    written  = 0

    with table.batch_writer() as bw:
        for r in readings:
            item = {
                "pk":          r["sensor_id"],      # partition key
                "sk":          r["timestamp"],      # sort key
                "sensor_type": r.get("sensor_type", ""),
                "location":    r.get("location", ""),
                "fog_node":    fog_node,
                "topic":       r.get("topic", ""),
                "anomaly":     r.get("anomaly"),
                "data":        _to_decimal(r.get("data", {})),
                "ttl":         int(time.time()) + 30 * 86400  # expire after 30 days
            }
            bw.put_item(Item=item)
            written += 1

    logger.info(f"Wrote {written} items")
    return written


def _to_decimal(obj):
    """DynamoDB requires Decimal instead of float."""
    if isinstance(obj, float):
        return Decimal(str(round(obj, 6)))
    if isinstance(obj, dict):
        return {k: _to_decimal(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_to_decimal(i) for i in obj]
    return obj


def _resp(status, body):
    return {
        "statusCode": status,
        "headers":    {"Content-Type": "application/json",
                       "Access-Control-Allow-Origin": "*"},
        "body":       json.dumps(body)
    }