from aws_cdk import (
    Stack,
    aws_ecs as ecs,
    aws_ecs_patterns as ecs_patterns,
    aws_ec2 as ec2,
)
from constructs import Construct


class FargateHelloWorld(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        vpc = ec2.Vpc(self, "osdpVpc", max_azs=3)  # default is all AZs in region
        cluster = ecs.Cluster(self, "osdpCluster", vpc=vpc)

        ecs_patterns.ApplicationLoadBalancedFargateService(
            self,
            "OSDPService",
            cluster=cluster,  # Required
            cpu=512,  # Default is 256
            desired_count=1,  # Default is 1
            task_image_options=ecs_patterns.ApplicationLoadBalancedTaskImageOptions(
                image=ecs.ContainerImage.from_registry("amazon/amazon-ecs-sample")
            ),
            memory_limit_mib=2048,  # Default is 512
            public_load_balancer=True,
        )  # Default is True
