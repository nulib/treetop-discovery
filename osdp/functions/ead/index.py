import json
import os
import uuid

import boto3
from eadpy import Ead

s3 = boto3.client("s3")


def handler(event, context):
    print(f"Processing Ead: {event}")

    source_bucket = event.get("bucket")
    key = event.get("key")

    if not source_bucket or not key:
        print("Missing required parameters: bucket or key")
        return {"statusCode": 400, "body": json.dumps("Missing required parameters: bucket or key")}

    dest_prefix = os.environ.get("DEST_PREFIX", "data/ead/")
    dest_bucket = os.environ["DEST_BUCKET"]

    try:
        # Download the Ead XML file from S3 to a temporary location
        local_file_name = f"/tmp/{uuid.uuid4().hex}.xml"
        s3.download_file(source_bucket, key, local_file_name)
        print(f"Downloaded file to: {local_file_name}")

        # Parse the Ead XML using eadpy with the exact same path
        ead = Ead(local_file_name)

        parsed_ead = ead.create_item_chunks()
        for record in parsed_ead:
            text = record["text"]
            print("Embedding Text:")
            for line in text.split("\n"):
                print(f"  {line}")
            print("-" * 20)

        # Save the processed data to S3 data source location
        dest_key = f"{dest_prefix}{os.path.basename(key).replace('.xml', '.json')}"
        s3.put_object(
            Bucket=dest_bucket, Key=dest_key, Body=json.dumps(parsed_ead, indent=2), ContentType="application/json"
        )

        print(f"Successfully processed Ead file. Output saved to s3://{dest_bucket}/{dest_key}")

        return {
            "statusCode": 200,
            "body": json.dumps(
                {
                    "message": "Ead file processed successfully",
                    "source": f"s3://{source_bucket}/{key}",
                    "destination": f"s3://{dest_bucket}/{dest_key}",
                }
            ),
        }

    except Exception as e:
        print(f"Error processing Ead file: {str(e)}")
        return {"statusCode": 500, "body": json.dumps(f"Error processing Ead file: {str(e)}")}
