"""DynamoDB database layer."""

import boto3
import os
from datetime import datetime
import uuid

TABLE_NAME = os.environ.get("DYNAMO_TABLE", "learning-items")

def get_table():
    dynamodb = boto3.resource("dynamodb", region_name=os.environ.get("AWS_DEFAULT_REGION", "us-east-1"))
    return dynamodb.Table(TABLE_NAME)


def list_bookmarks(category: str | None = None):
    table = get_table()
    if category:
        resp = table.query(
            KeyConditionExpression="pk = :pk",
            ExpressionAttributeValues={":pk": f"BOOKMARK#{category}"},
        )
    else:
        resp = table.scan(
            FilterExpression="begins_with(pk, :prefix)",
            ExpressionAttributeValues={":prefix": "BOOKMARK#"},
        )
    return resp.get("Items", [])


def get_bookmark(category: str, bookmark_id: str):
    table = get_table()
    resp = table.get_item(Key={"pk": f"BOOKMARK#{category}", "sk": bookmark_id})
    return resp.get("Item")


def create_bookmark(category: str, title: str, url: str, notes: str | None = None):
    table = get_table()
    bookmark_id = str(uuid.uuid4())[:8]
    item = {
        "pk": f"BOOKMARK#{category}",
        "sk": bookmark_id,
        "title": title,
        "url": url,
        "notes": notes or "",
        "created_at": datetime.now().isoformat(),
    }
    table.put_item(Item=item)
    return item


def update_bookmark(category: str, bookmark_id: str, **fields):
    table = get_table()
    updates = []
    values = {}
    names = {}
    for k, v in fields.items():
        if v is not None:
            attr_key = f"#{k}"
            val_key = f":{k}"
            updates.append(f"{attr_key} = {val_key}")
            values[val_key] = v
            names[attr_key] = k
    if not updates:
        return get_bookmark(category, bookmark_id)
    updates.append("#updated_at = :updated_at")
    values[":updated_at"] = datetime.now().isoformat()
    names["#updated_at"] = "updated_at"
    resp = table.update_item(
        Key={"pk": f"BOOKMARK#{category}", "sk": bookmark_id},
        UpdateExpression="SET " + ", ".join(updates),
        ExpressionAttributeValues=values,
        ExpressionAttributeNames=names,
        ReturnValues="ALL_NEW",
    )
    return resp.get("Attributes")


def delete_bookmark(category: str, bookmark_id: str):
    table = get_table()
    table.delete_item(Key={"pk": f"BOOKMARK#{category}", "sk": bookmark_id})


def get_categories():
    """Scan for unique categories."""
    table = get_table()
    resp = table.scan(
        FilterExpression="begins_with(pk, :prefix)",
        ExpressionAttributeValues={":prefix": "BOOKMARK#"},
        ProjectionExpression="pk",
    )
    cats = set()
    for item in resp.get("Items", []):
        cats.add(item["pk"].replace("BOOKMARK#", ""))
    return sorted(cats)
