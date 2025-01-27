import os
import logging
from loam_iiif.iiif import IIIFClient

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

def main():
    # url = os.environ.get('TARGET_URL')
    # if not url:
    #     logger.error("No TARGET_URL environment variable set")
    #     return

    fetch_collection("https://api.dc.library.northwestern.edu/api/v2/collections/819526ed-985c-4f8f-a5c8-631fc400c2f1?as=iiif") # collection with 6 images
    logger.info("Task completed successfully")


if __name__ == "__main__":
    main()