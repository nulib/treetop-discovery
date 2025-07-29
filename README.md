# Treetop Discovery

Treetop Discovery is an AWS CDK-based data discovery platform that builds searchable knowledge bases from IIIF (International Image Interoperability Framework) manifests and EAD (Encoded Archival Description) files using Amazon Bedrock.

## Quick Start for Simple Deployment

> [!WARNING]
> **Initial data loading can take several hours for large collections** and the UI will show CORS errors until data sync completes. See [Monitoring Data Loading Progress](#monitoring-data-loading-progress) below.

### AWS Requirements

- **AWS Account**: Administrator permissions recommended
- **AWS Regions**: Deploy in a region where Amazon Bedrock is available (e.g., us-east-1, us-west-2)
- **Bedrock Model Access**: Enable access to embedding and foundation models in the Bedrock console

### Prerequisites

Install these tools on your local machine:

- `uv` ([installation instructions](https://github.com/astral-sh/uv))
- `aws` cli ([installation instructions](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)) 
- AWS CDK cli ([installation instructions](https://docs.aws.amazon.com/cdk/v2/guide/getting_started.html))
- AWS CLI configured with your credentials (`aws configure`)

> [!NOTE]
> If you don't have `uv` installed, see [alternate Python setup](#alternative-python-setup-without-uv) below.

### Step 1: Install Dependencies

```bash
# Clone the repository and navigate to it
git clone https://github.com/nulib/treetop-discovery.git
cd treetop-discovery

# Install Python dependencies
uv sync --all-groups

# Activate virtual environment
source .venv/bin/activate

# Install Node.js dependencies for build function
cd osdp/functions/build_function && npm i && cd ../../../

# Verify CDK can build (while in project root)
cd osdp && cdk synth && cd ..
```

> [!IMPORTANT]
> If CDK cannot locate Python dependencies, restart your shell and re-activate the virtual environment.

### Step 2: Configuration

> [!IMPORTANT]
> **Choose Your Data Source Type First**: Treetop Discovery supports two data source types - **IIIF** or **EAD**. You must choose one during initial deployment. Additional data sources can be added later.

Create your configuration file:

```bash
cp osdp/config.toml.example osdp/config.toml
```

**For IIIF Data Sources** (digital collections with IIIF manifests):

```toml
stack_prefix = "my-treetop"  # Choose your stack name prefix
embedding_model_arn = "arn:aws:bedrock:us-east-1::foundation-model/amazon.titan-embed-text-v1"
foundation_model_arn = "arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-v2"

[ecr]
registry = "public.ecr.aws"
repository = "nulib-staging/osdp-iiif-fetcher"
tag = "latest"

[data]
type = "iiif"
collection_url = "https://your-iiif-collection-api-url"

[tags]
project = "my-project"
```

**For EAD Data Sources** (archival XML files in S3):

```toml
stack_prefix = "my-treetop"  # Choose your stack name prefix
embedding_model_arn = "arn:aws:bedrock:us-east-1::foundation-model/amazon.titan-embed-text-v1"
foundation_model_arn = "arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-v2"

# Note: ECR section not needed for EAD workflows

[data]
type = "ead"

[data.s3]
bucket = "your-s3-bucket-name"
prefix = "path/to/ead/files/"

[tags]
project = "my-project"
```

**Key Configuration Notes:**
- Replace Bedrock model ARNs with ones available in your AWS region
- **IIIF**: Requires your collection API URL and uses ECS container for manifest fetching
- **EAD**: Requires S3 bucket/prefix where your EAD XML files are stored
- ECR configuration only needed for IIIF workflows (uses Northwestern's public repository)

### Step 3: Deploy

```bash
# Navigate to CDK directory
cd osdp

# List available stacks to confirm name
cdk ls
# Output will show: my-treetop-OSDP-Prototype

# Deploy the stack
cdk deploy my-treetop-OSDP-Prototype
```

> [!TIP]
> **AWS SSO Users**: If using AWS SSO, you may need to run `aws sts get-caller-identity` before CDK commands to refresh credentials.

### Step 4: Monitor Deployment

CDK will deploy approximately 15-20 AWS resources including databases, compute services, storage, and AI/ML components. The deployment typically takes 10-15 minutes.

**Required AWS Permissions:**
This deployment requires Administrator permissions or a custom policy with extensive permissions across S3, RDS, Lambda, Step Functions, Bedrock, Cognito, API Gateway, Amplify, ECS, and IAM.

#### CloudFormation Stack Outputs

After deployment completes check the bottom for relevant stack outputs (if you miss them, just go to: AWS Console → CloudFormation → Your Stack → Outputs tab):

- `Website URL`: Your Amplify application URL 
- `ApiUrl`: Your API Gateway endpoint URL
- `UserPoolId`: Cognito User Pool ID (needed for creating users)
- `KnowledgeBaseId`: Bedrock Knowledge Base ID

> [!TIP]
> Save the `UserPoolId` and `UserPoolIdWebsite URL` from outputs. You'll need the `UserPoolId` to create Cognito users in the next step. `Website URL` is your application URL which can be retrieved manually by following step 6 below.

### Step 5: Create User Account

Before accessing the UI, create Cognito users using the `UserPoolId` from your stack outputs:

1. **Via AWS Console**:
   - Go to Amazon Cognito → User Pools
   - Select your pool (named `<stack-prefix>-user-pool`)
   - Click "Create user"
   - Set username, temporary password, and email
   - User must change password on first login

2. **Via CLI** (using UserPoolId from stack outputs):
   ```bash
   aws cognito-idp admin-create-user \
     --user-pool-id <UserPoolId-from-stack-outputs> \
     --username john.doe \
     --user-attributes Name=email,Value=john@example.com \
     --temporary-password TempPass123! \
     --message-action SUPPRESS
   ```

### Step 6: Locate and Test Your Application

Your application URL is available in the stack outputs as `Website URL`. If you need to find it manually:

1. **Via AWS Console**: Go to AWS Amplify → Apps → `<your-prefix>-ui-<suffix>` → View App
2. **Via CLI**: 
   ```bash
   aws amplify list-apps --query 'apps[?contains(name,`my-treetop-ui`)].{Name:name,Domain:defaultDomain}' --output table
   ```

The URL format is: `https://main.<app-id>.amplifyapp.com`

**Testing Access:**
- Navigate to your application URL
- Log in with the Cognito user credentials you created
- The chat interface should be available once data loading completes

### Step 7: Load Additional Data

After your initial deployment, you can load additional datasets by manually invoking the Step Function:

**For Additional IIIF Collections:**
1. Go to AWS Console → Step Functions
2. Select your state machine: `<stack-prefix>-data-pipeline`
3. Click "Start execution"
4. Use this JSON input (replace bucket name with your deployment's S3 bucket):
```json
{
  "s3": {
    "Bucket": "your-s3-bucket-name",
    "Key": "manifests.csv"
  },
  "workflowType": "iiif",
  "collection_url": "https://your-new-collection-api-url"
}
```

**For Additional EAD Files:**
1. Upload your EAD XML files to your S3 bucket
2. Go to AWS Console → Step Functions  
3. Select your state machine: `<stack-prefix>-data-pipeline`
4. Click "Start execution"
5. Use this JSON input (replace bucket name with your deployment's S3 bucket):
```json
{
  "s3": {
    "Bucket": "your-s3-bucket-name", 
    "Prefix": "path/to/new/ead/files/"
  },
  "workflowType": "ead"
}
```

> [!NOTE]
> To load EAD data after initially deploying with IIIF, you must grant S3 `GetObject` and `ListObjects` permissions to both the state machine and EAD processing Lambda function.

### Monitoring Data Loading Progress

**Initial data loading takes hours and the UI shows CORS errors until complete.**

Monitor progress in AWS Console:

1. **Step Functions**: AWS Console → Step Functions → `<prefix>-data-pipeline` → View execution progress
2. **Bedrock Knowledge Base**: AWS Console → Bedrock → Knowledge bases → Your KB → Data source → Sync jobs
3. **CloudWatch Logs**: Monitor Lambda function logs for processing details
4. **S3 Bucket**: Check `<stack-name>-<suffix>` bucket for processed data files

**The UI becomes accessible only after:**
- Step Function execution completes successfully
- Bedrock Knowledge Base sync reaches "Ready" status
- All Lambda functions finish processing

---

## Advanced Topics

### Architecture

![Step Functions Graph](images/stepfunctions_graph.png)

Treetop Discovery uses AWS CDK (Cloud Development Kit) to define and deploy cloud infrastructure as code. The CDK application creates the following AWS resources:

**Core Infrastructure:**
- S3 bucket for data storage
- RDS Aurora PostgreSQL cluster for vector storage
- VPC with subnets and security groups

**Data Processing:**
- Step Functions state machine for data ingestion
- Lambda functions for IIIF/EAD processing
- ECS tasks for IIIF manifest fetching (IIIF workflows only)

**AI/ML Services:**
- Amazon Bedrock Knowledge Base
- IAM roles for Bedrock access

**User Interface:**
- Amazon Cognito User Pool for authentication
- API Gateway with Lambda backend
- AWS Amplify app for frontend hosting

The core of the data processing is an AWS Step Function that orchestrates the ingestion workflow. The process begins by checking the `workflowType` to determine whether to process IIIF or EAD data. For IIIF data, it fetches manifest URLs from a collection API, processes each manifest using a Lambda function, and stores the results in S3. For EAD data, it processes XML files from a specified S3 location. Both workflows conclude by initiating a Bedrock ingestion job to make the data available for search and retrieval.

### Permissions

This application creates several IAM roles and policies to ensure that the different AWS services have the necessary permissions to interact with each other securely.

#### API
- **Cognito User Pool**: Manages user authentication.
- **Chat Lambda Function**:
  - Granted permissions to interact with Amazon Bedrock for invoking models (`bedrock:InvokeModel`), retrieving data (`bedrock:Retrieve`), and generating responses (`bedrock:RetrieveAndGenerate`).
  - The API Gateway uses a Cognito authorizer to protect the chat endpoint.

#### Database
- **RDS Cluster Security Group**: Allows inbound traffic on port 5432 from within the VPC, enabling services like Bedrock to connect to the database.
- **Database Initialization**: A custom resource is granted permissions to execute SQL statements on the RDS cluster (`rds-data:ExecuteStatement`) and retrieve database credentials from AWS Secrets Manager (`secretsmanager:GetSecretValue`).

#### Data Ingestion
- **ECS Task Role**: The ECS task for fetching IIIF manifests is granted `s3:PutObject` permissions to write data to the S3 data bucket.
- **Step Functions**:
  - The Step Function orchestrating the data pipeline has permissions to invoke Lambda functions (`fetch_iiif_manifest_function`, `process_ead_function`) and run the ECS task.
  - The Lambda functions for processing IIIF and EAD data are granted read and write access to the S3 data bucket.

#### Knowledge Base
- **Bedrock Knowledge Base Role**: A role is created for the Bedrock Knowledge Base with permissions to:
  - Read data from the S3 bucket.
  - Access the RDS database cluster for vector storage.
  - Invoke the embedding model in Bedrock.
  - Retrieve database credentials from AWS Secrets Manager.

#### CI/CD Pipeline
- **CodePipeline**: The pipeline is configured with a source from GitHub and uses a secret from AWS Secrets Manager for authentication.
- **Pipeline Stages**: The linting, testing, and deployment steps in the pipeline have the necessary permissions to install dependencies, run commands, and deploy the CDK application.

#### UI
- **Amplify Build Function**: A Lambda function for building the UI is granted permissions to create and start deployments in AWS Amplify.

### Alternative Python Setup (without uv)

If you prefer not to use `uv`, you can set up the environment with standard Python tools:

Ensure you are using Python 3.12:

```bash
python --version
# Python 3.12.x
```

Create a virtual environment:

```bash
python -m venv .venv
```

Activate it:

```bash
source .venv/bin/activate
```

Install `uv` within the virtual environment:

```bash
pip install uv
```

Install dependencies:

```bash
uv sync --all-groups
```


### Troubleshooting

**Common Issues:**

1. **CDK synthesis fails**: Restart your shell and re-activate the virtual environment
2. **Bedrock model access denied**: Enable model access in the Bedrock console for your region
3. **UI shows CORS errors**: Wait for data loading to complete (can take hours)
4. **Authentication errors with AWS SSO**: Run `aws sts get-caller-identity` to refresh credentials

---

## Northwestern University Development

> [!NOTE] 
> This section is specific to Northwestern University developers and staging environments.

### NU Development Environment

**Step 1: Clone Repository**
```bash
git clone https://github.com/nulib/treetop-discovery.git
cd treetop-discovery
```

Follow the main [Quick Start](#quick-start-for-simple-deployment) steps 1-2 for installation and configuration.

**Step 2: Authentication Setup (Required before Step 3)**
1. Go to [aws.northwestern.edu](https://aws.northwestern.edu)
2. Click the "GENERAL USE LOGIN" button
3. Expand the name of the AWS staging account
4. Hit the "Access keys" button
5. Choose "Option 1: Set AWS environment variables"
6. Copy and paste the commands into your terminal

> [!IMPORTANT]
> Complete the authentication setup above before running `cdk synth` or `cdk deploy` in Step 3, or you'll get authentication errors.

**Configuration Notes:**
For NU developers, the `stack_prefix` is automatically set using the `DEV_PREFIX` environment variable in AWS, so it can be omitted from `config.toml`.

### NU Staging Pipeline

The project includes a CI/CD pipeline for staging deployments:

- **Pipeline Stack**: `OsdpPipelineStack` 
- **Staging Stack**: `OsdpPipelineStack/staging/OSDP-Prototype`
- **GitHub Integration**: Pipeline sources from GitHub with Secrets Manager authentication

### IIIF Docker Image Development

Northwestern maintains the IIIF manifest fetcher Docker image. See [iiif/README.md](iiif/README.md) for details.

**Building and Pushing:**

```bash
# From project root
aws ecr-public get-login-password --region us-east-1 | docker login --username AWS --password-stdin public.ecr.aws/nulib-staging
docker build -t public.ecr.aws/nulib-staging/osdp-iiif-fetcher:[tag] -f iiif/Dockerfile .
docker push public.ecr.aws/nulib-staging/osdp-iiif-fetcher:[tag]
```

### NU Development Setup

**Python Environment:**
Follow the [Quick Start](#quick-start-for-simple-deployment) steps above.

> [!TIP]
> **VSCode Users**: Set Python interpreter via Command Palette (`⇧⌘P`) → `Python: Select Interpreter` → `./.venv/bin/python`

**Node.js Setup:**
```bash
node --version  # Should be v22.x
cd osdp/functions/build_function && npm i && cd ../../../
```

**Development Commands:**
```bash
# Testing
pytest

# Linting
ruff check .
ruff check --fix .

# Formatting  
ruff format .

# CDK commands (run from osdp/ directory)
cd osdp
cdk ls          # List stacks
cdk synth       # Generate CloudFormation
cdk deploy      # Deploy stack
cdk diff        # Compare local vs deployed
```

