import json
import os

import boto3

bedrock_agent_runtime_client = boto3.client("bedrock-agent-runtime")


def handler(event, _context):
    print(event)
    if not event.get("body") or event.get("body") == "":
        return {"statusCode": 400}

    request_body = json.loads(event.get("body"))
    user_prompt = request_body.get("user_prompt")
    _session_id = request_body.get("session_id", "")

    if not user_prompt:
        return {"statusCode": 400}

    print(user_prompt)

    knowledge_base_id = os.environ["KNOWLEDGE_BASE_ID"]
    modelArn = os.environ["MODEL_ARN"]

    prompt = f"""\n\nHuman:
    Please answer [question] appropriately.
    [question]
    {user_prompt}
    Assistant:
    """

    bedrock_response = bedrock_agent_runtime_client.retrieve_and_generate(
        input={
            "text": prompt,
        },
        retrieveAndGenerateConfiguration={
            "type": "KNOWLEDGE_BASE",
            "knowledgeBaseConfiguration": {
                "knowledgeBaseId": knowledge_base_id,
                "modelArn": modelArn,
                "generationConfiguration": {
                    "inferenceConfig": {
                        "textInferenceConfig": {
                            "maxTokens": 500,
                            "temperature": 0.7,
                            "topP": 0.9,
                        }
                    },
                },
                "retrievalConfiguration": {
                    "vectorSearchConfiguration": {
                        "numberOfResults": 10,
                    }
                },
            },
        },
    )

    print("Received response:" + json.dumps(bedrock_response, ensure_ascii=False))

    response_output = bedrock_response["output"]["text"]

    response = {
        "answer": response_output,
        "references": bedrock_response["citations"][0]["retrievedReferences"],
        "session_id": bedrock_response["sessionId"],
    }

    return {
        "headers": {"Access-Control-Allow-Origin": "*", "Access-Control-Allow-Credentials": True},
        "statusCode": 200,
        "body": json.dumps(response),
    }
