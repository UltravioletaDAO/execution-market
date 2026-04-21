# Execution Market Infrastructure - AWS WAF v2
#
# WAF Web ACL attached to the ALB. Provides:
# 1. Static IP blocklist for confirmed abusers
# 2. AWS Managed Common Rule Set (OWASP Top 10: SQLi, XSS, path traversal)
# 3. AWS Managed Known Bad Inputs (Log4j, host header injection)
# 4. AWS Managed Anonymous IP List (Tor exits — hosting providers COUNT-only)
# 5. A2A-specific rate limit: 100 req/5min for /a2a/ path
# 6. Global rate limit: 600 req/5min per IP (coarse safety net)
#
# Cost: ~$12/mo at current traffic levels
#   - $5/mo web ACL
#   - $1/mo per rule (6 rules = $6)
#   - $0.60 per million requests (~$0.30/mo at ~500K req/mo)
#   - WAF logging: ~$0.25/mo
#
# Added 2026-04-04 after CloudWatch revealed 20.5% of traffic is 4xx junk
# from Tor exit node 104.244.78.233 flooding POST /a2a/v1.

# ── IP Blocklist ─────────────────────────────────────────────────────────────

resource "aws_wafv2_ip_set" "blocklist" {
  name               = "${local.name_prefix}-ip-blocklist"
  description        = "Manually-managed blocklist for confirmed abusers"
  scope              = "REGIONAL"
  ip_address_version = "IPV4"
  addresses          = var.waf_blocked_ips

  tags = {
    Name = "${local.name_prefix}-ip-blocklist"
  }
}

# ── Web ACL ──────────────────────────────────────────────────────────────────

resource "aws_wafv2_web_acl" "main" {
  name        = "${local.name_prefix}-waf"
  scope       = "REGIONAL"
  description = "WAF for Execution Market ALB - rate limiting, IP reputation, blocklist"

  default_action {
    allow {}
  }

  # Rule 1: Static IP blocklist (highest priority — cheapest check)
  rule {
    name     = "ip-blocklist"
    priority = 1

    action {
      block {
        custom_response {
          response_code            = 403
          custom_response_body_key = "blocked"
        }
      }
    }

    statement {
      ip_set_reference_statement {
        arn = aws_wafv2_ip_set.blocklist.arn
      }
    }

    visibility_config {
      sampled_requests_enabled   = true
      cloudwatch_metrics_enabled = true
      metric_name                = "${local.name_prefix}-ip-blocklist"
    }
  }

  # Rule 2: AWS Managed — Common Rule Set (OWASP Top 10: SQLi, XSS, path traversal)
  # This is the broadest protection layer — catches general web exploits.
  rule {
    name     = "aws-common-rule-set"
    priority = 2

    override_action {
      none {}
    }

    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesCommonRuleSet"
        vendor_name = "AWS"

        # Exclude body size check — our API accepts variable-size JSON payloads
        # and evidence metadata. Application-layer middleware enforces 1MB limit.
        rule_action_override {
          name = "SizeRestrictions_BODY"
          action_to_use {
            count {}
          }
        }
      }
    }

    visibility_config {
      sampled_requests_enabled   = true
      cloudwatch_metrics_enabled = true
      metric_name                = "${local.name_prefix}-common-rule-set"
    }
  }

  # Rule 3: AWS Managed — Known Bad Inputs (Log4j, host header injection)
  rule {
    name     = "aws-known-bad-inputs"
    priority = 3

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
      metric_name                = "${local.name_prefix}-known-bad-inputs"
    }
  }

  # Rule 4: AWS Managed — Anonymous IP List (Tor exits, VPNs, hosting providers)
  #
  # IMPORTANT: HostingProviderIPList is set to COUNT-only because Execution
  # Market is an API for AI agents — agents overwhelmingly run on cloud infra
  # (AWS, GCP, Azure). Blocking hosting providers would block legitimate users.
  # Tor exits and anonymous proxies are still BLOCKED.
  rule {
    name     = "aws-anonymous-ip-list"
    priority = 4

    override_action {
      none {}
    }

    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesAnonymousIpList"
        vendor_name = "AWS"

        # Don't block hosting providers — AI agents run on cloud infra
        rule_action_override {
          name = "HostingProviderIPList"
          action_to_use {
            count {}
          }
        }
      }
    }

    visibility_config {
      sampled_requests_enabled   = true
      cloudwatch_metrics_enabled = true
      metric_name                = "${local.name_prefix}-anonymous-ip"
    }
  }

  # Rule 5: Stricter rate limit for /a2a/ path (100 requests per 5 minutes)
  # Priority BEFORE global rate limit so the stricter check fires first for A2A.
  rule {
    name     = "rate-limit-a2a"
    priority = 5

    action {
      block {
        custom_response {
          response_code            = 429
          custom_response_body_key = "rate-limited"
        }
      }
    }

    statement {
      rate_based_statement {
        limit              = 100
        aggregate_key_type = "IP"

        scope_down_statement {
          byte_match_statement {
            search_string         = "/a2a/"
            positional_constraint = "STARTS_WITH"

            field_to_match {
              uri_path {}
            }

            text_transformation {
              priority = 0
              type     = "LOWERCASE"
            }
          }
        }
      }
    }

    visibility_config {
      sampled_requests_enabled   = true
      cloudwatch_metrics_enabled = true
      metric_name                = "${local.name_prefix}-rate-limit-a2a"
    }
  }

  # Rule 6: Global rate limit — coarse safety net for volumetric abuse
  # Set to 600/5min (2 req/sec) to avoid false positives on legitimate AI agents
  # doing multi-step task lifecycles. App-layer rate limiters handle fine-grained
  # per-agent, per-endpoint throttling.
  rule {
    name     = "rate-limit-global"
    priority = 6

    action {
      block {
        custom_response {
          response_code            = 429
          custom_response_body_key = "rate-limited"
        }
      }
    }

    statement {
      rate_based_statement {
        limit              = 600
        aggregate_key_type = "IP"
      }
    }

    visibility_config {
      sampled_requests_enabled   = true
      cloudwatch_metrics_enabled = true
      metric_name                = "${local.name_prefix}-rate-limit-global"
    }
  }

  # Custom response bodies
  custom_response_body {
    key          = "blocked"
    content      = "{\"error\": \"forbidden\", \"message\": \"Access denied\"}"
    content_type = "APPLICATION_JSON"
  }

  custom_response_body {
    key          = "rate-limited"
    content      = "{\"error\": \"rate_limit_exceeded\", \"message\": \"Too many requests. Try again later.\"}"
    content_type = "APPLICATION_JSON"
  }

  visibility_config {
    sampled_requests_enabled   = true
    cloudwatch_metrics_enabled = true
    metric_name                = "${local.name_prefix}-waf"
  }

  tags = {
    Name = "${local.name_prefix}-waf"
  }
}

# ── WAF Logging ──────────────────────────────────────────────────────────────
# Log all WAF evaluations to CloudWatch for forensic analysis.
# Name MUST start with "aws-waf-logs-" (AWS requirement).
# Cost: ~$0.25/mo at current volume (~500K req/mo).

resource "aws_cloudwatch_log_group" "waf" {
  name              = "aws-waf-logs-${local.name_prefix}"
  retention_in_days = 90

  tags = {
    Name = "aws-waf-logs-${local.name_prefix}"
  }
}

resource "aws_wafv2_web_acl_logging_configuration" "main" {
  log_destination_configs = [aws_cloudwatch_log_group.waf.arn]
  resource_arn            = aws_wafv2_web_acl.main.arn

  # Only log BLOCK actions. ALLOW is 99%+ of traffic and not useful forensically.
  # Keeps log volume and cost bounded. See INC-2026-04-21 for why this matters:
  # earlier operator enabled WAF logging manually with this filter; Terraform plan
  # wanted to drop it because the filter wasn't codified. Now it is.
  logging_filter {
    default_behavior = "DROP"

    filter {
      behavior    = "KEEP"
      requirement = "MEETS_ANY"

      condition {
        action_condition {
          action = "BLOCK"
        }
      }
    }
  }
}

# ── Associate WAF with ALB ───────────────────────────────────────────────────

resource "aws_wafv2_web_acl_association" "alb" {
  resource_arn = aws_lb.main.arn
  web_acl_arn  = aws_wafv2_web_acl.main.arn
}

# ── CloudWatch Alarm: WAF blocked requests spike ────────────────────────────

resource "aws_cloudwatch_metric_alarm" "waf_blocked_requests" {
  alarm_name          = "${local.name_prefix}-waf-high-block-rate"
  alarm_description   = "WAF is blocking > 100 requests per 5 minutes - possible attack"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "BlockedRequests"
  namespace           = "AWS/WAFV2"
  period              = 300
  statistic           = "Sum"
  threshold           = 100
  treat_missing_data  = "notBreaching"

  dimensions = {
    WebACL = aws_wafv2_web_acl.main.name
    Region = local.region
    Rule   = "ALL"
  }

  alarm_actions = [aws_sns_topic.mcp_alerts.arn]

  tags = {
    Name     = "${local.name_prefix}-waf-high-block-rate"
    Severity = "warning"
  }
}
