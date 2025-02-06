from aws_cdk import Stage

from constructs import Construct
from stacks.osdp_prototype_stack import OsdpPrototypeStack


class OsdpApplicationStage(Stage):
    def __init__(self, scope: Construct, id: str, **kwargs):
        super().__init__(scope, id, **kwargs)
        OsdpPrototypeStack(
            self,
            "OSDP-Prototype"
        )
