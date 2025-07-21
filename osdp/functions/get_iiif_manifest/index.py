import hashlib
import json
import logging
import os

import boto3
from loam_iiif.iiif import IIIFClient

DEST_BUCKET = os.environ["DEST_BUCKET"]
DEST_PREFIX = os.environ.get("DEST_PREFIX")

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def key_from_uri(uri):
    # Compute a SHA256 hash of the URI
    hash_digest = hashlib.sha256(uri.encode("utf-8")).hexdigest()
    return f"{hash_digest}.txt"


def handler(event, _context):
    # Extract the CSV row from the event payload
    row = event.get("row")
    if not row:
        return {"statusCode": 400, "body": json.dumps({"message": "No 'row' provided in event."})}

    # Now extract the URI from the row
    uri = row.get("uri")
    if not uri:
        return {"statusCode": 400, "body": json.dumps({"message": "No 'uri' provided in row."})}

    # Parse the IIIF manifest using loam-iiif
    client = IIIFClient()
    try:
        manifest_data = client.parse_manifest(uri, strip_tags=True)
        if not manifest_data:
            return {"statusCode": 400, "body": json.dumps({"message": "Failed to parse IIIF manifest."})}
        
        text = manifest_data.get("text", "")
        if not text:
            return {"statusCode": 400, "body": json.dumps({"message": "No text content found in manifest."})}
            
    except Exception as e:
        logger.error(f"Error parsing IIIF manifest: {e}")
        return {"statusCode": 500, "body": json.dumps({"message": "Error parsing IIIF manifest", "error": str(e)})}

    # Write to S3
    s3_key = f"{DEST_PREFIX}{key_from_uri(uri)}"

    s3 = boto3.client("s3")
    try:
        s3.put_object(Bucket=DEST_BUCKET, Key=s3_key, Body=text, ContentType="text/plain")

        return {
            "statusCode": 200,
            "body": json.dumps({"message": "Manifest fetched and stored successfully", "s3_key": s3_key}),
        }

    except Exception as e:
        logger.error(f"Error writing manifest to S3: {e}")
        return {"statusCode": 500, "body": json.dumps({"message": "Error writing to S3", "error": str(e)})}
