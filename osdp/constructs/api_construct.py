from aws_cdk import (
    CfnOutput,
)
from aws_cdk import (
    aws_lambda as _lambda,
)

from constructs import Construct


class ApiConstruct(Construct):
    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # Hello World Function
        # This is a standin for our API at the moment
        my_function = _lambda.Function(
            self,
            "HelloWorldFunction",
            runtime=_lambda.Runtime.NODEJS_20_X,  # Provide any supported Node.js runtime
            handler="index.handler",
            code=_lambda.Code.from_inline(
                """
                exports.handler = async function(event) {
                return {
                    headers: {
                        "Access-Control-Allow-Origin" : "*",
                        "Access-Control-Allow-Credentials" : true
                    },
                    statusCode: 200,
                    body: JSON.stringify('Hello World!'),
                };
                };
                """
            ),
        )

        # Define the Lambda function URL resource
        self.api_url = my_function.add_function_url(
            auth_type=_lambda.FunctionUrlAuthType.NONE,
        )

        # Define a CloudFormation output for your URL
        CfnOutput(self, "apiUrlOutput", value=self.api_url.url)
