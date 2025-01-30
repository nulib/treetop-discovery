import aws_cdk as core
import aws_cdk.assertions as assertions

from osdp_cdk import OsdpPrototypeStack


# example tests. To run these tests, uncomment this file along with the example
# resource in source/source_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = OsdpPrototypeStack(app, "OsdpPrototypeStack")
    _template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
