from aws_cdk import (
    Stack,
    aws_lambda as _lambda,
    CfnOutput,
    aws_s3 as s3,
    RemovalPolicy,
    Fn,
    aws_iam as iam,
    triggers,
    Duration,
    Size,
)
from constructs import Construct


class OSDPPrototype(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Hello World Function
        my_function = _lambda.Function(
            self, "HelloWorldFunction",
            runtime = _lambda.Runtime.NODEJS_20_X, # Provide any supported Node.js runtime
            handler = "index.handler",
            code = _lambda.Code.from_inline(
                """
                exports.handler = async function(event) {
                return {
                    headers: {
                        "Access-Control-Allow-Origin" : "*",
                        "Access-Control-Allow-Credentials" : true
                    },
                    statusCode: 200,
                    body: JSON.stringify('Hello World!'),
                };
                };
                """
            ),
        )

        # Define the Lambda function URL resource
        my_function_url = my_function.add_function_url(
            auth_type = _lambda.FunctionUrlAuthType.NONE,
        )

        # Define a CloudFormation output for your URL
        CfnOutput(self, "myFunctionUrlOutput", value=my_function_url.url)

        # S3 bucket for the static UI
        # Generate unique bucket name using the same logic as CloudFormation
        unique_id = Fn.select(2, Fn.split("/", self.stack_id))
        suffix = Fn.select(4, Fn.split("-", unique_id))
        bucket_name = Fn.join("-", ["osdp-ui", suffix])

        # Create S3 bucket for the UI
        ui_bucket = s3.Bucket(
            self,
            "UserInterfaceBucket",
            bucket_name=bucket_name,
            website_index_document="index.html",
            website_error_document="error.html",
            block_public_access=s3.BlockPublicAccess(
                block_public_acls=False,
                block_public_policy=False,
                ignore_public_acls=False,
                restrict_public_buckets=False,
            ),
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
        )

        # Add bucket policy
        ui_bucket.add_to_resource_policy(
            iam.PolicyStatement(
                actions=["s3:GetObject"],
                resources=[f"{ui_bucket.bucket_arn}/*"],
                principals=[iam.AnyPrincipal()],
            )
        )

        # Output the website URL
        CfnOutput(
            self,
            "WebsiteURL",
            value=ui_bucket.bucket_website_url,
            description="URL for UI website hosted on S3",
        )

        # Lambda function to build the UI and deploy to S3
        build_function = triggers.TriggerFunction(
            self,
            "BuildFunction",
            runtime=_lambda.Runtime.NODEJS_LATEST,
            handler="index.handler",
            code=_lambda.Code.from_asset("./functions/build_function"),
            environment={
                "BUCKET_NAME": ui_bucket.bucket_name,
                "REPO_NAME": "osdp-prototype-ui",
                "NEXT_PUBLIC_API_URL": my_function_url.url,
            },
            timeout=Duration.minutes(5),
            memory_size=1024,
            ephemeral_storage_size=Size.gibibytes(1),
        )

        build_function.add_layers(
            _lambda.LayerVersion.from_layer_version_arn(
                self,
                "GitLayer",
                layer_version_arn="arn:aws:lambda:us-east-1:553035198032:layer:git-lambda2:8",
            )
        )

        build_function_url = build_function.add_function_url(
            auth_type=_lambda.FunctionUrlAuthType.NONE,
        )

        CfnOutput(self, "buildFunctionUrl", value=build_function_url.url)

         # Grant Lambda permissions
        ui_bucket.grant_read_write(build_function)

        # Create trigger
        # triggers.Trigger(
        #     self, "BuildTrigger",
        #     handler=build_function,
        #     execute_after=[ui_bucket, my_function]
        # )
