import aws_cdk as core
import aws_cdk.assertions as assertions

from source.source_stack import OSDPPrototype

# example tests. To run these tests, uncomment this file along with the example
# resource in source/source_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = OSDPPrototype(app, "source")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
