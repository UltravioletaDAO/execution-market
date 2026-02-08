#!/bin/bash
# ============================================================================
# Execution Market Documentation Site Deployment Script
# Target: https://docs.execution.market
# Stack: VitePress → S3 → CloudFront
# ============================================================================
#
# FIRST-TIME SETUP (Manual AWS Console or CLI steps):
#
# 1. Create OAC (Origin Access Control):
#    aws cloudfront create-origin-access-control \
#      --origin-access-control-config '{
#        "Name": "em-docs-site-oac",
#        "Description": "OAC for docs.execution.market",
#        "SigningProtocol": "sigv4",
#        "SigningBehavior": "always",
#        "OriginAccessControlOriginType": "s3"
#      }' --region us-east-1
#    → Note the OAC ID (e.g., E1ABC123DEF456)
#
# 2. Create CloudFront Distribution via AWS Console or CLI:
#    - Origin: em-production-docs-site.s3.us-east-2.amazonaws.com
#    - OAC: Use the OAC created above
#    - Alternate domain: docs.execution.market
#    - SSL: Use wildcard cert arn:aws:acm:us-east-1:YOUR_AWS_ACCOUNT_ID:certificate/841084f8-b130-4b12-87ee-88ac7d81be24
#    - Default root: index.html
#    - Error 403 → /index.html (for SPA routing)
#    - Price class: PriceClass_100 (US/EU)
#    → Note the Distribution ID
#
# 3. Add S3 bucket policy (after CloudFront created):
#    Replace DISTRIBUTION_ID in the policy below and apply:
#    {
#      "Version": "2012-10-17",
#      "Statement": [{
#        "Sid": "AllowCloudFrontServicePrincipal",
#        "Effect": "Allow",
#        "Principal": {"Service": "cloudfront.amazonaws.com"},
#        "Action": "s3:GetObject",
#        "Resource": "arn:aws:s3:::em-production-docs-site/*",
#        "Condition": {
#          "StringEquals": {
#            "AWS:SourceArn": "arn:aws:cloudfront::YOUR_AWS_ACCOUNT_ID:distribution/DISTRIBUTION_ID"
#          }
#        }
#      }]
#    }
#
# 4. Create Route53 A record:
#    Name: docs.execution.market
#    Type: A (Alias)
#    Target: CloudFront distribution domain (d123abc.cloudfront.net)
#    Zone ID: Z050891416D4N69E74FEN
#
# ============================================================================

set -e

# Configuration
AWS_REGION="us-east-2"
S3_BUCKET="em-production-docs-site"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DOCS_SITE_DIR="$PROJECT_ROOT/docs-site"
DIST_DIR="$DOCS_SITE_DIR/docs/.vitepress/dist"

# CloudFront Distribution ID (set after first-time setup)
# Update this after creating CloudFront distribution
CLOUDFRONT_DIST_ID="${CLOUDFRONT_DIST_ID:-}"

echo "=============================================="
echo "  Execution Market Docs Deployment"
echo "  Target: https://docs.execution.market"
echo "=============================================="
echo ""
echo "Region:    $AWS_REGION"
echo "S3 Bucket: $S3_BUCKET"
echo "Source:    $DOCS_SITE_DIR"
echo ""

# -----------------------------------------------------------------------------
# Step 1: Check prerequisites
# -----------------------------------------------------------------------------
echo "1. Checking prerequisites..."

if ! command -v aws &> /dev/null; then
    echo "   ERROR: AWS CLI not found. Please install it."
    exit 1
fi

if ! command -v npm &> /dev/null; then
    echo "   ERROR: npm not found. Please install Node.js."
    exit 1
fi

if ! aws sts get-caller-identity &> /dev/null; then
    echo "   ERROR: AWS credentials not configured."
    exit 1
fi

echo "   ✓ Prerequisites OK"

# -----------------------------------------------------------------------------
# Step 2: Create S3 bucket if needed
# -----------------------------------------------------------------------------
echo ""
echo "2. Checking S3 bucket..."

if aws s3api head-bucket --bucket "$S3_BUCKET" 2>/dev/null; then
    echo "   ✓ Bucket exists: s3://$S3_BUCKET"
else
    echo "   Creating bucket: s3://$S3_BUCKET"
    aws s3 mb "s3://$S3_BUCKET" --region "$AWS_REGION"
    
    echo "   Blocking public access..."
    aws s3api put-public-access-block \
        --bucket "$S3_BUCKET" \
        --public-access-block-configuration \
        'BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true'
    
    echo "   ✓ Bucket created with public access blocked"
    echo ""
    echo "   ⚠️  IMPORTANT: Complete first-time setup steps at top of this script!"
    echo "   ⚠️  You need to create CloudFront distribution and bucket policy."
fi

# -----------------------------------------------------------------------------
# Step 3: Build docs-site
# -----------------------------------------------------------------------------
echo ""
echo "3. Building documentation site..."

cd "$DOCS_SITE_DIR"

# Install dependencies if needed
if [ ! -d "node_modules" ]; then
    echo "   Installing dependencies..."
    npm install
fi

echo "   Running VitePress build..."
npm run build

if [ ! -d "$DIST_DIR" ]; then
    echo "   ERROR: Build failed - dist directory not found"
    exit 1
fi

FILE_COUNT=$(find "$DIST_DIR" -type f | wc -l | tr -d ' ')
DIST_SIZE=$(du -sh "$DIST_DIR" | cut -f1)
echo "   ✓ Build complete: $FILE_COUNT files, $DIST_SIZE"

# -----------------------------------------------------------------------------
# Step 4: Sync to S3
# -----------------------------------------------------------------------------
echo ""
echo "4. Syncing to S3..."

# Static assets with long cache (1 year)
echo "   Syncing assets (long cache)..."
aws s3 sync "$DIST_DIR/" "s3://$S3_BUCKET/" \
    --delete \
    --cache-control "max-age=31536000,public" \
    --exclude "*.html" \
    --exclude "*.json" \
    --exclude "hashmap.json" \
    --region "$AWS_REGION"

# HTML and JSON with short cache (1 hour)
echo "   Syncing HTML/JSON (short cache)..."
aws s3 sync "$DIST_DIR/" "s3://$S3_BUCKET/" \
    --exclude "*" \
    --include "*.html" \
    --include "*.json" \
    --cache-control "max-age=3600,public" \
    --region "$AWS_REGION"

echo "   ✓ Sync complete"

# -----------------------------------------------------------------------------
# Step 5: CloudFront invalidation
# -----------------------------------------------------------------------------
echo ""
echo "5. CloudFront cache invalidation..."

if [ -n "$CLOUDFRONT_DIST_ID" ]; then
    echo "   Creating invalidation for /*..."
    INVALIDATION_ID=$(aws cloudfront create-invalidation \
        --distribution-id "$CLOUDFRONT_DIST_ID" \
        --paths "/*" \
        --query 'Invalidation.Id' \
        --output text)
    echo "   ✓ Invalidation created: $INVALIDATION_ID"
else
    echo "   ⚠️  CLOUDFRONT_DIST_ID not set"
    echo ""
    echo "   After creating CloudFront distribution, run:"
    echo "   aws cloudfront create-invalidation \\"
    echo "     --distribution-id YOUR_DIST_ID \\"
    echo "     --paths \"/*\""
    echo ""
    echo "   Or set CLOUDFRONT_DIST_ID environment variable and re-run this script."
fi

# -----------------------------------------------------------------------------
# Done
# -----------------------------------------------------------------------------
echo ""
echo "=============================================="
echo "  Deployment Complete!"
echo "=============================================="
echo ""
echo "  S3: s3://$S3_BUCKET"
if [ -n "$CLOUDFRONT_DIST_ID" ]; then
    echo "  URL: https://docs.execution.market"
else
    echo ""
    echo "  ⚠️  First-time setup required!"
    echo "  See comments at top of this script for:"
    echo "  - CloudFront distribution creation"
    echo "  - S3 bucket policy (CloudFront access)"
    echo "  - Route53 DNS record"
fi
echo ""
