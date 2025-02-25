#!/usr/bin/env python3
import aws_cdk as cdk
from aws_cdk import SecretValue, pipelines

from constructs import Construct
from pipeline.osdp_application_stage import OsdpApplicationStage


class PipelineStack(cdk.Stack):
    def __init__(self, scope: Construct, construct_id: str, stack_prefix: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Define the CodePipeline source
        source = pipelines.CodePipelineSource.git_hub(
            "nulib/osdp-prototype-cdk",
            "main",
            authentication=SecretValue.secrets_manager("osdp/github-token"),
        )

        # Define the synth step.
        # Pass the context parameters including stack_prefix set to "staging".
        synth = pipelines.ShellStep(
            "Synth",
            input=source,
            commands=[
                "cd osdp",
                "pip install -r requirements.txt -r requirements-dev.txt",
                "npm install -g aws-cdk",
                "cd functions/build_function",
                "npm install",
                "cd ../../",
                "cdk --version",
                f"cdk synth -c stack_prefix={stack_prefix}",
            ],
            primary_output_directory="osdp/cdk.out",
        )

        # Define the CodePipeline using CDK Pipelines
        pipeline = pipelines.CodePipeline(
            self,
            "OsdpPipeline",
            synth=synth,
        )

        validation_wave = pipeline.add_wave("Validation")

        validation_wave.add_pre(
            pipelines.ShellStep(
                "Lint",
                input=source,
                commands=["cd osdp", "pip install -r requirements-dev.txt", "ruff check ."],
            )
        )

        validation_wave.add_pre(
            pipelines.ShellStep(
                "Style",
                input=source,
                commands=["cd osdp", "pip install -r requirements-dev.txt", "ruff format --check ."],
            )
        )

        validation_wave.add_pre(
            pipelines.ShellStep(
                "Test",
                input=source,
                commands=[
                    "cd osdp",
                    "pip install -r requirements.txt -r requirements-dev.txt",
                    "npm install -g aws-cdk",
                    "pytest -vv tests/",
                ],
            )
        )

        # Define the application stages
        deploy_stage = OsdpApplicationStage(
            self, "staging", stack_prefix=stack_prefix, env=cdk.Environment(account="625046682746", region="us-east-1")
        )
        pipeline.add_stage(deploy_stage)
