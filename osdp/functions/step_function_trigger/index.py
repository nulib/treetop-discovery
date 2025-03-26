import json
import os
import uuid

import boto3

sfn = boto3.client("stepfunctions")


def handler(event, context):
    print(f"Event: {event}")

    # Get environment variables
    workflow_type = os.environ.get("WORKFLOW_TYPE", "iiif")

    # Allow overriding workflow type from the event
    if event and isinstance(event, dict) and "workflowType" in event:
        workflow_type = event["workflowType"]

    # Debugging logs
    print(f"Triggering Step Function with workflow type: {workflow_type}")
    print(f"Bucket: {os.environ['BUCKET']}")

    # Common parameters
    execution_input = {
        "s3": {"Bucket": os.environ["BUCKET"]},
        "workflowType": workflow_type,
    }

    # Add workflow-specific parameters
    if workflow_type == "iiif":
        # For IIIF workflow, we need the collection URL
        execution_input["collection_url"] = os.environ["SOURCE_COLLECTION"]
        execution_input["s3"]["Key"] = os.environ.get("COLLECTION_FILENAME", "manifests.csv")
    elif workflow_type == "ead":
        # For EAD workflow, we need the prefix where EAD XML files are stored
        execution_input["s3"]["Prefix"] = os.environ["SOURCE_PREFIX"]
        execution_input["s3"]["Bucket"] = os.environ["SOURCE_BUCKET"]

    # Generate a unique name for this execution
    execution_name = f"{workflow_type}-{uuid.uuid4().hex[:8]}"

    # Start the execution
    response = sfn.start_execution(
        stateMachineArn=os.environ["STATE_MACHINE_ARN"], name=execution_name, input=json.dumps(execution_input)
    )

    return {
        "statusCode": 200,
        "body": json.dumps(
            {
                "message": f"{workflow_type.upper()} workflow triggered",
                "executionArn": response["executionArn"],
                "executionName": execution_name,
                "startDate": response["startDate"].isoformat(),
            }
        ),
    }
