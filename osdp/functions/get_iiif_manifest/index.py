import hashlib
import json
import os

import boto3
import requests

BUCKET = os.environ["BUCKET"]


def key_from_uri(uri):
    # Compute a SHA256 hash of the URI
    hash_digest = hashlib.sha256(uri.encode("utf-8")).hexdigest()
    return f"iiif/{hash_digest}.json"


def handler(event, _context):
    print(event)

    # Extract the CSV row from the event payload
    row = event.get("row")
    if not row:
        return {"statusCode": 400, "body": json.dumps({"message": "No 'row' provided in event."})}

    # Now extract the URI from the row
    uri = row.get("uri")
    if not uri:
        return {"statusCode": 400, "body": json.dumps({"message": "No 'uri' provided in row."})}

    # Fetch the IIIF manifest from the URL
    try:
        response = requests.get(uri)
        response.raise_for_status()
        manifest = response.json()
    except Exception as e:
        print(f"Error fetching manifest from {uri}: {e}")
        return {"statusCode": 500, "body": json.dumps({"message": "Error fetching manifest", "error": str(e)})}

    # Write to S3
    s3_key = key_from_uri(uri)

    s3 = boto3.client("s3")
    try:
        s3.put_object(Bucket=BUCKET, Key=s3_key, Body=json.dumps(manifest), ContentType="application/json")
    except Exception as e:
        print(f"Error writing manifest to S3: {e}")
        return {"statusCode": 500, "body": json.dumps({"message": "Error writing to S3", "error": str(e)})}

    return {
        "statusCode": 200,
        "body": json.dumps({"message": "Manifest fetched and stored successfully", "s3_key": s3_key}),
    }
