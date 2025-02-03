import os

from aws_cdk import (
    Fn,
    RemovalPolicy,
    Stack,
    Tags,
)
from aws_cdk import (
    aws_s3 as s3,
)

from constructs import Construct
from constructs.api_construct import ApiConstruct
from constructs.ecs_task_construct import EcsConstruct
from constructs.step_functions_construct import StepFunctionsConstruct
from constructs.ui_construct import UIConstruct

ECR_REPO = "arn:aws:ecr:us-east-1:625046682746:repository/osdp-iiif-fetcher"
ECR_IMAGE = "625046682746.dkr.ecr.us-east-1.amazonaws.com/osdp-iiif-fetcher:latest"
COLLECTION_URL = os.getenv("COLLECTION_URL", "https://api.dc.library.northwestern.edu/api/v2/collections/819526ed-985c-4f8f-a5c8-631fc400c2f1?as=iiif")

class OsdpPrototypeStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Apply tag to all resources in this stack
        Tags.of(self).add("project", "imls-grant")

        # Generate unique name logic
        unique_id = Fn.select(2, Fn.split("/", self.stack_id))
        suffix = Fn.select(4, Fn.split("-", unique_id))

        # Create the API
        api_construct = ApiConstruct(self, "ApiConstruct")

        # Create the UI
        _ui_construct = UIConstruct(self, "UIConstruct", stack_id=suffix, api_url=api_construct.api_url.url)

        # S3 bucket for the IIIF Manifests (and other data)
        data_bucket_name = Fn.join("-", ["osdp", suffix])

        data_bucket = s3.Bucket(
            self,
            "DataBucket",
            bucket_name=data_bucket_name,
            block_public_access=s3.BlockPublicAccess(
                block_public_acls=False,
                block_public_policy=False,
                ignore_public_acls=False,
                restrict_public_buckets=False,
            ),
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
        )
        # Instantiate the ECS construct
        ecs_construct = EcsConstruct(
            self, "EcsConstruct", 
            data_bucket=data_bucket, 
            ecr_repo=ECR_REPO, 
            ecr_image=ECR_IMAGE)

        # Instantiate the Step Functions construct
        _step_functions_construct = StepFunctionsConstruct(
            self,
            "StepFunctionsConstruct",
            ecs_construct=ecs_construct,
            data_bucket=data_bucket,
            collection_url=COLLECTION_URL
        )


