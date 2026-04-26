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

# ─── CloudFront Response Headers Policy (SaaS Hardening Phase 1.2) ───
#
# Injects security headers on every response served by the dashboard CDN:
#   - HSTS (2-year, includeSubDomains, preload)
#   - Content-Type-Options: nosniff
#   - X-Frame-Options: DENY (clickjacking — also enforced via CSP frame-ancestors 'none')
#   - Referrer-Policy: strict-origin-when-cross-origin
#   - Permissions-Policy: camera=(self), geolocation=(self) (EvidenceUpload needs them),
#                         microphone=(), payment=() (not used)
#   - Content-Security-Policy-Report-Only (Phase A):
#       Deployed in Report-Only mode first so we can monitor violations for 1-2
#       weeks via browser reports without breaking the app. A follow-up PR flips
#       the `Content-Security-Policy-Report-Only` header to `Content-Security-Policy`
#       (enforcing) once telemetry shows no legitimate requests are being blocked.
#       No `'unsafe-eval'` in script-src — Vite production builds do not need it.
#
# Origins allowed in connect-src were derived from:
#   - dashboard/src/lib/{supabase,dynamic}.ts                (Supabase + Dynamic)
#   - dashboard/node_modules/@dynamic-labs/*                 (*.dynamicauth.com runtime APIs)
#   - dashboard/src/context/XMTPContext.tsx                  (XMTP production network)
#   - dashboard/node_modules/@xmtp/*                         (xmtp.network + ephemera)
#   - dashboard/node_modules/@worldcoin/idkit*               (World ID bridge/assets)
#   - dashboard/public/_headers (existing meta CSP)          (api, s3, cloudfront)
resource "aws_cloudfront_response_headers_policy" "execution_market_security_headers" {
  name    = "${local.name_prefix}-dashboard-security-headers"
  comment = "Security headers for execution.market dashboard (HSTS, XFO, CSP-Report-Only)"

  security_headers_config {
    strict_transport_security {
      access_control_max_age_sec = 63072000 # 2 years
      include_subdomains         = true
      preload                    = true
      override                   = true
    }

    content_type_options {
      override = true
    }

    frame_options {
      frame_option = "DENY"
      override     = true
    }

    referrer_policy {
      referrer_policy = "strict-origin-when-cross-origin"
      override        = true
    }
  }

  # Permissions-Policy + Content-Security-Policy-Report-Only are not first-class
  # fields in aws_cloudfront_response_headers_policy, so we emit them as custom
  # headers. The built-in `content_security_policy` block only supports
  # enforcing CSP, not Report-Only — we'll migrate to it in Phase B.
  custom_headers_config {
    items {
      header   = "Permissions-Policy"
      value    = "camera=(self), microphone=(), geolocation=(self), payment=()"
      override = true
    }

    items {
      header = "Content-Security-Policy-Report-Only"
      value = join("; ", [
        "default-src 'self'",
        "script-src 'self' 'unsafe-inline'",
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
        "font-src 'self' https://fonts.gstatic.com",
        "img-src 'self' data: blob: https:",
        join(" ", [
          "connect-src 'self'",
          "https://api.execution.market",
          "https://mcp.execution.market",
          "https://*.supabase.co",
          "wss://*.supabase.co",
          "https://app.dynamic.xyz",
          "https://*.dynamic.xyz",
          "https://*.dynamicauth.com",
          "wss://*.dynamicauth.com",
          "https://dynamic-static-assets.com",
          "https://*.dynamic-static-assets.com",
          "https://*.xmtp.network",
          "wss://*.xmtp.network",
          "https://*.ephemera.network",
          "https://developer.worldcoin.org",
          "https://world-id-assets.com",
          "https://*.amazonaws.com",
          "https://*.lambda-url.us-east-2.on.aws",
          "https://*.cloudfront.net",
          "https://*.sentry.io",
        ]),
        "frame-src 'self' https://*.dynamicauth.com https://id.worldcoin.org",
        "frame-ancestors 'none'",
        "base-uri 'self'",
        "form-action 'self'",
        "object-src 'none'",
        "report-uri /csp-report",
      ])
      override = true
    }

    # RFC 8288 — Link headers for agent discovery.
    # Multi-value Link header per RFC 8288 §3 (comma-separated).
    # Points scanners and agents at our .well-known discovery endpoints
    # without requiring them to fetch the HTML first.
    items {
      header = "Link"
      value = join(", ", [
        "</.well-known/api-catalog>; rel=\"api-catalog\"; type=\"application/linkset+json\"",
        "</.well-known/mcp/server-card.json>; rel=\"mcp-server-card\"; type=\"application/json\"",
        "</.well-known/agent-skills/index.json>; rel=\"agent-skills\"; type=\"application/json\"",
        "</.well-known/oauth-protected-resource>; rel=\"oauth-protected-resource\"; type=\"application/json\"",
        "</skill.md>; rel=\"service-doc\"; type=\"text/markdown\"",
        "</llms.txt>; rel=\"llms\"; type=\"text/plain\""
      ])
      override = true
    }
  }
}

# ─── CloudFront Function — Markdown Negotiation (RFC 7231 / Agent Readiness) ──
#
# Attached to the default cache behavior as a viewer-request function.
# When a client sends `Accept: text/markdown` explicitly (not via */* wildcard),
# the URI is rewritten to the canonical markdown document (skill.md by default,
# with per-route overrides). Browsers never send text/markdown explicitly, so
# they continue to receive index.html.
#
# See docs/architecture/MARKDOWN_NEGOTIATION.md for the route map and rationale.
resource "aws_cloudfront_function" "markdown_negotiation" {
  name    = "${local.name_prefix}-markdown-negotiation"
  runtime = "cloudfront-js-2.0"
  comment = "Rewrite URI to skill.md on Accept: text/markdown (agent markdown negotiation)"
  publish = true
  code    = file("${path.module}/markdown-negotiation.js")
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

  # WAFv2 (Phase 3.4 — SaaS Production Hardening). See waf-cloudfront.tf.
  web_acl_id = aws_wafv2_web_acl.cloudfront_dashboard.arn

  aliases = [
    var.domain,
    "www.${var.domain}"
  ]

  origin {
    domain_name              = aws_s3_bucket.dashboard.bucket_regional_domain_name
    origin_id                = "S3-${local.name_prefix}-dashboard"
    origin_access_control_id = aws_cloudfront_origin_access_control.dashboard.id
  }

  # Evidence S3 bucket — serves /feedback/* JSON documents for on-chain feedbackURIs.
  # ERC-8004 Reputation Registry stores feedbackUri as execution.market/feedback/...
  # CloudFront proxies these to the evidence S3 bucket directly.
  dynamic "origin" {
    for_each = var.enable_evidence_pipeline ? [1] : []
    content {
      domain_name              = aws_s3_bucket.evidence[0].bucket_regional_domain_name
      origin_id                = "S3-${local.name_prefix}-evidence"
      origin_access_control_id = aws_cloudfront_origin_access_control.dashboard.id
    }
  }

  default_cache_behavior {
    allowed_methods        = ["GET", "HEAD", "OPTIONS"]
    cached_methods         = ["GET", "HEAD"]
    target_origin_id       = "S3-${local.name_prefix}-dashboard"
    compress               = true
    viewer_protocol_policy = "redirect-to-https"

    cache_policy_id            = "658327ea-f89d-4fab-a63d-7e88639e58f6" # CachingOptimized
    origin_request_policy_id   = null
    response_headers_policy_id = aws_cloudfront_response_headers_policy.execution_market_security_headers.id

    function_association {
      event_type   = "viewer-request"
      function_arn = aws_cloudfront_function.markdown_negotiation.arn
    }
  }

  # Feedback JSON documents — served from evidence S3 bucket.
  # On-chain feedbackURIs reference execution.market/feedback/{task_id}/...
  # These are immutable once created, cache aggressively.
  dynamic "ordered_cache_behavior" {
    for_each = var.enable_evidence_pipeline ? [1] : []
    content {
      path_pattern           = "/feedback/*"
      allowed_methods        = ["GET", "HEAD", "OPTIONS"]
      cached_methods         = ["GET", "HEAD"]
      target_origin_id       = "S3-${local.name_prefix}-evidence"
      compress               = true
      viewer_protocol_policy = "redirect-to-https"

      cache_policy_id            = "658327ea-f89d-4fab-a63d-7e88639e58f6" # CachingOptimized
      response_headers_policy_id = aws_cloudfront_response_headers_policy.execution_market_security_headers.id
    }
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

    response_headers_policy_id = aws_cloudfront_response_headers_policy.execution_market_security_headers.id

    forwarded_values {
      query_string = false
      cookies { forward = "none" }
    }
  }

  # SPA routing: return index.html for 403/404 (S3 returns 403 for missing keys).
  # TTL of 300s reduces repeated S3 origin fetches for unknown SPA routes.
  custom_error_response {
    error_code            = 403
    response_code         = 200
    response_page_path    = "/index.html"
    error_caching_min_ttl = 300
  }

  custom_error_response {
    error_code            = 404
    response_code         = 200
    response_page_path    = "/index.html"
    error_caching_min_ttl = 300
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
