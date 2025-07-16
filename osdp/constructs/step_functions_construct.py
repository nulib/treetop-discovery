# step_functions_construct.py
from aws_cdk import BundlingFileAccess, Duration, Stack, triggers
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
    aws_lambda as _lambda,
)
from aws_cdk import (
    aws_stepfunctions as sfn,
)
from aws_cdk import (
    aws_stepfunctions_tasks as sfn_tasks,
)
from constructs import Construct


class StepFunctionsConstruct(Construct):
    def __init__(
        self,
        scope: Construct,
        id: str,
        *,
        ecs_construct,
        data_bucket,
        data_config,
        knowledge_base=None,
        data_source=None,
        knowledge_base_id=None,
        data_source_id=None,
        **kwargs,
    ) -> None:
        super().__init__(scope, id)

        # Create the ECS Run Task state
        run_task = sfn_tasks.EcsRunTask(
            self,
            "OsdpRunFargateManifestFetcherTask",
            integration_pattern=sfn.IntegrationPattern.RUN_JOB,  # Wait for task completion
            cluster=ecs_construct.cluster,
            task_definition=ecs_construct.task_definition,
            container_overrides=[
                sfn_tasks.ContainerOverride(
                    container_definition=ecs_construct.container,
                    environment=[
                        {
                            "name": "COLLECTION_URL",
                            "value": sfn.JsonPath.string_at("$.collection_url"),
                        },
                        {"name": "BUCKET_NAME", "value": data_bucket.bucket_name},
                    ],
                )
            ],
            assign_public_ip=True,
            subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC),
            launch_target=sfn_tasks.EcsFargateLaunchTarget(platform_version=ecs.FargatePlatformVersion.LATEST),
            propagated_tag_source=ecs.PropagatedTagSource.TASK_DEFINITION,
            result_path="$.task_result",  # I think this can be removed
        )

        # Lambda function for fetching manifests from url list
        fetch_iiif_manifest_function = _lambda.Function(
            self,
            "fetch_iiif_manifest_function",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="index.handler",
            code=_lambda.Code.from_asset(
                "./functions/get_iiif_manifest",
                bundling={
                    "image": _lambda.Runtime.PYTHON_3_11.bundling_image,
                    "bundling_file_access": BundlingFileAccess.VOLUME_COPY,
                    "command": [
                        "bash",
                        "-c",
                        "pip install -r requirements.txt -t /asset-output && cp -r . /asset-output",
                    ],
                },
            ),
            timeout=Duration.minutes(2),
            environment={"DEST_BUCKET": data_bucket.bucket_name, "DEST_PREFIX": "data/iiif/"},
        )

        # Lambda function for processing EAD XML files
        process_ead_function = _lambda.Function(
            self,
            "process_ead_function",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="index.handler",
            code=_lambda.Code.from_asset(
                "./functions/ead",
                bundling={
                    "image": _lambda.Runtime.PYTHON_3_11.bundling_image,
                    "bundling_file_access": BundlingFileAccess.VOLUME_COPY,
                    "command": [
                        "bash",
                        "-c",
                        "pip install -r requirements.txt -t /asset-output && cp -r . /asset-output",
                    ],
                },
            ),
            timeout=Duration.minutes(3),
            environment={
                "DEST_BUCKET": data_bucket.bucket_name,
                "DEST_PREFIX": "data/ead/",
            },
            memory_size=512,
        )

        # Grant the Lambda function read/write access to S3
        data_bucket.grant_read(fetch_iiif_manifest_function)
        data_bucket.grant_put(fetch_iiif_manifest_function)

        # Grant EAD Lambda read/write access to S3
        data_bucket.grant_read(process_ead_function)
        data_bucket.grant_put(process_ead_function)

        # IAM Role for Step Functions to access S3 and invoke Lambda
        step_functions_role = iam.Role(
            self,
            "StepFunctionsExecutionRole",
            assumed_by=iam.ServicePrincipal("states.amazonaws.com"),
        )

        step_functions_role.add_to_policy(
            iam.PolicyStatement(
                actions=["s3:ListBucket", "s3:GetObject"],
                resources=[
                    data_bucket.bucket_arn,
                    data_bucket.arn_for_objects("*"),
                ],
            )
        )

        step_functions_role.add_to_policy(
            iam.PolicyStatement(
                actions=["lambda:InvokeFunction"],
                resources=[fetch_iiif_manifest_function.function_arn, process_ead_function.function_arn],
            )
        )

        # Permission for Bedrock data sync
        step_functions_role.add_to_policy(iam.PolicyStatement(actions=["bedrock:StartIngestionJob"], resources=["*"]))

        # Permission to write results to S3
        step_functions_role.add_to_policy(
            iam.PolicyStatement(
                actions=["s3:PutObject"], resources=[data_bucket.arn_for_objects("step-function-results/*")]
            )
        )

        # Lambda permission to allow invocation from Step Functions
        fetch_iiif_manifest_function.add_permission(
            "AllowStepFunctionsInvoke",
            principal=iam.ServicePrincipal("states.amazonaws.com"),
        )

        # Permission for EAD Lambda
        process_ead_function.add_permission(
            "AllowStepFunctionsInvoke",
            principal=iam.ServicePrincipal("states.amazonaws.com"),
        )

        manifest_fetch_concurrency = self.node.try_get_context("manifest_fetch_concurrency") or 2
        ead_process_concurrency = self.node.try_get_context("ead_process_concurrency") or 10

        # Define EAD processing workflow using Distributed Map
        ead_distributed_map_state = sfn.CustomState(
            self,
            "EadDistributedMapWithItemReader",
            state_json={
                "Type": "Map",
                "ItemReader": {
                    "Resource": "arn:aws:states:::s3:listObjectsV2",
                    "Parameters": {"Bucket.$": "$.s3.Bucket", "Prefix.$": "$.s3.Prefix"},
                },
                "Parameters": {"sourceBucket.$": "$.s3.Bucket", "item.$": "$$.Map.Item.Value"},
                "MaxConcurrency": ead_process_concurrency,
                "ItemProcessor": {
                    "ProcessorConfig": {"Mode": "DISTRIBUTED", "ExecutionType": "STANDARD"},
                    "StartAt": "ProcessEadFile",
                    "States": {
                        "ProcessEadFile": {
                            "Type": "Task",
                            "Resource": "arn:aws:states:::lambda:invoke",
                            "Parameters": {
                                "FunctionName": process_ead_function.function_arn,
                                "Payload": {"bucket.$": "$.sourceBucket", "key.$": "$.item.Key"},
                            },
                            "TimeoutSeconds": 43200,  # 12 hours
                            "End": True,
                        }
                    },
                },
                "ResultWriter": {
                    "Resource": "arn:aws:states:::s3:putObject",
                    "Parameters": {
                        "Bucket": data_bucket.bucket_name,
                        "Prefix": "step-function-results/ead-processing/",
                    },
                },
            },
        )

        # Define Distributed Map with ItemReader using a raw JSON state definition
        distributed_map_state = sfn.CustomState(
            self,
            "IIIFDistributedMapWithItemReader",
            state_json={
                "Type": "Map",
                "ItemReader": {
                    "Resource": "arn:aws:states:::s3:getObject",
                    "ReaderConfig": {"InputType": "CSV", "CSVHeaderLocation": "GIVEN", "CSVHeaders": ["uri", "text"]},
                    "Parameters": {"Bucket.$": "$.s3.Bucket", "Key.$": "$.s3.Key"},
                },
                "MaxConcurrency": manifest_fetch_concurrency,
                "ItemProcessor": {
                    "ProcessorConfig": {"Mode": "DISTRIBUTED", "ExecutionType": "STANDARD"},
                    "StartAt": "InvokeFetchManifest",
                    "States": {
                        "InvokeFetchManifest": {
                            "Type": "Task",
                            "Resource": "arn:aws:states:::lambda:invoke",
                            "Parameters": {
                                "FunctionName": fetch_iiif_manifest_function.function_arn,
                                "Payload": {
                                    "row.$": "$",
                                },
                            },
                            "TimeoutSeconds": 43200,  # 12 hours
                            "End": True,
                        }
                    },
                },
                "ResultWriter": {
                    "Resource": "arn:aws:states:::s3:putObject",
                    "Parameters": {
                        "Bucket": data_bucket.bucket_name,
                        "Prefix": "step-function-results/iiif-processing",
                    },
                },
            },
        )

        # Add bedrock knowledge base ingestion task - shared between both workflows
        start_ingestion = sfn.CustomState(
            self,
            "StartBedrockIngestion",
            state_json={
                "Type": "Task",
                "Parameters": {
                    "DataSourceId": data_source_id,
                    "KnowledgeBaseId": knowledge_base_id,
                },
                "Resource": "arn:aws:states:::aws-sdk:bedrockagent:startIngestionJob",
            },
        )

        # Define the success and failure states
        success = sfn.Succeed(self, "TaskCompleted")
        failure = sfn.Fail(self, "TaskFailed", error="TaskFailedError", cause="Task execution failed")

        # Add a Choice state to determine the workflow
        choice_state = sfn.Choice(self, "DataTypeChoice")
        choice_state.when(
            sfn.Condition.string_equals("$.workflowType", "iiif"),
            run_task.next(distributed_map_state).next(start_ingestion),
        )
        choice_state.when(
            sfn.Condition.string_equals("$.workflowType", "ead"),
            ead_distributed_map_state.next(start_ingestion),
        )
        choice_state.otherwise(failure)

        definition = choice_state.afterwards().next(success)

        self.state_machine = sfn.StateMachine(
            self, "OsdpStackSpinup", definition=definition, timeout=Duration.hours(12), role=step_functions_role
        )

        # Permissions are too broad for now
        # Use the Stack context to access account and region
        stack = Stack.of(self)
        step_functions_role.add_to_policy(
            iam.PolicyStatement(
                actions=["states:StartExecution"],
                resources=[f"arn:aws:states:{stack.region}:{stack.account}:stateMachine:*"],
            )
        )

        # Get workflow type and source info from data_config
        workflow_type = data_config.get("type")

        # Configure environment variables for the trigger based on data_config
        env_vars = {
            "STATE_MACHINE_ARN": self.state_machine.state_machine_arn,
            "BUCKET": data_bucket.bucket_name,
            "WORKFLOW_TYPE": workflow_type,
        }

        # Add type-specific environment variables
        if workflow_type == "iiif":
            env_vars["SOURCE_COLLECTION"] = data_config.get("collection_url", "")
            env_vars["COLLECTION_FILENAME"] = "manifests.csv"
        elif workflow_type == "ead":
            s3_config = data_config.get("s3", {})
            env_vars["SOURCE_PREFIX"] = s3_config.get("prefix", "")
            env_vars["SOURCE_BUCKET"] = s3_config.get("bucket", "")
            # For EAD workflow, source bucket is external, we need to grant permissions
            if "bucket" in s3_config:
                step_functions_role.add_to_policy(
                    iam.PolicyStatement(
                        actions=["s3:ListBucket", "s3:GetObject"],
                        resources=[
                            f"arn:aws:s3:::{s3_config['bucket']}",
                            f"arn:aws:s3:::{s3_config['bucket']}/*",
                        ],
                    )
                )
                process_ead_function.role.add_to_policy(  # Changed: Using correct method add_to_policy on Lambda's role
                    iam.PolicyStatement(
                        actions=["s3:ListBucket", "s3:GetObject"],
                        resources=[
                            f"arn:aws:s3:::{s3_config['bucket']}",
                            f"arn:aws:s3:::{s3_config['bucket']}/*",
                        ],
                    )
                )

        # Add a Lambda trigger for Step Functions execution
        self.step_function_trigger = triggers.TriggerFunction(
            self,
            "TriggerStepFunction",
            runtime=_lambda.Runtime.PYTHON_3_10,
            handler="index.handler",
            environment=env_vars,
            code=_lambda.Code.from_asset("./functions/step_function_trigger"),
            timeout=Duration.minutes(3),
            initial_policy=[
                iam.PolicyStatement(
                    actions=["states:StartExecution"],
                    resources=[self.state_machine.state_machine_arn],
                )
            ],
            execute_on_handler_change=False,
        )

        # Ensure the trigger function executes only after these resources are provisioned
        self.step_function_trigger.execute_after(self.state_machine)
        self.step_function_trigger.execute_after(data_bucket)
        self.step_function_trigger.execute_after(fetch_iiif_manifest_function)
        self.step_function_trigger.execute_after(knowledge_base)
        self.step_function_trigger.execute_after(data_source)
        self.step_function_trigger.execute_after(process_ead_function)
