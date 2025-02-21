
# OSDP Prototype

## IIIF manifest fetcher docker image

 - [IIIF manifest fetcher docker image](iiif/README.md)

## OSDP Prototype Stack (CDK)

All steps performed from `osdp` directory

```
cd osdp
```

### Setup

The OSDP primarily uses Python, but NodeJS is used for one lambda.

#### Python

Ensure using Python 3.10.5:

```
python --version
# Python 3.10.5
```

To manually create a virtualenv

```
python -m venv .venv
```

Activate your virtualenv.

```
source .venv/bin/activate
```

Install the required dependencies.

```
pip install -r requirements.txt -r requirements-dev.txt
```

#### Node

**Node is only needed for local development not deployment**

Ensure using v22:

```
node --version
# v22.13.1
```

There is one lambda that uses node:

```
cd functions/build_function
npm i
cd ../../
```

### Define context values

Context values are key-value pairs that can be associated with an app, stack, or construct. They may be supplied in the `cdk.json` or or on the command line.

Since the `cdk.json` file is generally committed to source control, it should generally be used for values shared with the team. Anything that needs to be overriden with specific deploys should be supplied on theh command line.

#### Required context values

- `stack_prefix` (str) - will be appended to the beginning of the CloudFormation stack on deploy. (*For NU devs this is not required, it will use the `DEV_PREFIX` env var in AWS.)
- `collection_url` (str)- the url of the IIIF collection to load during deployment. There is a small collection (6 items) in the `cdk.json` file, but you will want to change or override on the command line.

#### Optional context values

- `tags` (dict) - Key value pair tags applied to all resources in the stack. Example:
```
"tags": {
      "project": "chatbot"
    },
```
- `manifest_fetch_url` (str) - The concurrency to use when retrieving IIIF manifests from your API. If not provided, the default will be used (2).
- `amplify.auth.secret_name` (str) - The name of the AWS Secrets Manager secret used for authentication. **To disable auth, use the `NO_AUTH` keyword**
- `amplify.auth.username_key` (str) - The key for the username field within the secret (default: "username").
- `amplify.auth.password_key` (str) - The key for the password field within the secret (default: "password").

```bash
# use default secret name (`OSDPSecrets`)
cdk deploy

# use NO_AUTH keyword to disable auth
cdk deploy -c amplify.auth.secret_name=NO_AUTH

# use altername secret name with default username and password key
cdk deploy -c amplify.auth.secret_name=MySecretName

# use custom values
cdk deploy \
  -c amplify.auth.secret_name=MySecret \
  -c amplify.auth.username_key=myUserKey \
  -c amplify.auth.password_key=myPassKey
```

> [!IMPORTANT]
> If a secret amplify.auth.secret_name is provided, it must be present in Secrets Manager or the app will not deploy


#### Providing context values on the command line

Example:
```
cdk deploy -c stack_prefix=alice
```

### Synthesize the CloudFormation template (optional)

Synthesize the CloudFormation template for this code (login to AWS account first). You must first log in to AWS with administrator credentials.

```
cdk synth
```

### Deploy the CDK app

To deploy the stack to AWS. You must first log in to AWS with administrator credentials using `aws sso login`.

First obtain your stack name. Ex:
```bash
cdk ls

yourprefix-OSDP-Prototype #this one is your stack name
OsdpPipelineStack
OsdpPipelineStack/staging/OSDP-Prototype (staging-OSDP-Prototype)
```

Then deploy your stack:

```
cdk deploy yourprefix-OSDP-Prototype
```


### Testing

To run the tests.

```
pytest
```

### Linting

```
ruff check .
```

or

```
ruff check --fix .
```

### Style

To run formatting

```
ruff format .
```

## Useful commands

 * `cdk ls`          list all stacks in the app
 * `cdk synth`       emits the synthesized CloudFormation template
 * `cdk deploy`      deploy this stack to your default AWS account/region
 * `cdk diff`        compare deployed stack with current state
 * `cdk docs`        open CDK documentation

Enjoy!
