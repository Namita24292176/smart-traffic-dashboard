#!/bin/bash
set -e

REGION="eu-west-1"
STACK="smart-traffic"
BUCKET="smart-traffic-deploy-$(date +%s)"

echo ">>> Creating S3 bucket for deployment artifacts"
aws s3 mb "s3://${BUCKET}" --region "${REGION}"

echo ">>> Installing Lambda dependencies"
pip install boto3 requests -t cloud/ --quiet

echo ">>> Packaging SAM template"
sam package \
  --template-file template.yaml \
  --s3-bucket "${BUCKET}" \
  --output-template-file packaged.yaml \
  --region "${REGION}"

echo ">>> Deploying to AWS"
sam deploy \
  --template-file packaged.yaml \
  --stack-name "${STACK}" \
  --capabilities CAPABILITY_IAM \
  --region "${REGION}" \
  --no-fail-on-empty-changeset

echo ""
echo ">>> Stack outputs (copy the ApiEndpoint value):"
aws cloudformation describe-stacks \
  --stack-name "${STACK}" \
  --region "${REGION}" \
  --query "Stacks[0].Outputs" \
  --output table