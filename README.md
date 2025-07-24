# Treetop Discovery

## About the Project

## Getting Started

### Prerequisites

To get started you will need to have the following installed:

- `uv` ([installation instructions](https://github.com/astral-sh/uv))
- `aws` cli ([installation instructions](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html))
- AWS cdk cli (see [install instructions)](https://docs.aws.amazon.com/cdk/v2/guide/getting_started.html))

> [!NOTE]
> If you don't have `uv` installed (or don't want to), see [alternate instructions](#install-uv-with-python) below.

### Install

Install dependencies in a virtual environment:

```bash
uv sync --all-groups
```

Activate the virtual environment:

```bash
source .venv/bin/activate
```

While logged into aws, verify that it will build:

```bash
cd osdp && cdk synth
```

> [!IMPORTANT]
> If cdk cannot locate the python deps, restarting your shell will typically fix it.

### Configuration

Your application configuration values should be provided in a file named `osdp/config.toml`. (An example of the format is provided in `config.toml.example`)

```toml
stack_prefix = "my-stack"
embedding_model_arn = ""
foundation_model_arn = ""
manifest_fetch_concurrency = 15
ead_process_concurrency = 10

[ecr]
# The full repository path is composed of {registry}/{repository}:{tag}
# e.g. public.ecr.aws/nulib-staging/osdp-iiif-fetcher:latest
registry = "public.ecr.aws"
repository = "nulib-staging/osdp-iiif-fetcher"
tag = "latest"

[data]
type = "iiif"
collection_url = "https://api.dc.library.northwestern.edu/api/v2/collections/ecacd539-fe38-40ec-bbc0-590acee3d4f2?as=iiif"

# Alternatively, for EAD data use the following structure for data
# [data]
# type = "ead"

# [data.s3]
# bucket = "my-bucket"
# prefix = "my-prefix

[tags]
project = "my-project"
```

##### Description

- `stack_prefix` (str)(Required) - will be appended to the beginning of the CloudFormation stack on deploy. (*For NU devs this is not needed, it will use the `DEV_PREFIX` env var in AWS.)
- `ecr` (dict)(Required) - Describes the ECR repository to use for the IIIF manifest fetcher.
- `data` (dist)(Required) - Describes either the IIIF collection url or S3 location of EAD source XML files to load on initial app creation.
- `embedding_model_arn` (str)(Required) - Embedding model to use for Bedrock Knowledgebase
- `foundation_model_arn` (str)(Required) - Foundation model to use for Bedrock RetreiveAndGenerate invocations
- `tags` (dict) - Key value pair tags applied to all resources in the stack. 
- `manifest_fetch_concurrency` (str) - The concurrency to use when retrieving IIIF manifests from your API. 
- `ead_process_concurrency` (str) - The concurrency to use when processing EAD files. 

### Deploy

Run the deploy command, providing the name of your stack. (This will be your `stack_prefix` + `_OSDP_Prototype`. It can also be obtained by running `cdk ls`:

```bash
cd osdp && cdk ls

mystack-OSDP-Prototype # <-- it's this one
OsdpPipelineStack
OsdpPipelineStack/staging/OSDP-Prototype 
```

Deploy
```bash
cd osdp && cdk deploy mystack-OSDP-Prototype
```

## Permissions

This application creates several IAM roles and policies to ensure that the different AWS services have the necessary permissions to interact with each other securely.

### API
- **Cognito User Pool**: Manages user authentication.
- **Chat Lambda Function**:
  - Granted permissions to interact with Amazon Bedrock for invoking models (`bedrock:InvokeModel`), retrieving data (`bedrock:Retrieve`), and generating responses (`bedrock:RetrieveAndGenerate`).
  - The API Gateway uses a Cognito authorizer to protect the chat endpoint.

### Database
- **RDS Cluster Security Group**: Allows inbound traffic on port 5432 from within the VPC, enabling services like Bedrock to connect to the database.
- **Database Initialization**: A custom resource is granted permissions to execute SQL statements on the RDS cluster (`rds-data:ExecuteStatement`) and retrieve database credentials from AWS Secrets Manager (`secretsmanager:GetSecretValue`).

### Data Ingestion
- **ECS Task Role**: The ECS task for fetching IIIF manifests is granted `s3:PutObject` permissions to write data to the S3 data bucket.
- **Step Functions**:
  - The Step Function orchestrating the data pipeline has permissions to invoke Lambda functions (`fetch_iiif_manifest_function`, `process_ead_function`) and run the ECS task.
  - The Lambda functions for processing IIIF and EAD data are granted read and write access to the S3 data bucket.

### Knowledge Base
- **Bedrock Knowledge Base Role**: A role is created for the Bedrock Knowledge Base with permissions to:
  - Read data from the S3 bucket.
  - Access the RDS database cluster for vector storage.
  - Invoke the embedding model in Bedrock.
  - Retrieve database credentials from AWS Secrets Manager.

### CI/CD Pipeline
- **CodePipeline**: The pipeline is configured with a source from GitHub and uses a secret from AWS Secrets Manager for authentication.
- **Pipeline Stages**: The linting, testing, and deployment steps in the pipeline have the necessary permissions to install dependencies, run commands, and deploy the CDK application.

### UI
- **Amplify Build Function**: A Lambda function for building the UI is granted permissions to create and start deployments in AWS Amplify.

## Architecture

![Step Functions Graph](images/stepfunctions_graph.png)

The core of the project is an AWS Step Function that orchestrates the data ingestion process. The workflow begins by checking the `workflowType` to determine whether to process IIIF or EAD data. For IIIF data, it fetches manifest URLs from a collection API, processes each manifest using a Lambda function, and stores the results in S3. For EAD data, it processes XML files from a specified S3 location. Both workflows conclude by initiating a Bedrock ingestion job to make the data available for search and retrieval.

#### Loading additional data

Additional data can be loaded by manually invoking the step function.

* Note that to load EAD data if you had initially run a IIIF load you will need to grant S3 `GetObject` and `ListObjects` permissions to both the state machine and the EAD processing lambda.

Example state machine input for IIIF load:
```json
{
  "s3": {
    "Bucket": "your-s3-bucket-name",
    "Key": "manifests.csv"
  },
  "workflowType": "iiif",
  "collection_url": "https://api.dc.library.northwestern.edu/api/v2/collections/your-collection-id?as=iiif"
}
```
Example state machine input for EAD load: 
```json
{
  "s3": {
    "Bucket": "your-s3-bucket-name",
    "Prefix": "path/to/your/ead/files/"
  },
  "workflowType": "ead"
}
```

### Install `uv` with Python

To install `uv` locally

Ensure you are using Python 3.10:

```bash
python --version
# Python 3.10.5
```

Create a virtual environment:

```bash
python -m venv .venv
```

Activate it:

```bash
source .venv/bin/activate
```

Install `uv` within the virutual environment:

```bash
pip install uv
```

Install dependencies:

```bash
uv sync --all-groups
```

## Development

### IIIF manifest fetcher docker image

This is a ECR repository that is consumed by the OSDP.

See its [readme](iiif/README.md) for more information.

#### Building and Pushing the Image

To build and push the image to ECR, run the following commands from the project root:

```bash
aws ecr-public get-login-password --region us-east-1 | docker login --username AWS --password-stdin public.ecr.aws/nulib-staging
docker build -t public.ecr.aws/nulib-staging/osdp-iiif-fetcher:[tag] -f iiif/Dockerfile .
docker push public.ecr.aws/nulib-staging/osdp-iiif-fetcher:[tag]
```

> [!NOTE]
> Replace `[tag]` with the new version tag for the image. The default should be "latest"

### OSDP Prototype Stack (CDK)

#### Setup

The OSDP primarily uses Python, but NodeJS is used for one lambda.

##### Python

Follow the steps in the [quickstart](#quick-start-)

> [!TIP]
> If using VSCode, set your Python interpreter by opening the Command Palette `⇧⌘P` and choosing `Python: Select Interpreter`.
> Set the path to `./.venv/bin/python`.
> Read more [here](https://code.visualstudio.com/docs/python/environments#_working-with-python-interpreters).


##### Node

Ensure using v22:

```bash
node --version
# v22.13.1
```

There is one lambda that uses node:

```bash
cd functions/build_function
npm i
cd ../../
```

#### Testing

To run the tests.

```bash
pytest
```

If the app has not been synthesized, tests may fail. See [synth instructions](#synthesize-the-cloudformation-template-optional).

#### Linting

```bash
ruff check .
```

or

```bash
ruff check --fix .
```

#### Style

To run formatting

```bash
ruff format .
```

## Useful commands

Useful `cdk` commands to be run within the `osdp/` directory:

 * `cdk ls`          list all stacks in the app
 * `cdk synth`       emits the synthesized CloudFormation template
 * `cdk deploy`      deploy this stack to your default AWS account/region
 * `cdk diff`        compare deployed stack with current state
 * `cdk docs`        open CDK documentation

Enjoy!
