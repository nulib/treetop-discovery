import csv
import io
import logging
import os

import boto3
from loam_iiif.iiif import IIIFClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def fetch_collection(url):
    try:
        with IIIFClient() as client:
            manifests, collections = client.get_manifests_and_collections_ids(url)
    except Exception as e:
        logger.error(f"An error occurred: {e}")
        raise

    logger.info(f"Found {len(manifests)} manifests and {len(collections)} collections.")
    results = []
    for manifest_url in manifests:
        try:
            chunks = client.create_manifest_chunks([manifest_url])
            for chunk in chunks:
                results.append({"uri": manifest_url, "text": chunk["text"]})
        except Exception as e:
            logger.error(f"Could not process manifest {manifest_url}: {e}")
            continue

    return results


def main():
    url = os.environ.get("COLLECTION_URL")
    if not url:
        logger.error("No COLLECTION_URL environment variable set")
        return

    bucket_name = os.environ.get("BUCKET_NAME")
    if not bucket_name:
        logger.error("No BUCKET_NAME environment variable set")
        return

    data = fetch_collection(url)

    if not data:
        logger.warning("No data was fetched or processed. Exiting.")
        return

    output = io.StringIO()
    fieldnames = ["uri", "text"]
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(data)
    csv_data = output.getvalue()

    try:
        s3 = boto3.client("s3")

        respone = s3.put_object(
            Body=bytes(csv_data, encoding="utf-8"),
            Bucket=bucket_name,
            Key="manifests.csv",
            ContentType="text/csv",
        )
        logger.info(f"Uploaded file to S3: {respone}")
    except Exception as e:
        logger.error(f"An error occurred uploading file to S3: {e}")
        raise

    logger.info("Task completed successfully")


if __name__ == "__main__":
    main()
