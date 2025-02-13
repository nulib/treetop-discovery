
# OSDP Prototype

## IIIF manifest fetcher docker image

 - [IIIF manifest fetcher docker image](iiif/README.md)

## OSDP Prototype Stack (CDK)

All steps performed from `osdp` directory

```
cd osdp
```

### Setup

To manually create a virtualenv

```
python3 -m venv .venv
```

Aactivate your virtualenv.

```
source .venv/bin/activate
```

Install the required dependencies.

```
pip install -r requirements.txt -r requirements-dev.txt
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

### Style

```
ruff check .
```

or

```
ruff check --fix .
```

To add additional dependencies, for example other CDK libraries, just add
them to your `setup.py` file and rerun the `pip install -r requirements.txt`
command.

## Useful commands

 * `cdk ls`          list all stacks in the app
 * `cdk synth`       emits the synthesized CloudFormation template
 * `cdk deploy`      deploy this stack to your default AWS account/region
 * `cdk diff`        compare deployed stack with current state
 * `cdk docs`        open CDK documentation

Enjoy!
