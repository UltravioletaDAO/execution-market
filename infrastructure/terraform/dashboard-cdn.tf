# Execution Market — Dashboard CDN (S3 + CloudFront)
#
# Static React SPA served via CloudFront from S3.
# URL: execution.market (root domain)
# Replaces: ECS Fargate container em-production-dashboard
#
# Why: Dashboard is a Vite-built SPA (HTML/CSS/JS). Zero server-side logic.
# S3+CloudFront: ~$1/mo vs ~$30/mo on ECS. Deploys in ~90s vs ~10 min.
#
# S3 bucket: us-east-2 (same region as all other infra)
# ACM cert: us-east-1 (CloudFront REQUIRES certs in us-east-1 — AWS limitation)
#
# Migration:
#   1. terraform apply → creates S3 + CloudFront
#   2. CI/CD builds dashboard, syncs to S3
#   3. Test via d*.cloudfront.net
#   4. Uncomment Route53 records, apply → DNS switch
#   5. Remove ECS dashboard service + ECR repo

# ─── S3 Bucket (us-east-2, same region as everything else) ────────

resource "aws_s3_bucket" "dashboard" {
  bucket = "${local.name_prefix}-dashboard"

  tags = {
    Name    = "${local.name_prefix}-dashboard"
    Purpose = "dashboard-static-hosting"
  }
}

resource "aws_s3_bucket_versioning" "dashboard" {
  bucket = aws_s3_bucket.dashboard.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_public_access_block" "dashboard" {
  bucket                  = aws_s3_bucket.dashboard.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# ─── CloudFront Origin Access Control (OAC) ───────────────────────

resource "aws_cloudfront_origin_access_control" "dashboard" {
  name                              = "${local.name_prefix}-dashboard-oac"
  description                       = "OAC for dashboard S3 bucket"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

# ─── ACM Certificate (us-east-1 — CloudFront requirement) ─────────

provider "aws" {
  alias  = "us_east_1"
  region = "us-east-1"

  default_tags {
    tags = {
      Project     = "Execution Market"
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  }
}

resource "aws_acm_certificate" "dashboard_cdn" {
  provider          = aws.us_east_1
  domain_name       = var.domain
  validation_method = "DNS"

  subject_alternative_names = [
    "www.${var.domain}"
  ]

  lifecycle {
    create_before_destroy = true
  }

  tags = {
    Name = "${local.name_prefix}-dashboard-cdn-cert"
  }
}

resource "aws_route53_record" "dashboard_cert_validation" {
  for_each = {
    for dvo in aws_acm_certificate.dashboard_cdn.domain_validation_options : dvo.domain_name => {
      name   = dvo.resource_record_name
      record = dvo.resource_record_value
      type   = dvo.resource_record_type
    }
  }

  allow_overwrite = true
  name            = each.value.name
  records         = [each.value.record]
  ttl             = 60
  type            = each.value.type
  zone_id         = data.aws_route53_zone.main.zone_id
}

resource "aws_acm_certificate_validation" "dashboard_cdn" {
  provider                = aws.us_east_1
  certificate_arn         = aws_acm_certificate.dashboard_cdn.arn
  validation_record_fqdns = [for record in aws_route53_record.dashboard_cert_validation : record.fqdn]
}

# ─── CloudFront Distribution ──────────────────────────────────────

resource "aws_cloudfront_distribution" "dashboard" {
  enabled             = true
  is_ipv6_enabled     = true
  default_root_object = "index.html"
  comment             = "Execution Market Dashboard"
  price_class         = "PriceClass_100" # NA + Europe (cheapest)
  http_version        = "http2and3"
  wait_for_deployment = true

  aliases = [
    var.domain,
    "www.${var.domain}"
  ]

  origin {
    domain_name              = aws_s3_bucket.dashboard.bucket_regional_domain_name
    origin_id                = "S3-${local.name_prefix}-dashboard"
    origin_access_control_id = aws_cloudfront_origin_access_control.dashboard.id
  }

  default_cache_behavior {
    allowed_methods        = ["GET", "HEAD", "OPTIONS"]
    cached_methods         = ["GET", "HEAD"]
    target_origin_id       = "S3-${local.name_prefix}-dashboard"
    compress               = true
    viewer_protocol_policy = "redirect-to-https"

    cache_policy_id          = "658327ea-f89d-4fab-a63d-7e88639e58f6" # CachingOptimized
    origin_request_policy_id = null
  }

  # Aggressive cache for /assets/* (Vite content hashes = cache-safe)
  ordered_cache_behavior {
    path_pattern           = "/assets/*"
    allowed_methods        = ["GET", "HEAD"]
    cached_methods         = ["GET", "HEAD"]
    target_origin_id       = "S3-${local.name_prefix}-dashboard"
    compress               = true
    viewer_protocol_policy = "redirect-to-https"

    min_ttl     = 31536000 # 1 year
    default_ttl = 31536000
    max_ttl     = 31536000

    forwarded_values {
      query_string = false
      cookies { forward = "none" }
    }
  }

  # SPA routing: return index.html for 403/404
  custom_error_response {
    error_code            = 403
    response_code         = 200
    response_page_path    = "/index.html"
    error_caching_min_ttl = 10
  }

  custom_error_response {
    error_code            = 404
    response_code         = 200
    response_page_path    = "/index.html"
    error_caching_min_ttl = 10
  }

  viewer_certificate {
    acm_certificate_arn      = aws_acm_certificate.dashboard_cdn.arn
    ssl_support_method       = "sni-only"
    minimum_protocol_version = "TLSv1.2_2021"
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  tags = {
    Name = "${local.name_prefix}-dashboard-cdn"
  }

  depends_on = [aws_acm_certificate_validation.dashboard_cdn]
}

# ─── S3 Bucket Policy — CloudFront OAC read access ────────────────

resource "aws_s3_bucket_policy" "dashboard" {
  bucket = aws_s3_bucket.dashboard.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "AllowCloudFrontServicePrincipal"
        Effect    = "Allow"
        Principal = { Service = "cloudfront.amazonaws.com" }
        Action    = "s3:GetObject"
        Resource  = "${aws_s3_bucket.dashboard.arn}/*"
        Condition = {
          StringEquals = {
            "AWS:SourceArn" = aws_cloudfront_distribution.dashboard.arn
          }
        }
      }
    ]
  })
}

# ─── Route53 DNS ───────────────────────────────────────────────────
# UNCOMMENT after verifying CloudFront works via d*.cloudfront.net
# This REPLACES the current A record pointing to ALB/ECS.

resource "aws_route53_record" "dashboard_cdn" {
  zone_id         = data.aws_route53_zone.main.zone_id
  name            = var.domain
  type            = "A"
  allow_overwrite = true
  alias {
    name                   = aws_cloudfront_distribution.dashboard.domain_name
    zone_id                = aws_cloudfront_distribution.dashboard.hosted_zone_id
    evaluate_target_health = false
  }
}

resource "aws_route53_record" "dashboard_cdn_www" {
  zone_id         = data.aws_route53_zone.main.zone_id
  name            = "www.${var.domain}"
  type            = "A"
  allow_overwrite = true
  alias {
    name                   = aws_cloudfront_distribution.dashboard.domain_name
    zone_id                = aws_cloudfront_distribution.dashboard.hosted_zone_id
    evaluate_target_health = false
  }
}

# ─── Outputs ───────────────────────────────────────────────────────

output "dashboard_cdn_domain" {
  description = "CloudFront domain for testing before DNS switch"
  value       = aws_cloudfront_distribution.dashboard.domain_name
}

output "dashboard_cdn_id" {
  description = "CloudFront distribution ID (for CI/CD invalidation)"
  value       = aws_cloudfront_distribution.dashboard.id
}

output "dashboard_s3_bucket" {
  description = "S3 bucket for dashboard static files"
  value       = aws_s3_bucket.dashboard.id
}
