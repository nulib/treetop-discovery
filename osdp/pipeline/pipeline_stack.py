#!/usr/bin/env python3
import aws_cdk as cdk
from aws_cdk import SecretValue, pipelines
from aws_cdk import aws_ssm as ssm
from constructs import Construct
from pipeline.osdp_application_stage import OsdpApplicationStage


class PipelineStack(cdk.Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Define the CodePipeline source
        source = pipelines.CodePipelineSource.git_hub(
            "nulib/treetop-discovery",
            "main",
            authentication=SecretValue.secrets_manager("osdp/github-token"),
        )

        # Fetch the single configuration JSON string from SSM Parameter Store
        config_json_param = ssm.StringParameter.from_string_parameter_name(
            self,
            "ConfigJsonParam",
            "/osdp/staging/config",  # Parameter containing the JSON config
        )

        # CDK Tokens cannot be processed during synthesis phase directly in Python logic.
        # We need to pass the SSM parameter reference into the ShellStep environment
        # and process it within the shell commands using `aws ssm get-parameter`.
        # Alternatively, and more cleanly, pass individual parameters as done previously.
        # However, sticking to the "single entity" requirement, we'll try a different approach:
        # Pass the parameter name to the ShellStep and resolve it inside the shell commands.

        # Define the synth step.
        synth = pipelines.ShellStep(
            "Synth",
            input=source,
            # Pass the SSM parameter name as an environment variable
            env={"CONFIG_PARAM_NAME": config_json_param.parameter_name},
            commands=[
                "npm install -g aws-cdk",
                "pip install uv",
                # Install jq using dnf (common in Amazon Linux 2/2023) or apt-get (Ubuntu)
                # The '|| true' prevents failure if one command doesn't exist or jq is already installed
                "sudo dnf install -y jq || true",
                "sudo dnf install -y libxcrypt-compat || true",
                "uv sync --no-dev",
                ". .venv/bin/activate",
                "cd osdp",
                "cdk --version",
                # Fetch the JSON config from SSM within the shell
                "echo 'Fetching config from SSM parameter: $CONFIG_PARAM_NAME'",
                # The complex shell command using jq to parse JSON and build synth args
                """
                CONFIG_JSON=$(aws ssm get-parameter \\
                  --name "$CONFIG_PARAM_NAME" --query Parameter.Value --output text) && \\
                SYNTH_ARGS=$(echo "$CONFIG_JSON" | jq -r '
                  to_entries | map(
                    if .key == "data" then
                      .value | to_entries | map("-c data.\\(.key)='\\''\(.value)'\\''") | join(" ")
                    else
                      "-c \\(.key)='\\''\(.value)'\\''"
                    end
                  ) | join(" ")
                ') && \\
                echo "Running cdk synth with args: $SYNTH_ARGS" && \\
                cdk synth $SYNTH_ARGS
                """,
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
                    "cd osdp",
                    "pytest -vv tests/",
                ],
            )
        )

        # Define the application stages
        # The stack_prefix will be passed through the context by the synth step
        deploy_stage = OsdpApplicationStage(
            self, "staging", env=cdk.Environment(account="625046682746", region="us-east-1")
        )
        pipeline.add_stage(deploy_stage)
