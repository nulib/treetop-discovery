import aws_cdk as core
import aws_cdk.assertions as assertions
import pytest

from treetop.stacks.treetop_stack import TreetopStack

STACK_PREFIX = "alice"


@pytest.fixture
def stack_and_template():
    app = core.App()
    app.node.set_context("stack_prefix", "alice")
    app.node.set_context("tags", {"foo": "bar", "environment": "dev"})
    app.node.set_context("data", {"type": "ead", "s3": {"bucket": "test-bucket", "prefix": "test-prefix/"}})
    app.node.set_context(
        "embedding_model_arn", "arn:aws:sagemaker:us-east-1:123456789012:model/bedrock-embedding-model"
    )
    app.node.set_context(
        "foundation_model_arn", "arn:aws:sagemaker:us-east-1:123456789012:model/bedrock-embedding-model"
    )
    app.node.set_context("aws:cdk:bundling-stacks", [])  # Disable bundling to speed up tests
    stack = TreetopStack(app, "alice-Treetop", env={"account": "123456789012", "region": "us-east-1"})
    template = assertions.Template.from_stack(stack)
    return stack, template


def test_status_lambda_created(stack_and_template):
    """Test that the status Lambda function is created with correct properties."""
    stack, template = stack_and_template
    template.has_resource_properties(
        "AWS::Lambda::Function",
        {
            "Handler": "index.handler",
            "Runtime": "python3.11",
            "Timeout": 60,
            "MemorySize": 512,
            "Environment": {
                "Variables": {
                    "KNOWLEDGE_BASE_ID": assertions.Match.any_value(),
                    "DATA_SOURCE_ID": assertions.Match.any_value(),
                }
            },
        },
    )


def test_status_lambda_has_bedrock_permissions(stack_and_template):
    """Test that the status Lambda function has proper Bedrock permissions."""
    stack, template = stack_and_template
    template.has_resource_properties(
        "AWS::IAM::Policy",
        {
            "PolicyDocument": {
                "Statement": assertions.Match.array_with(
                    [
                        assertions.Match.object_like(
                            {
                                "Action": [
                                    "bedrock:ListIngestionJobs",
                                    "bedrock:GetIngestionJob",
                                ],
                                "Effect": "Allow",
                                "Resource": assertions.Match.any_value(),
                            }
                        )
                    ]
                )
            }
        },
    )


def test_status_endpoint_with_cognito_auth(stack_and_template):
    """Test that the /status endpoint is created with Cognito authorization."""
    stack, template = stack_and_template

    # Check that a GET method is created with Cognito auth
    template.has_resource_properties(
        "AWS::ApiGateway::Method",
        {
            "HttpMethod": "GET",
            "ResourceId": assertions.Match.any_value(),
            "RestApiId": assertions.Match.any_value(),
            "AuthorizationType": "COGNITO_USER_POOLS",
            "AuthorizerId": assertions.Match.any_value(),
            "Integration": {
                "Type": "AWS_PROXY",
                "IntegrationHttpMethod": "POST",  # Lambda proxy always uses POST
            },
        },
    )


def test_status_resource_created(stack_and_template):
    """Test that the /status API resource is created."""
    stack, template = stack_and_template

    # Check that a resource is created (we can't easily check the path name in CDK tests)
    template.has_resource_properties(
        "AWS::ApiGateway::Resource",
        {
            "ParentId": assertions.Match.any_value(),
            "PathPart": "status",
            "RestApiId": assertions.Match.any_value(),
        },
    )


def test_api_gateway_cors_includes_get_method(stack_and_template):
    """Test that CORS is configured to allow GET methods."""
    stack, template = stack_and_template

    # Check for OPTIONS method that includes GET in allowed methods
    response_headers = {
        "ResponseParameters": {
            "method.response.header.Access-Control-Allow-Headers": assertions.Match.string_like_regexp(".*"),
            "method.response.header.Access-Control-Allow-Methods": assertions.Match.string_like_regexp(".*GET.*"),
        }
    }
    template.has_resource_properties(
        "AWS::ApiGateway::Method",
        {
            "HttpMethod": "OPTIONS",
            "ResourceId": assertions.Match.any_value(),
            "RestApiId": assertions.Match.any_value(),
            "Integration": {
                "IntegrationResponses": assertions.Match.array_with([assertions.Match.object_like(response_headers)]),
            },
        },
    )


def test_admin_group_still_exists(stack_and_template):
    """Test that the Admin group still exists (regression test)."""
    stack, template = stack_and_template
    template.has_resource_properties(
        "AWS::Cognito::UserPoolGroup",
        {
            "GroupName": "Admin",
            "UserPoolId": assertions.Match.any_value(),
        },
    )


def test_lambda_count(stack_and_template):
    """Test that we have the expected number of Lambda functions."""
    stack, template = stack_and_template

    # Count Lambda functions - should have chat, status, and other functions
    lambda_functions = template.find_resources("AWS::Lambda::Function")

    # Should have at least 2 Lambda functions (chat and status)
    # Note: There might be other Lambda functions in the stack
    assert len(lambda_functions) >= 2


def test_api_method_count(stack_and_template):
    """Test that we have the expected API methods."""
    stack, template = stack_and_template

    # Find all API Gateway methods
    api_methods = template.find_resources("AWS::ApiGateway::Method")

    # Should have at least: POST /chat, GET /status, plus OPTIONS for CORS
    # Note: There might be additional methods
    assert len(api_methods) >= 3
