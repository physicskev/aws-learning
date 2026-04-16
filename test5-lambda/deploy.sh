#!/bin/bash
# Deploy Lambda function to AWS
# Usage: ./deploy.sh
#
# Prerequisites:
#   - AWS CLI configured (aws configure)
#   - Lambda function 'test5-lambda' already created in AWS console or via CLI
#   - IAM role with LambdaBasicExecutionRole

set -e

FUNCTION_NAME="test5-lambda"
REGION="us-east-1"
HANDLER="lambda_handler.handler"
RUNTIME="python3.12"

echo "=== Building deployment package ==="
cd "$(dirname "$0")/function"

# Create temp build dir
BUILD_DIR=$(mktemp -d)
cp lambda_handler.py "$BUILD_DIR/"

# If there are pip dependencies, install them
# pip install --target "$BUILD_DIR" psycopg2-binary  # uncomment when adding Postgres

# Create zip
cd "$BUILD_DIR"
zip -r /tmp/test5-lambda.zip .
cd -

echo "=== Deploying to AWS Lambda ==="
aws lambda update-function-code \
    --function-name "$FUNCTION_NAME" \
    --zip-file fileb:///tmp/test5-lambda.zip \
    --region "$REGION"

echo "=== Done ==="
echo "Test with: aws lambda invoke --function-name $FUNCTION_NAME --payload '{\"requestContext\":{\"http\":{\"method\":\"GET\",\"path\":\"/api/health\"}}}' /tmp/lambda-response.json && cat /tmp/lambda-response.json"

# Cleanup
rm -rf "$BUILD_DIR" /tmp/test5-lambda.zip
