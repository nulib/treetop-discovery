import os
import logging
from loam_iiif.iiif import IIIFClient
import boto3

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def fetch_collection(url):
    try:
        with IIIFClient() as client:
            manifests, collections = client.get_manifests_and_collections_ids(url)
    except Exception as e:
        logger.error(f"An error occurred: {e}")
        raise

    logger.info(
        f"Traversal completed. Found {len(manifests)} unique manifests and {len(collections)} collections."
    )

    return manifests

def main():
    url = os.environ.get('COLLECTION_URL')
    if not url:
        logger.error("No COLLECTION_URL environment variable set")
        return

    bucket_name = os.environ.get('BUCKET_NAME')
    if not bucket_name:
        logger.error("No BUCKET_NAME environment variable set")
        return

    manifests_urls = fetch_collection(url)
    data = '\n'.join(manifests_urls)

    try:
        s3 = boto3.client('s3')

        respone = s3.put_object(
            Body=bytes(data, encoding='utf-8'),
            Bucket=bucket_name,
            Key="manifests.csv",
            ContentType='text/csv'
        )
        logger.info(f"Uploaded file to S3: {respone}")
    except Exception as e:
        logger.error(f"An error occurred uploading file to S3: {e}")
        raise


    logger.info("Task completed successfully")


if __name__ == "__main__":
    main()