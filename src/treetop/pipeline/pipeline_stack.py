#!/usr/bin/env python3
import aws_cdk as cdk
from aws_cdk import SecretValue, pipelines
from aws_cdk import aws_ssm as ssm
from constructs import Construct

from treetop.pipeline.treetop_application_stage import TreetopApplicationStage


class PipelineStack(cdk.Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Define the CodePipeline source
        source = pipelines.CodePipelineSource.git_hub(
            "nulib/treetop-discovery",
            "main",
            authentication=SecretValue.secrets_manager("treetop/github-token"),
        )

        # Get stack_prefix and other configs from parameter store
        config_param = ssm.StringParameter.from_string_parameter_name(self, "ConfigParam", "/treetop/staging/config")

        synth = pipelines.ShellStep(
            "Synth",
            input=source,
            commands=[
                "npm install -g aws-cdk",
                "pip install uv",
                "sudo dnf install -y libxcrypt-compat || true",
                "uv sync --no-dev",
                ". .venv/bin/activate",
                "cdk --version",
                f"cdk synth {config_param.string_value}",
            ],
            primary_output_directory="treetop/cdk.out",
        )

        # Define the CodePipeline using CDK Pipelines
        pipeline = pipelines.CodePipeline(
            self,
            "TreetopPipeline",
            synth=synth,
        )

        validation_wave = pipeline.add_wave("Validation")

        validation_wave.add_pre(
            pipelines.ShellStep(
                "Lint",
                input=source,
                commands=["pip install uv", "uv sync --only-dev", ". .venv/bin/activate", "ruff check ."],
            )
        )

        validation_wave.add_pre(
            pipelines.ShellStep(
                "Style",
                input=source,
                commands=["pip install uv", "uv sync --only-dev", ". .venv/bin/activate", "ruff format --check ."],
            )
        )

        validation_wave.add_pre(
            pipelines.ShellStep(
                "Test",
                input=source,
                commands=[
                    "npm install -g aws-cdk",
                    "pip install uv",
                    "uv sync",
                    ". .venv/bin/activate",
                    "pytest -vv tests/",
                ],
            )
        )

        # Define the application stages
        # The stack_prefix will be passed through the context by the synth step
        deploy_stage = TreetopApplicationStage(
            self, "staging", env=cdk.Environment(account=self.account, region=self.region)
        )
        pipeline.add_stage(deploy_stage)
