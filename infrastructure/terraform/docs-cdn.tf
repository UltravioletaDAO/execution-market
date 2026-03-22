# Execution Market — Docs CDN (S3 + CloudFront)
#
# Static VitePress site served via CloudFront from S3.
# URL: docs.execution.market
# Cost: ~$0.50/month (S3 + CloudFront free tier)
#
# S3 bucket: us-east-2 (same region as all other infra)
# ACM cert: us-east-1 (CloudFront REQUIRES certs in us-east-1 — AWS limitation)
#
# VitePress uses cleanUrls: true — generates /foo.html accessed as /foo.
# CloudFront Function rewrites paths to append .html for clean URL support.

locals {
  docs_bucket_name = "${local.name_prefix}-docs"
  docs_domain      = "docs.${var.domain}"
}

# ─── S3 Bucket ───────────────────────────────────────────────────

resource "aws_s3_bucket" "docs" {
  bucket = local.docs_bucket_name

  tags = {
    Name    = local.docs_bucket_name
    Purpose = "docs-static-hosting"
  }
}

resource "aws_s3_bucket_versioning" "docs" {
  bucket = aws_s3_bucket.docs.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_public_access_block" "docs" {
  bucket                  = aws_s3_bucket.docs.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# ─── CloudFront Origin Access Control (OAC) ──────────────────────

resource "aws_cloudfront_origin_access_control" "docs" {
  name                              = "${local.name_prefix}-docs-oac"
  description                       = "OAC for docs S3 bucket"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

# ─── ACM Certificate (us-east-1 — CloudFront requirement) ───────

resource "aws_acm_certificate" "docs_cdn" {
  provider          = aws.us_east_1
  domain_name       = local.docs_domain
  validation_method = "DNS"

  lifecycle {
    create_before_destroy = true
  }

  tags = {
    Name = "${local.name_prefix}-docs-cdn-cert"
  }
}

resource "aws_route53_record" "docs_cert_validation" {
  for_each = {
    for dvo in aws_acm_certificate.docs_cdn.domain_validation_options : dvo.domain_name => {
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

resource "aws_acm_certificate_validation" "docs_cdn" {
  provider                = aws.us_east_1
  certificate_arn         = aws_acm_certificate.docs_cdn.arn
  validation_record_fqdns = [for record in aws_route53_record.docs_cert_validation : record.fqdn]
}

# ─── CloudFront Function (clean URL rewriting) ──────────────────
#
# VitePress with cleanUrls generates /foo.html but links point to /foo.
# This function rewrites incoming requests:
#   /             → /index.html
#   /guide        → /guide.html
#   /guide/       → /guide/index.html
#   /assets/x.js  → /assets/x.js (no change — has extension)

resource "aws_cloudfront_function" "docs_url_rewrite" {
  name    = "${local.name_prefix}-docs-url-rewrite"
  runtime = "cloudfront-js-2.0"
  comment = "Rewrite clean URLs to .html for VitePress"
  publish = true
  code    = <<-EOF
    function handler(event) {
      var request = event.request;
      var uri = request.uri;

      // If URI has a file extension, pass through as-is
      if (uri.includes('.')) {
        return request;
      }

      // If URI ends with /, append index.html
      if (uri.endsWith('/')) {
        request.uri = uri + 'index.html';
        return request;
      }

      // Otherwise append .html (VitePress clean URLs)
      request.uri = uri + '.html';
      return request;
    }
  EOF
}

# ─── CloudFront Distribution ────────────────────────────────────

resource "aws_cloudfront_distribution" "docs" {
  enabled             = true
  is_ipv6_enabled     = true
  default_root_object = "index.html"
  comment             = "Execution Market Docs"
  price_class         = "PriceClass_100" # NA + Europe (cheapest)
  http_version        = "http2and3"
  wait_for_deployment = true

  aliases = [local.docs_domain]

  origin {
    domain_name              = aws_s3_bucket.docs.bucket_regional_domain_name
    origin_id                = "S3-${local.docs_bucket_name}"
    origin_access_control_id = aws_cloudfront_origin_access_control.docs.id
  }

  default_cache_behavior {
    allowed_methods        = ["GET", "HEAD", "OPTIONS"]
    cached_methods         = ["GET", "HEAD"]
    target_origin_id       = "S3-${local.docs_bucket_name}"
    compress               = true
    viewer_protocol_policy = "redirect-to-https"

    cache_policy_id = "658327ea-f89d-4fab-a63d-7e88639e58f6" # CachingOptimized

    function_association {
      event_type   = "viewer-request"
      function_arn = aws_cloudfront_function.docs_url_rewrite.arn
    }
  }

  # Aggressive cache for /assets/* (Vite content hashes = cache-safe)
  ordered_cache_behavior {
    path_pattern           = "/assets/*"
    allowed_methods        = ["GET", "HEAD"]
    cached_methods         = ["GET", "HEAD"]
    target_origin_id       = "S3-${local.docs_bucket_name}"
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

  # 403 → serve 404.html (S3 returns 403 for missing keys with OAC)
  custom_error_response {
    error_code            = 403
    response_code         = 404
    response_page_path    = "/404.html"
    error_caching_min_ttl = 60
  }

  # 404 → serve 404.html
  custom_error_response {
    error_code            = 404
    response_code         = 404
    response_page_path    = "/404.html"
    error_caching_min_ttl = 60
  }

  viewer_certificate {
    acm_certificate_arn      = aws_acm_certificate.docs_cdn.arn
    ssl_support_method       = "sni-only"
    minimum_protocol_version = "TLSv1.2_2021"
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  tags = {
    Name = "${local.name_prefix}-docs-cdn"
  }

  depends_on = [aws_acm_certificate_validation.docs_cdn]
}

# ─── S3 Bucket Policy — CloudFront OAC read access ──────────────

resource "aws_s3_bucket_policy" "docs" {
  bucket = aws_s3_bucket.docs.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "AllowCloudFrontServicePrincipal"
        Effect    = "Allow"
        Principal = { Service = "cloudfront.amazonaws.com" }
        Action    = "s3:GetObject"
        Resource  = "${aws_s3_bucket.docs.arn}/*"
        Condition = {
          StringEquals = {
            "AWS:SourceArn" = aws_cloudfront_distribution.docs.arn
          }
        }
      }
    ]
  })
}

# ─── Route53 DNS ─────────────────────────────────────────────────

resource "aws_route53_record" "docs_cdn" {
  zone_id = data.aws_route53_zone.main.zone_id
  name    = local.docs_domain
  type    = "A"

  alias {
    name                   = aws_cloudfront_distribution.docs.domain_name
    zone_id                = aws_cloudfront_distribution.docs.hosted_zone_id
    evaluate_target_health = false
  }
}

# ─── Outputs ─────────────────────────────────────────────────────

output "docs_cdn_domain" {
  description = "CloudFront domain for testing before DNS switch"
  value       = aws_cloudfront_distribution.docs.domain_name
}

output "docs_cdn_id" {
  description = "CloudFront distribution ID (for CI/CD invalidation)"
  value       = aws_cloudfront_distribution.docs.id
}

output "docs_s3_bucket" {
  description = "S3 bucket for docs static files"
  value       = aws_s3_bucket.docs.id
}
