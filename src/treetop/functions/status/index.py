import base64
import json
import os
from typing import Any, Dict

import boto3

# This module-level client is the target for mocking in tests.
bedrock_agent_client = boto3.client("bedrock-agent")


def decode_jwt_payload(token: str) -> Dict[str, Any]:
    """Decode JWT payload without verification (API Gateway already verified it)."""
    try:
        # JWT has 3 parts separated by dots: header.payload.signature
        # We only need the payload (middle part)
        parts = token.split(".")
        if len(parts) != 3:
            return {}

        # Add padding if needed for base64 decoding
        payload = parts[1]
        # Correct padding: add only the minimal required '='
        payload += "=" * (-len(payload) % 4)

        # Decode base64 and parse JSON
        decoded_bytes = base64.urlsafe_b64decode(payload)
        payload_dict = json.loads(decoded_bytes.decode("utf-8"))

        return payload_dict
    except Exception as e:
        print(f"Error decoding JWT: {e}")
        return {}


def is_user_admin(event: Dict[str, Any]) -> bool:
    """Check if the authenticated user is in the Admin group."""
    try:
        # Get the authorization header
        headers = event.get("headers", {})
        auth_header = headers.get("Authorization") or headers.get("authorization")

        if not auth_header or not auth_header.startswith("Bearer "):
            return False

        # Extract the token
        token = auth_header[7:]  # Remove 'Bearer ' prefix

        # Decode the JWT payload
        payload = decode_jwt_payload(token)

        # Check if user is in Admin group
        groups = payload.get("cognito:groups", [])
        return "Admin" in groups

    except Exception as e:
        print(f"Error checking admin status: {e}")
        return False


def get_ingestion_jobs_status(knowledge_base_id: str, data_source_id: str) -> list:
    """Get the status of ingestion jobs for the data source."""
    try:
        # Directly use the module-level client. This ensures that when
        # 'index.bedrock_agent_client' is patched, the mock is used here.
        response = bedrock_agent_client.list_ingestion_jobs(
            knowledgeBaseId=knowledge_base_id,
            dataSourceId=data_source_id,
            maxResults=50,  # Get up to 50 most recent jobs
        )

        jobs = []
        for job in response.get("ingestionJobSummaries", []):
            jobs.append(
                {
                    "ingestionJobId": job.get("ingestionJobId"),
                    "status": job.get("status"),
                    "startedAt": job.get("startedAt").isoformat() if job.get("startedAt") else None,
                    "updatedAt": job.get("updatedAt").isoformat() if job.get("updatedAt") else None,
                    "description": job.get("description", ""),
                    "statistics": job.get("statistics", {}),
                }
            )

        return jobs

    except Exception as e:
        print(f"Error getting ingestion jobs: {e}")
        return []


def handler(event, context):
    """Lambda handler for status endpoint."""
    print(f"Event: {json.dumps(event)}")

    # Check if user is admin
    if not is_user_admin(event):
        return {
            "statusCode": 403,
            "headers": {"Access-Control-Allow-Origin": "*", "Access-Control-Allow-Credentials": True},
            "body": json.dumps({"error": "Access denied. Admin privileges required."}),
        }

    # Get environment variables
    knowledge_base_id = os.environ.get("KNOWLEDGE_BASE_ID")
    data_source_id = os.environ.get("DATA_SOURCE_ID")

    if not knowledge_base_id or not data_source_id:
        return {
            "statusCode": 500,
            "headers": {"Access-Control-Allow-Origin": "*", "Access-Control-Allow-Credentials": True},
            "body": json.dumps({"error": "Configuration error: missing knowledge base or data source ID"}),
        }

    # Get ingestion job statuses by calling the updated function.
    jobs = get_ingestion_jobs_status(knowledge_base_id, data_source_id)

    # Prepare response
    response_data = {
        "knowledgeBaseId": knowledge_base_id,
        "dataSourceId": data_source_id,
        "ingestionJobs": jobs,
        "totalJobs": len(jobs),
    }

    return {
        "statusCode": 200,
        "headers": {"Access-Control-Allow-Origin": "*", "Access-Control-Allow-Credentials": True},
        "body": json.dumps(response_data),
    }
