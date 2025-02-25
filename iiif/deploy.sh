#!/bin/bash

# Set variables
AWS_REGION="us-east-1"  # e.g., us-east-1
ECR_REPOSITORY_NAME="osdp-iiif-fetcher"
IMAGE_TAG="latest"

# Get AWS account ID
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Login to ECR
aws ecr-public get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin public.ecr.aws

# Create ECR repository if it doesn't exist
aws ecr-public create-repository --repository-name $ECR_REPOSITORY_NAME --region $AWS_REGION || true

# Build Docker image
docker build -t $ECR_REPOSITORY_NAME:$IMAGE_TAG .

# Tag image for ECR
docker tag $ECR_REPOSITORY_NAME:$IMAGE_TAG public.ecr.aws/$ECR_REPOSITORY_NAME:$IMAGE_TAG

# Push image to ECR
docker push public.ecr.aws/$ECR_REPOSITORY_NAME:$IMAGE_TAG