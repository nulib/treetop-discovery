# ui_construct.py
from typing import Optional

from aws_cdk import App, BundlingOptions, CfnOutput, Duration, Fn, Size, Stack, triggers
from aws_cdk import aws_amplify_alpha as amplify
from aws_cdk import aws_iam as iam
from aws_cdk import (
    aws_lambda as _lambda,
)
from aws_cdk import aws_secretsmanager as secretsmanager

from constructs import Construct


class AmplifyAuthContext:
    """
    Holds Amplify authentication context values from the CDK application.

    This class retrieves optional authentication-related context values from the CDK context,
    either from `cdk.json` or CLI parameters.

    Attributes
    ----------
    secret_name : Optional[str]
        The name of the AWS Secrets Manager secret used for authentication (default: "OSDPSecrets").
        Use `NO_AUTH` keyword to disable authentication.
    username_key : str
        The key for the username field within the secret (default: "username").
    password_key : str
        The key for the password field within the secret (default: "password").

    Examples
    --------
    Pass context values using the CDK CLI:

    ```
    cdk deploy
        -c amplify.auth.secret_name=MySecret
        -c amplify.auth.username_key=myUserKey
        -c amplify.auth.password_key=myPassKey
    ```

    If not provided, `username_key` and `password_key` default to `"username"` and `"password"`, respectively.

    Parameters
    ----------
    app : App
        The CDK App object from which to retrieve context values.
    """

    def __init__(self, app: App):
        context_name = self._get_optional_context(app, "amplify.auth.secret_name")
        self.secret_name: str = (
            "OSDPSecrets" if context_name is None else (None if context_name == "NO_AUTH" else context_name)
        )
        self.username_key: str = self._get_optional_context(app, "amplify.auth.username_key") or "username"
        self.password_key: str = self._get_optional_context(app, "amplify.auth.password_key") or "password"

    @staticmethod
    def _get_optional_context(app: App, key: str) -> Optional[str]:
        """
        Retrieve an optional context value from the CDK application.

        :param app: The CDK App object.
        :param key: The context key to retrieve.
        :return: The context value if available, otherwise `None`.
        """
        return app.node.try_get_context(key) or None


class UIConstruct(Construct):
    def __init__(
        self, scope: Construct, id: str, *, stack_id: str, api_url: str, auth_context: AmplifyAuthContext, **kwargs
    ) -> None:
        super().__init__(scope, id)

        stack = Stack.of(self)
        app_name = Fn.join("-", [stack.stack_name.lower(), "ui", stack_id])
        app_branch_name = "main"

        if auth_context.secret_name:
            secret = secretsmanager.Secret.from_secret_name_v2(
                self,
                "AmplifyAuthSecret",
                secret_name=auth_context.secret_name,
            )

            username = secret.secret_value_from_json(auth_context.username_key).unsafe_unwrap()
            password = secret.secret_value_from_json(auth_context.password_key)

            basic_auth = amplify.BasicAuth(
                username=username,
                password=password,
            )
        else:
            basic_auth = None

        self.amplify_app = amplify.App(
            self,
            "AmplifyApp",
            app_name=app_name,
            auto_branch_creation=amplify.AutoBranchCreation(
                auto_build=False,
            ),
            basic_auth=basic_auth,
        )

        self.amplify_branch = self.amplify_app.add_branch(app_branch_name)

        self.build_function = triggers.TriggerFunction(
            self,
            "BuildFunction",
            runtime=_lambda.Runtime.NODEJS_22_X,
            handler="index.handler",
            code=_lambda.Code.from_asset(
                "./functions/build_function",
                bundling=BundlingOptions(
                    image=_lambda.Runtime.NODEJS_22_X.bundling_image,
                    user="root",
                    command=["bash", "-c", "npm i && cp -r . /asset-output/"],
                ),
            ),
            environment={
                "REPO_NAME": "osdp-prototype-ui",
                "NEXT_PUBLIC_API_URL": api_url,
                "AMPLIFY_APP_ID": self.amplify_app.app_id,
                "AMPLIFY_BRANCH_NAME": app_branch_name,
            },
            timeout=Duration.minutes(5),  # TODO: Build times are nearing this limit
            memory_size=1024,
            ephemeral_storage_size=Size.gibibytes(1),
            initial_policy=[
                iam.PolicyStatement(
                    actions=["amplify:CreateDeployment", "amplify:StartDeployment"],
                    resources=[
                        self.amplify_branch.arn,
                        f"{self.amplify_branch.arn}/*",
                    ],
                )
            ],
        )

        # Add the Git layer to the build function
        self.build_function.add_layers(
            _lambda.LayerVersion.from_layer_version_arn(
                self,
                "GitLayer",
                layer_version_arn="arn:aws:lambda:us-east-1:553035198032:layer:git-lambda2:8",
            )
        )

        self.build_function_url = self.build_function.add_function_url(
            auth_type=_lambda.FunctionUrlAuthType.AWS_IAM,
        )

        self.build_function.node.add_dependency(self.amplify_app)

        CfnOutput(self, "buildFunctionUrl", value=self.build_function_url.url)
        CfnOutput(
            self,
            "Website URL",
            value=f"https://{app_branch_name}.{self.amplify_app.default_domain}",
            description="URL for UI hosted on Amplify",
        )
