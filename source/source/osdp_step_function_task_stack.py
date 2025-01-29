from aws_cdk import (
    Stack,
    aws_ecs as ecs,
    aws_iam as iam,
    aws_ec2 as ec2,
    aws_logs as logs,
    aws_lambda as _lambda,
    aws_stepfunctions as sfn,
    aws_stepfunctions_tasks as sfn_tasks,
    Duration,
    triggers,
    Fn,
    aws_s3 as s3,
    RemovalPolicy,
)
import os
from constructs import Construct

ECR_REPO = "arn:aws:ecr:us-east-1:625046682746:repository/osdp-iiif-fetcher"
ECR_IMAGE = "625046682746.dkr.ecr.us-east-1.amazonaws.com/osdp-iiif-fetcher:latest"
class OsdpStepFunctionTaskStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        unique_id = Fn.select(2, Fn.split("/", self.stack_id))
        suffix = Fn.select(4, Fn.split("-", unique_id))
        bucket_name = Fn.join("-", ["osdp-manifests", suffix])

        bucket = s3.Bucket(
            self,
            "ManifestsBucket",
            bucket_name=bucket_name,
            block_public_access=s3.BlockPublicAccess(
                block_public_acls=False,
                block_public_policy=False,
                ignore_public_acls=False,
                restrict_public_buckets=False,
            ),
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
        )

        # Create VPC
        vpc = ec2.Vpc(self, "OsdpVpc", max_azs=2)

        # Create ECS Cluster
        cluster = ecs.Cluster(self, "OsdpCluster", vpc=vpc)

        # Task Role
        task_role = iam.Role(
            self,
            "OsdpTaskRole",
            assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
        )

        task_role.add_to_policy(
            iam.PolicyStatement(
                actions=["ecr:GetDownloadUrlForLayer", "ecr:BatchGetImage"],
                resources=[ECR_REPO],
            )
        )

        task_role.add_to_policy(
            iam.PolicyStatement(
                actions=["ecr:GetAuthorizationToken"],
                resources=["*"],  # This applies to the entire ECR service
            )
        )

        bucket.grant_put(task_role)

        # Execution Role for ECS Task
        execution_role = iam.Role(
            self,
            "OsdpExecutionRole",
            assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
        )

        execution_role.add_to_policy(
            iam.PolicyStatement(
                actions=["ecr:GetAuthorizationToken"],
                resources=["*"],  # This allows getting auth tokens for ECR
            )
        )

        execution_role.add_to_policy(
            iam.PolicyStatement(
                actions=["ecr:BatchCheckLayerAvailability", "ecr:GetDownloadUrlForLayer", "ecr:BatchGetImage"],
                resources=[ECR_REPO],
            )
        )

        execution_role.add_to_policy(
            iam.PolicyStatement(
                actions=["logs:CreateLogStream", "logs:PutLogEvents"],
                resources=["*"],  # You can scope this to your log group ARN
            )
        )

        # Create Task Definition
        task_definition = ecs.FargateTaskDefinition(
            self,
            "OsdpIiifFetcherTaskDef",
            memory_limit_mib=512,
            cpu=256,
            task_role=task_role,
            execution_role=execution_role
        )

        # Add container to task definition
        container = task_definition.add_container(
            "OsdpIiifFetcherContainer",
            image=ecs.ContainerImage.from_registry(
               ECR_IMAGE
            ),
            logging=ecs.LogDriver.aws_logs(
                stream_prefix="osdp-iiif-fetcher",
                log_retention=logs.RetentionDays.ONE_WEEK,
            ),
        )

        # First define the success and failure states
        success = sfn.Succeed(self, "TaskCompleted")
        failure = sfn.Fail(
            self, "TaskFailed", error="TaskFailedError", cause="Task execution failed"
        )

        # Create the ECS Run Task state
        run_task = sfn_tasks.EcsRunTask(
            self,
            "OsdpRunTask",
            integration_pattern=sfn.IntegrationPattern.RUN_JOB,  # Wait for task completion
            cluster=cluster,
            task_definition=task_definition,
            container_overrides=[
                sfn_tasks.ContainerOverride(
                    container_definition=container,
                    # Add any environment variables or command overrides
                    environment=[{"name": "COLLECTION_URL", "value": os.environ['COLLECTION_URL']}, {"name": "BUCKET_NAME", "value": bucket.bucket_name}],
                    # command=["command", "arg1", "arg2"]
                )
            ],
            assign_public_ip=True,
            subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC),
            launch_target=sfn_tasks.EcsFargateLaunchTarget(
                platform_version=ecs.FargatePlatformVersion.LATEST
            ),
            propagated_tag_source=ecs.PropagatedTagSource.TASK_DEFINITION,
        )

        # Create a chain that includes error handling
        definition = sfn.Chain.start(run_task)
        definition = definition.next(success)

        # Finally create the state machine with error handling
        state_machine = sfn.StateMachine(
            self, "OneOffTaskStateMachine", definition=definition
        )

        # Add this after your state machine creation
        triggers.TriggerFunction(
            self,
            "TriggerStepFunction",
            runtime=_lambda.Runtime.PYTHON_3_9,
            handler="index.handler",
            environment={"STATE_MACHINE_ARN": state_machine.state_machine_arn},
            code=_lambda.Code.from_asset("./functions/step_function_trigger"),
            # Grant permission to start Step Function execution
            timeout=Duration.minutes(1),
            initial_policy=[
                iam.PolicyStatement(
                    actions=["states:StartExecution"],
                    resources=[state_machine.state_machine_arn],
                )
            ],
        )
