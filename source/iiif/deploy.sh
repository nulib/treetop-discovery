#!/bin/bash

# Set variables
AWS_REGION="us-east-1"  # e.g., us-east-1
ECR_REPOSITORY_NAME="osdp-iiif-fetcher"
IMAGE_TAG="latest"

# Get AWS account ID
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Login to ECR
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

# Create ECR repository if it doesn't exist
aws ecr create-repository --repository-name $ECR_REPOSITORY_NAME --region $AWS_REGION || true

# Build Docker image
docker build -t $ECR_REPOSITORY_NAME:$IMAGE_TAG .

# Tag image for ECR
docker tag $ECR_REPOSITORY_NAME:$IMAGE_TAG $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPOSITORY_NAME:$IMAGE_TAG

# Push image to ECR
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPOSITORY_NAME:$IMAGE_TAG