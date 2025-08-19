# ecs_construct.py
from aws_cdk import (
    aws_ec2 as ec2,
)
from aws_cdk import (
    aws_ecs as ecs,
)
from aws_cdk import (
    aws_iam as iam,
)
from aws_cdk import (
    aws_logs as logs,
)
from constructs import Construct


class EcsConstruct(Construct):
    def __init__(self, scope: Construct, id: str, *, data_bucket, ecr_image: str, **kwargs) -> None:
        super().__init__(scope, id)

        # Use the default VPC
        self.vpc = ec2.Vpc.from_lookup(self, "DefaultVpc", is_default=True)

        # Create ECS Cluster
        self.cluster = ecs.Cluster(self, "TreetopCluster", vpc=self.vpc)

        # Task Role
        self.task_role = iam.Role(
            self,
            "TreetopTaskRole",
            assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
        )

        data_bucket.grant_put(self.task_role)

        # Execution Role for ECS Task
        self.execution_role = iam.Role(
            self,
            "TreetopExecutionRole",
            assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
        )

        self.execution_role.add_to_policy(
            iam.PolicyStatement(
                actions=["logs:CreateLogStream", "logs:PutLogEvents"],
                resources=["*"],
            )
        )

        # Create Task Definition
        self.task_definition = ecs.FargateTaskDefinition(
            self,
            "TreetopIiifFetcherTaskDef",
            memory_limit_mib=512,
            cpu=256,
            task_role=self.task_role,
            execution_role=self.execution_role,
        )

        # Add container to task definition
        self.container = self.task_definition.add_container(
            "TreetopIiifFetcherContainer",
            image=ecs.ContainerImage.from_registry(ecr_image),
            logging=ecs.LogDriver.aws_logs(
                stream_prefix="Treetop-iiif-fetcher",
                log_retention=logs.RetentionDays.ONE_WEEK,
            ),
        )
