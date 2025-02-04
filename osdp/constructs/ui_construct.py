# ui_construct.py
from aws_cdk import (
    CfnOutput,
    Duration,
    Fn,
    RemovalPolicy,
    Size,
    Stack,
    triggers,
)
from aws_cdk import aws_iam as iam
from aws_cdk import (
    aws_lambda as _lambda,
)
from aws_cdk import (
    aws_s3 as s3,
)

from constructs import Construct


class UIConstruct(Construct):
    def __init__(self, scope: Construct, id: str, *, stack_id: str, api_url: str, **kwargs) -> None:
        super().__init__(scope, id)

        stack = Stack.of(self)
        ui_bucket_name = Fn.join("-", [stack.stack_name.lower(), "ui", stack_id])

        # Create the S3 bucket for the UI
        self.ui_bucket = s3.Bucket(
            self,
            "UserInterfaceBucket",
            bucket_name=ui_bucket_name,
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
        self.ui_bucket.add_to_resource_policy(
            iam.PolicyStatement(
                actions=["s3:GetObject"],
                resources=[f"{self.ui_bucket.bucket_arn}/*"],
                principals=[iam.AnyPrincipal()],
            )
        )

        # Define a build function for the UI
        self.build_function = triggers.TriggerFunction(
            self,
            "BuildFunction",
            runtime=_lambda.Runtime.NODEJS_LATEST,
            handler="index.handler",
            code=_lambda.Code.from_asset("./functions/build_function"),
            environment={
                "BUCKET_NAME": self.ui_bucket.bucket_name,
                "REPO_NAME": "osdp-prototype-ui",
                "NEXT_PUBLIC_API_URL": api_url,
            },
            timeout=Duration.minutes(5),
            memory_size=1024,
            ephemeral_storage_size=Size.gibibytes(1),
        )

        # Add the Git layer to the build function
        self.build_function.add_layers(
            _lambda.LayerVersion.from_layer_version_arn(
                self,
                "GitLayer",
                layer_version_arn="arn:aws:lambda:us-east-1:553035198032:layer:git-lambda2:8",
            )
        )

        # Does it need this?
        self.build_function_url = self.build_function.add_function_url(
            auth_type=_lambda.FunctionUrlAuthType.NONE,
        )

        # Grant Lambda permissions
        self.ui_bucket.grant_read_write(self.build_function)

        CfnOutput(self, "buildFunctionUrl", value=self.build_function_url.url)

        # Output the website URL
        CfnOutput(
            self,
            "WebsiteURL",
            value=self.ui_bucket.bucket_website_url,
            description="URL for UI website hosted on S3",
        )