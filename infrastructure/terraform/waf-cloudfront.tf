# Execution Market Infrastructure - CloudFront WAF (Phase 3.4)
#
# WAFv2 WebACL attached to the dashboard CloudFront distribution.
# The existing waf.tf covers the ALB (api/mcp hosts); this closes the gap
# on the SPA + CDN paths.
#
# IMPORTANT: CloudFront-scoped Web ACLs MUST be created in us-east-1.
# Uses the existing `aws.us_east_1` provider alias from dashboard-cdn.tf.
#
# Rules:
#   1. AWSManagedRulesCommonRuleSet      (priority 1 — OWASP Top 10)
#   2. AWSManagedRulesKnownBadInputsRuleSet (priority 2 — Log4j, host injection)
#   3. Rate limit                         (priority 3 — 1000 req / 5min per IP)
#
# Logging: CloudWatch log group (30d retention, us-east-1).
# Name MUST start with "aws-waf-logs-" (AWS requirement).
#
# Cost:
#   - $5/mo web ACL
#   - $1/mo per rule (3 rules = $3)
#   - $0.60 per million requests
#   - WAF logging: ~$0.25/mo

# ── Web ACL (CLOUDFRONT scope — must live in us-east-1) ──────────────────────

resource "aws_wafv2_web_acl" "cloudfront_dashboard" {
  provider    = aws.us_east_1
  name        = "${local.name_prefix}-cloudfront-dashboard-waf"
  scope       = "CLOUDFRONT"
  description = "WAF for Execution Market dashboard CloudFront distribution"

  default_action {
    allow {}
  }

  # Rule 1: AWS Managed — Common Rule Set (OWASP Top 10: SQLi, XSS, path traversal)
  rule {
    name     = "aws-common-rule-set"
    priority = 1

    override_action {
      none {}
    }

    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesCommonRuleSet"
        vendor_name = "AWS"
      }
    }

    visibility_config {
      sampled_requests_enabled   = true
      cloudwatch_metrics_enabled = true
      metric_name                = "${local.name_prefix}-cf-common-rule-set"
    }
  }

  # Rule 2: AWS Managed — Known Bad Inputs (Log4j, host header injection)
  rule {
    name     = "aws-known-bad-inputs"
    priority = 2

    override_action {
      none {}
    }

    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesKnownBadInputsRuleSet"
        vendor_name = "AWS"
      }
    }

    visibility_config {
      sampled_requests_enabled   = true
      cloudwatch_metrics_enabled = true
      metric_name                = "${local.name_prefix}-cf-known-bad-inputs"
    }
  }

  # Rule 3: Rate limit — 1000 requests per 5 minutes per IP across the entire
  # distribution. Coarse volumetric protection for the SPA + CDN surface.
  rule {
    name     = "rate-limit-global"
    priority = 3

    action {
      block {}
    }

    statement {
      rate_based_statement {
        limit              = 1000
        aggregate_key_type = "IP"
      }
    }

    visibility_config {
      sampled_requests_enabled   = true
      cloudwatch_metrics_enabled = true
      metric_name                = "${local.name_prefix}-cf-rate-limit-global"
    }
  }

  visibility_config {
    sampled_requests_enabled   = true
    cloudwatch_metrics_enabled = true
    metric_name                = "${local.name_prefix}-cloudfront-dashboard-waf"
  }

  tags = {
    Name = "${local.name_prefix}-cloudfront-dashboard-waf"
  }
}

# ── WAF Logging ──────────────────────────────────────────────────────────────
# Log group name MUST start with "aws-waf-logs-" (AWS requirement).
# CLOUDFRONT-scoped WAF logging config must also live in us-east-1.

resource "aws_cloudwatch_log_group" "waf_cloudfront" {
  provider          = aws.us_east_1
  name              = "aws-waf-logs-${local.name_prefix}-cloudfront-dashboard"
  retention_in_days = 30

  tags = {
    Name = "aws-waf-logs-${local.name_prefix}-cloudfront-dashboard"
  }
}

resource "aws_wafv2_web_acl_logging_configuration" "cloudfront_dashboard" {
  provider                = aws.us_east_1
  log_destination_configs = [aws_cloudwatch_log_group.waf_cloudfront.arn]
  resource_arn            = aws_wafv2_web_acl.cloudfront_dashboard.arn
}
