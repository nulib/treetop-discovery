# Treetop - Docker image to fetch IIIF manifests

## Deployment

Deployment is handled via the `deploy-ecr.yml` Github Action.

## Local Development

To run the script locally, you can use the following commands from the `iiif/` directory:

```bash
export COLLECTION_URL="http://example.com/collection"
export BUCKET_NAME="your-s3-bucket-name"
uv run python manifest_fetcher.py
```