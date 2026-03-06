# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Treetop Discovery is an AWS CDK application (Python) that deploys a searchable knowledge base built from IIIF manifests or EAD (archival XML) files using Amazon Bedrock. The frontend is a Next.js app hosted on AWS Amplify.

## Common Commands

```bash
# Install/sync dependencies (requires uv)
uv sync --all-groups

# Activate virtual environment
source .venv/bin/activate

# Run all tests
pytest

# Run a single test file
pytest tests/unit/test_api.py

# Linting
ruff check .
ruff check --fix .

# Formatting
ruff format .

# CDK commands
cdk synth       # Generate CloudFormation templates
cdk deploy      # Deploy stack
cdk diff        # Compare local vs deployed
cdk ls          # List stacks
```

## Configuration

Before running CDK commands, `config.toml` must exist at the repo root (copy from `config.toml.example`). The `app.py` entry point loads this file and injects values as CDK context.

Required config keys: `stack_prefix`, `embedding_model_arn`, `foundation_model_arn`, `data` (with `type` = `"iiif"` or `"ead"`).

The `stack_prefix` can also come from the `DEV_PREFIX` environment variable (used in NU dev environments).

## Architecture

### Entry Point

`app.py` loads `config.toml`, validates required context (model ARNs, data config), and instantiates `TreetopStack` named `{stack_prefix}-Treetop`.

### Stack Composition (`src/treetop/stacks/treetop_stack.py`)

`TreetopStack` composes six CDK constructs in dependency order:

1. **S3 data bucket** — auto-named `{stack_name}-{suffix}`, holds processed IIIF/EAD data
2. **`EcsConstruct`** — ECS Fargate cluster + task for fetching IIIF manifests (IIIF workflow only); pulls from ECR `public.ecr.aws/nulib-staging/treetop-iiif-fetcher`
3. **`DatabaseConstruct`** — RDS Aurora PostgreSQL (vector storage for Bedrock); custom DB name/credentials configurable via `[database]` in `config.toml`
4. **`KnowledgeBaseConstruct`** — Bedrock Knowledge Base backed by the S3 bucket and Aurora DB
5. **`ApiConstruct`** — Cognito User Pool + API Gateway with two Lambda-backed routes: `POST /chat` and `GET /status`
6. **`UIConstruct`** — Amplify app + Node.js build Lambda that deploys the `osdp-prototype-ui` repo
7. **`StepFunctionsConstruct`** — Step Functions state machine orchestrating the full ingestion pipeline

### Lambda Functions (`src/treetop/functions/`)

- `chat/` — Calls `bedrock:RetrieveAndGenerate` with the Knowledge Base
- `status/` — Returns Bedrock ingestion job status (Admin group required)
- `get_iiif_manifest/` — Processes a single IIIF manifest and writes JSON to S3
- `ead/` — Processes EAD XML files from S3
- `step_function_trigger/` — Triggers the Step Functions state machine
- `build_function/` — Node.js Lambda that clones and deploys the UI to Amplify

### Data Ingestion Flow

Step Functions checks `workflowType`:
- **IIIF**: fetches manifest list from `collection_url`, fans out via ECS task per manifest, results written to S3, then triggers Bedrock sync
- **EAD**: processes XML files from configured S3 prefix, then triggers Bedrock sync

### Testing

Tests use `aws_cdk.assertions` to validate synthesized CloudFormation templates. Tests set CDK context directly on the `App` and use `Template.from_stack()` for assertions. Use `aws:cdk:bundling-stacks: []` context to skip Lambda bundling in tests.
