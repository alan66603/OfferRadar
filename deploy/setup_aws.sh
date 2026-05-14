#!/bin/bash
# deploy/setup_aws.sh — one-time AWS resource creation
# Prerequisites: AWS CLI configured, .env loaded (source .env or export vars manually)
set -e

BUCKET="${S3_BUCKET:-offerradar-state}"
REGION="${AWS_REGION:-ap-southeast-2}"
ROLE_NAME="offerradar-lambda-role"
FUNCTION_NAME="offerradar"
SCHEDULE="rate(4 hours)"
ZIP="offerradar_lambda.zip"

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo "AWS account: $ACCOUNT_ID  region: $REGION"

echo ""
echo "=== 1/5  S3 bucket ==="
aws s3api create-bucket \
    --bucket "$BUCKET" \
    --region "$REGION" \
    --create-bucket-configuration LocationConstraint="$REGION" 2>/dev/null \
    && echo "Created: $BUCKET" || echo "Already exists: $BUCKET"

echo "Uploading resume.pdf..."
aws s3 cp resume.pdf "s3://$BUCKET/resume.pdf"

echo ""
echo "=== 2/5  IAM role ==="
aws iam create-role \
    --role-name "$ROLE_NAME" \
    --assume-role-policy-document '{
      "Version":"2012-10-17",
      "Statement":[{"Effect":"Allow","Principal":{"Service":"lambda.amazonaws.com"},"Action":"sts:AssumeRole"}]
    }' 2>/dev/null && echo "Role created" || echo "Role already exists"

aws iam attach-role-policy \
    --role-name "$ROLE_NAME" \
    --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole 2>/dev/null || true

aws iam put-role-policy \
    --role-name "$ROLE_NAME" \
    --policy-name offerradar-s3 \
    --policy-document "{
      \"Version\":\"2012-10-17\",
      \"Statement\":[{
        \"Effect\":\"Allow\",
        \"Action\":[\"s3:GetObject\",\"s3:PutObject\"],
        \"Resource\":\"arn:aws:s3:::${BUCKET}/*\"
      }]
    }"

ROLE_ARN="arn:aws:iam::${ACCOUNT_ID}:role/$ROLE_NAME"
echo "Waiting 10s for IAM to propagate..."
sleep 10

echo ""
echo "=== 3/5  Lambda function ==="
aws lambda create-function \
    --function-name "$FUNCTION_NAME" \
    --runtime python3.12 \
    --role "$ROLE_ARN" \
    --handler lambda_handler.handler \
    --zip-file "fileb://$ZIP" \
    --timeout 300 \
    --memory-size 512 \
    --region "$REGION" \
    --environment "Variables={\
GMAIL_IMAP_HOST=${GMAIL_IMAP_HOST},\
GMAIL_USER=${GMAIL_USER},\
GMAIL_APP_PASSWORD=${GMAIL_APP_PASSWORD},\
ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY},\
TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN},\
TELEGRAM_CHAT_ID=${TELEGRAM_CHAT_ID},\
S3_BUCKET=${BUCKET}}"

FUNCTION_ARN=$(aws lambda get-function \
    --function-name "$FUNCTION_NAME" \
    --query Configuration.FunctionArn --output text)

echo ""
echo "=== 4/5  EventBridge rule ($SCHEDULE) ==="
RULE_ARN=$(aws events put-rule \
    --name offerradar-schedule \
    --schedule-expression "$SCHEDULE" \
    --state ENABLED \
    --region "$REGION" \
    --query RuleArn --output text)

aws lambda add-permission \
    --function-name "$FUNCTION_NAME" \
    --statement-id offerradar-eventbridge \
    --action lambda:InvokeFunction \
    --principal events.amazonaws.com \
    --source-arn "$RULE_ARN" 2>/dev/null || true

aws events put-targets \
    --rule offerradar-schedule \
    --targets "Id=1,Arn=$FUNCTION_ARN" \
    --region "$REGION"

echo ""
echo "=== 5/5  Done ==="
echo "Lambda:   $FUNCTION_NAME"
echo "Schedule: $SCHEDULE"
echo "S3:       s3://$BUCKET"
echo ""
echo "To redeploy after code changes:"
echo "  ./deploy/package.sh"
echo "  aws lambda update-function-code --function-name $FUNCTION_NAME --zip-file fileb://$ZIP"
