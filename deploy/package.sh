#!/bin/bash
# deploy/package.sh — builds the Lambda deployment zip
set -e

PACKAGE_DIR="build/lambda_package"
OUTPUT="offerradar_lambda.zip"

echo "Cleaning build directory..."
rm -rf "$PACKAGE_DIR" "$OUTPUT"
mkdir -p "$PACKAGE_DIR"

echo "Installing dependencies..."
pip install -r requirements.txt --target "$PACKAGE_DIR" --quiet
# Remove boto3/botocore — the Lambda runtime already provides them
rm -rf "$PACKAGE_DIR/boto3" "$PACKAGE_DIR/botocore" "$PACKAGE_DIR/s3transfer"

echo "Copying source files..."
cp -r offerradar "$PACKAGE_DIR/"
cp lambda_handler.py main.py preferences.yaml "$PACKAGE_DIR/"

echo "Creating zip..."
cd "$PACKAGE_DIR" && zip -r "../../$OUTPUT" . -q
cd ../..

echo "Done: $OUTPUT ($(du -sh "$OUTPUT" | cut -f1))"
