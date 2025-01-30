def handler(event, context):
  import boto3
  import os

  sfn = boto3.client('stepfunctions')
  sfn.start_execution(
      stateMachineArn=os.environ['STATE_MACHINE_ARN'],
      name='CDKTriggeredExecution',
      input=f'{{"collection_url": "{os.environ["COLLECTION_URL"]}"}}'
  )