from aws_cdk import Stage
from aws_cdk import aws_iam as iam
from constructs import Construct

from treetop.stacks.treetop_stack import TreetopStack


class TreetopApplicationStage(Stage):
    def __init__(self, scope: Construct, id: str, **kwargs):
        super().__init__(scope, id, **kwargs)

        github_action_arn = f"arn:aws:iam::{self.account}:oidc-provider/token.actions.githubusercontent.com"

        principal = iam.WebIdentityPrincipal(
            github_action_arn,
            conditions={"StringLike": {"token.actions.githubusercontent.com:sub": "repo:nulib/osdp-prototype-ui:*"}},
        )

        TreetopStack(self, "Treetop", ui_function_invoke_principal=principal)
