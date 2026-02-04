# Deploy Instructions

Three deployment targets for Execution Market infrastructure.

---

## 1. Docs Site → docs.execution.market

The documentation site is built with VitePress and deployed as static files to S3 + CloudFront.

### Build

```bash
cd docs-site
npm install
npm run build
# Output: docs-site/docs/.vitepress/dist/
```

### AWS Infrastructure (One-Time Setup)

```bash
# Create S3 bucket for docs
aws s3 mb s3://execution-market-docs-site --region us-east-2

# Enable static website hosting
aws s3 website s3://execution-market-docs-site \
  --index-document index.html \
  --error-document 404.html

# Set bucket policy for public read
aws s3api put-bucket-policy --bucket execution-market-docs-site --policy '{
  "Version": "2012-10-17",
  "Statement": [{
    "Sid": "PublicRead",
    "Effect": "Allow",
    "Principal": "*",
    "Action": "s3:GetObject",
    "Resource": "arn:aws:s3:::execution-market-docs-site/*"
  }]
}'

# Request ACM certificate (us-east-1 required for CloudFront)
aws acm request-certificate \
  --domain-name docs.execution.market \
  --validation-method DNS \
  --region us-east-1

# Create CloudFront distribution
aws cloudfront create-distribution \
  --distribution-config '{
    "CallerReference": "execution-market-docs-2026",
    "Comment": "Execution Market Documentation Site",
    "DefaultRootObject": "index.html",
    "Origins": {
      "Quantity": 1,
      "Items": [{
        "Id": "S3-execution-market-docs-site",
        "DomainName": "execution-market-docs-site.s3-website.us-east-2.amazonaws.com",
        "CustomOriginConfig": {
          "HTTPPort": 80,
          "OriginProtocolPolicy": "http-only"
        }
      }]
    },
    "DefaultCacheBehavior": {
      "TargetOriginId": "S3-execution-market-docs-site",
      "ViewerProtocolPolicy": "redirect-to-https",
      "AllowedMethods": {"Quantity": 2, "Items": ["GET", "HEAD"]},
      "CachedMethods": {"Quantity": 2, "Items": ["GET", "HEAD"]},
      "ForwardedValues": {"QueryString": false, "Cookies": {"Forward": "none"}},
      "Compress": true,
      "MinTTL": 0,
      "DefaultTTL": 86400,
      "MaxTTL": 31536000
    },
    "CustomErrorResponses": {
      "Quantity": 1,
      "Items": [{
        "ErrorCode": 404,
        "ResponseCode": 200,
        "ResponsePagePath": "/index.html",
        "ErrorCachingMinTTL": 300
      }]
    },
    "Aliases": {"Quantity": 1, "Items": ["docs.execution.market"]},
    "ViewerCertificate": {
      "ACMCertificateArn": "arn:aws:acm:us-east-1:ACCOUNT:certificate/CERT_ID",
      "SSLSupportMethod": "sni-only",
      "MinimumProtocolVersion": "TLSv1.2_2021"
    },
    "Enabled": true
  }'

# Add Route53 record
# A record: docs.execution.market → CloudFront distribution
aws route53 change-resource-record-sets --hosted-zone-id ZONE_ID --change-batch '{
  "Changes": [{
    "Action": "UPSERT",
    "ResourceRecordSet": {
      "Name": "docs.execution.market",
      "Type": "A",
      "AliasTarget": {
        "HostedZoneId": "Z2FDTNDATAQYW2",
        "DNSName": "DISTRIBUTION_ID.cloudfront.net",
        "EvaluateTargetHealth": false
      }
    }
  }]
}'
```

### Deploy (Recurring)

```bash
# Build and sync
cd docs-site
npm run build

# Upload to S3
aws s3 sync docs/.vitepress/dist/ s3://execution-market-docs-site/ \
  --delete \
  --cache-control "public, max-age=86400"

# Set immutable cache for assets
aws s3 sync docs/.vitepress/dist/assets/ s3://execution-market-docs-site/assets/ \
  --cache-control "public, max-age=31536000, immutable"

# Invalidate CloudFront cache
aws cloudfront create-invalidation \
  --distribution-id DISTRIBUTION_ID \
  --paths "/*"
```

### GitHub Actions (Optional)

Add `.github/workflows/deploy-docs.yml`:

```yaml
name: Deploy Docs
on:
  push:
    branches: [main]
    paths: ['docs-site/**']

jobs:
  deploy:
    runs-on: ubuntu-latest
    permissions:
      id-token: write
      contents: read
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 20
      - run: cd docs-site && npm ci && npm run build
      - uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.AWS_ROLE_ARN_PROD }}
          aws-region: us-east-2
      - run: |
          aws s3 sync docs-site/docs/.vitepress/dist/ s3://execution-market-docs-site/ --delete
          aws cloudfront create-invalidation --distribution-id ${{ secrets.DOCS_CF_DIST_ID }} --paths "/*"
```

---

## 2. React Dashboard → S3 + CloudFront (execution.market)

Replace the current static landing page with the React dashboard build.

### Build

```bash
cd dashboard
npm install
npm run build
# Output: dashboard/dist/
```

### AWS Infrastructure (One-Time)

The domain `execution.market` is already served by CloudFront pointing to an S3 bucket with the old static landing page. To update:

```bash
# 1. Identify the existing CloudFront distribution
aws cloudfront list-distributions --query \
  "DistributionList.Items[?contains(Aliases.Items, 'execution.market')].{Id:Id,Domain:DomainName}" \
  --output table

# 2. Identify the existing S3 bucket (from CloudFront origin config)
aws cloudfront get-distribution --id EXISTING_DIST_ID \
  --query "Distribution.DistributionConfig.Origins"

# 3. Upload the React dashboard build
aws s3 sync dashboard/dist/ s3://EXISTING_BUCKET/ \
  --delete \
  --cache-control "public, max-age=86400"

# 4. Set immutable cache for hashed assets
aws s3 sync dashboard/dist/assets/ s3://EXISTING_BUCKET/assets/ \
  --cache-control "public, max-age=31536000, immutable"

# 5. Set no-cache for index.html (SPA entry point)
aws s3 cp dashboard/dist/index.html s3://EXISTING_BUCKET/index.html \
  --cache-control "no-cache, no-store, must-revalidate"

# 6. Update CloudFront error pages for SPA routing
# Custom error response: 403 → /index.html (200)
# Custom error response: 404 → /index.html (200)
aws cloudfront update-distribution --id EXISTING_DIST_ID \
  --if-match ETAG \
  --distribution-config file://cloudfront-spa-config.json

# 7. Invalidate cache
aws cloudfront create-invalidation \
  --distribution-id EXISTING_DIST_ID \
  --paths "/*"
```

### SPA Config for CloudFront

CloudFront needs custom error responses to handle client-side routing. Ensure the distribution config includes:

```json
{
  "CustomErrorResponses": {
    "Quantity": 2,
    "Items": [
      {
        "ErrorCode": 403,
        "ResponseCode": 200,
        "ResponsePagePath": "/index.html",
        "ErrorCachingMinTTL": 0
      },
      {
        "ErrorCode": 404,
        "ResponseCode": 200,
        "ResponsePagePath": "/index.html",
        "ErrorCachingMinTTL": 0
      }
    ]
  }
}
```

### Build with Environment Variables

The dashboard needs Supabase credentials at build time:

```bash
VITE_SUPABASE_URL=https://puyhpytmtkyevnxffksl.supabase.co \
VITE_SUPABASE_ANON_KEY=your-anon-key \
npm run build
```

### Deploy Script

```bash
#!/bin/bash
# scripts/deploy-dashboard-s3.sh
set -euo pipefail

BUCKET="execution-market-dashboard-prod"  # or existing bucket name
CF_DIST_ID="E1XXXXXXXX"

echo "Building dashboard..."
cd dashboard
npm ci
VITE_SUPABASE_URL=$VITE_SUPABASE_URL \
VITE_SUPABASE_ANON_KEY=$VITE_SUPABASE_ANON_KEY \
npm run build

echo "Uploading to S3..."
aws s3 sync dist/ s3://$BUCKET/ --delete --cache-control "public, max-age=86400"
aws s3 cp dist/index.html s3://$BUCKET/index.html --cache-control "no-cache"
aws s3 sync dist/assets/ s3://$BUCKET/assets/ --cache-control "public, max-age=31536000, immutable"

echo "Invalidating CloudFront..."
aws cloudfront create-invalidation --distribution-id $CF_DIST_ID --paths "/*"

echo "Deploy complete."
```

---

## 3. React Dashboard → Docker + ECS

This uses the existing Terraform infrastructure and Dockerfile.

### Build and Push to ECR

```bash
# Login to ECR
AWS_ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
AWS_REGION=us-east-2
ECR_REPO=$AWS_ACCOUNT.dkr.ecr.$AWS_REGION.amazonaws.com

aws ecr get-login-password --region $AWS_REGION | \
  docker login --username AWS --password-stdin $ECR_REPO

# Build dashboard image
docker build \
  -f Dockerfile.dashboard \
  --build-arg VITE_SUPABASE_URL=$VITE_SUPABASE_URL \
  --build-arg VITE_SUPABASE_ANON_KEY=$VITE_SUPABASE_ANON_KEY \
  --target production \
  -t execution-market-dashboard:latest \
  ./dashboard

# Tag and push
docker tag execution-market-dashboard:latest $ECR_REPO/chamba-dashboard:latest
docker tag execution-market-dashboard:latest $ECR_REPO/chamba-dashboard:$(git rev-parse --short HEAD)
docker push $ECR_REPO/chamba-dashboard:latest
docker push $ECR_REPO/chamba-dashboard:$(git rev-parse --short HEAD)
```

### Deploy via Terraform

```bash
cd infrastructure/terraform

# Update the dashboard image variable
terraform apply \
  -var="dashboard_image=$ECR_REPO/chamba-dashboard:$(git rev-parse --short HEAD)" \
  -var="environment=production"
```

### Deploy via ECS Force Deploy

If the image tag is `latest` and already pushed:

```bash
# Force new deployment (pulls latest image)
aws ecs update-service \
  --cluster chamba-production \
  --service chamba-dashboard \
  --force-new-deployment \
  --region us-east-2
```

### Deploy via GitHub Actions

Already configured in `.github/workflows/deploy.yml`:
- Push to `main` → builds, pushes to ECR, deploys to ECS
- Creates release tag → deploys to production with approval gate

### Manual Deploy Script

Existing at `scripts/deploy-manual.sh`:

```bash
# Full manual deploy
make rebuild-dashboard  # Build container
# Then push to ECR and update ECS (see script)
```

### Health Check

After deploying, verify:

```bash
# ECS service status
aws ecs describe-services \
  --cluster chamba-production \
  --services chamba-dashboard \
  --query "services[0].{Status:status,Running:runningCount,Desired:desiredCount}"

# HTTP health check
curl -f https://execution.market/health
```

---

## Quick Reference

| Target | Build Command | Deploy Command |
|--------|--------------|----------------|
| Docs site | `cd docs-site && npm run build` | `aws s3 sync dist/ s3://execution-market-docs-site/ --delete` |
| Dashboard (S3) | `cd dashboard && npm run build` | `aws s3 sync dist/ s3://BUCKET/ --delete` |
| Dashboard (ECS) | `docker build -f Dockerfile.dashboard` | `aws ecs update-service --force-new-deployment` |

## Required AWS Resources

| Resource | Purpose | Already Exists? |
|----------|---------|-----------------|
| S3 bucket (docs) | VitePress static files | No (create) |
| CloudFront (docs) | CDN for docs | No (create) |
| ACM cert (docs) | SSL for docs subdomain | No (create) |
| Route53 record (docs) | DNS for docs subdomain | No (create) |
| S3 bucket (dashboard) | React SPA files | Yes (landing page) |
| CloudFront (dashboard) | CDN for dashboard | Yes (landing page) |
| ECR repo (dashboard) | Docker images | Yes |
| ECS cluster | Container orchestration | Yes |
| ALB | Load balancing | Yes |
