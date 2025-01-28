from aws_cdk import (
    Stack,
    aws_ecs as ecs,
    aws_ec2 as ec2,
    aws_logs as logs,
    aws_iam as iam,
    aws_ecr as ecr,
)
from constructs import Construct


class IiifFetcherStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Create the vpc
        vpc = ec2.Vpc(self, "osdpVpc", max_azs=3)  # default is all AZs in region
        cluster = ecs.Cluster(self, "osdpCluster", vpc=vpc)

        # Create Task Definition
        task_definition = ecs.FargateTaskDefinition(
            self,
            "IiifFetcherTaskDef",
            memory_limit_mib=512,
            cpu=256,
        )

        # Reference the ECR repository
        repository = ecr.Repository.from_repository_attributes(
            self,
            "IiifFetcherRepo",
            repository_name="osdp-iiif-fetcher",
            repository_arn="arn:aws:ecr:us-east-1:625046682746:repository/osdp-iiif-fetcher"
        )

        # Add container to task definition
        container = task_definition.add_container(
            "IiifFetcherContainer",
            # image=ecs.ContainerImage.from_registry("625046682746.dkr.ecr.us-east-1.amazonaws.com/osdp-iiif-fetcher:latest"),
            image=ecs.ContainerImage.from_ecr_repository(repository, "latest"),
            logging=ecs.LogDrivers.aws_logs(
                stream_prefix="IiifFetcher", log_retention=logs.RetentionDays.ONE_WEEK
            ),
        )

        # Create Fargate Service
        service = ecs.FargateService(
            self,
            "IiifFetcherService",
            cluster=cluster,
            task_definition=task_definition,
            desired_count=0,
            min_healthy_percent=0,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC),
            assign_public_ip=True  # Required for public subnet access to ECR
        )

        # Add necessary permissions for CloudWatch Logs
        task_definition.add_to_task_role_policy(
            iam.PolicyStatement(
                actions=["logs:CreateLogStream", "logs:PutLogEvents"], resources=["*"]
            )
        )
