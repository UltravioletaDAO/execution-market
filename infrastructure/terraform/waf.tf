# Execution Market Infrastructure - AWS WAF v2
#
# WAF Web ACL attached to the ALB. Provides:
# 1. Static IP blocklist for confirmed abusers
# 2. AWS Managed Common Rule Set (OWASP Top 10: SQLi, XSS, path traversal)
# 3. AWS Managed Known Bad Inputs (Log4j, host header injection)
# 4. AWS Managed Amazon IP Reputation List (known scanners, botnets, abusive VPS)
# 5. AWS Managed Anonymous IP List (Tor exits — hosting providers COUNT-only)
# 6. Stricter rate limit for non-legitimate Host headers (50 req/5min)
# 7. A2A-specific rate limit: 100 req/5min for /a2a/ path
# 8. Global rate limit: 600 req/5min per IP (coarse safety net)
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

  # Rule 4: AWS Managed — Amazon IP Reputation List (added 2026-05-13)
  # Blocks IPs identified by AWS threat intelligence: known scanners, botnets,
  # malicious actors, and IPs associated with bitcoin/DDoS abuse. Catches abusive
  # VPS providers (Contabo, Hetzner, OVH, etc.) automatically without manual CIDR
  # maintenance. Replaces the brittle approach of blocking AS51167 by CIDR.
  rule {
    name     = "aws-amazon-ip-reputation"
    priority = 4

    override_action {
      none {}
    }

    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesAmazonIpReputationList"
        vendor_name = "AWS"
      }
    }

    visibility_config {
      sampled_requests_enabled   = true
      cloudwatch_metrics_enabled = true
      metric_name                = "${local.name_prefix}-amazon-ip-reputation"
    }
  }

  # Rule 5: AWS Managed — Anonymous IP List (Tor exits, VPNs, hosting providers)
  #
  # IMPORTANT: HostingProviderIPList is set to COUNT-only because Execution
  # Market is an API for AI agents — agents overwhelmingly run on cloud infra
  # (AWS, GCP, Azure). Blocking hosting providers would block legitimate users.
  # Tor exits and anonymous proxies are still BLOCKED.
  rule {
    name     = "aws-anonymous-ip-list"
    priority = 5

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

  # Rule 6: Strict rate limit for non-legitimate Host headers (added 2026-05-13)
  #
  # Legitimate clients ALWAYS use one of our DNS hostnames as the Host header
  # (mcp.execution.market, api.execution.market, admin.execution.market).
  # Scanners typically hit the raw ALB IP — Host header becomes the IP itself.
  #
  # This rule fires BEFORE rate-limit-global (lower priority number) so abusive
  # IP-direct traffic is throttled aggressively at 50 req/5min/IP, regardless
  # of whether the global 600 threshold has been crossed.
  #
  # Scope-down: rate-limit ONLY requests whose Host header is NOT one of our
  # legitimate hostnames. Built via AND(NOT host=mcp, NOT host=api, NOT host=admin).
  #
  # SAFETY NOTE re: ALB health checks — ALB->target health checks run inside the
  # VPC and never traverse this WAF (WAF only inspects external client requests),
  # so this rule cannot affect them. External uptime probes (Pingdom, StatusCake,
  # canaries) that target real hostnames are unaffected.
  rule {
    name     = "rate-limit-bad-host"
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
        limit              = 50
        aggregate_key_type = "IP"

        scope_down_statement {
          and_statement {
            statement {
              not_statement {
                statement {
                  byte_match_statement {
                    search_string         = "mcp.${var.domain_name}"
                    positional_constraint = "EXACTLY"
                    field_to_match {
                      single_header {
                        name = "host"
                      }
                    }
                    text_transformation {
                      priority = 0
                      type     = "LOWERCASE"
                    }
                  }
                }
              }
            }
            statement {
              not_statement {
                statement {
                  byte_match_statement {
                    search_string         = "api.${var.domain_name}"
                    positional_constraint = "EXACTLY"
                    field_to_match {
                      single_header {
                        name = "host"
                      }
                    }
                    text_transformation {
                      priority = 0
                      type     = "LOWERCASE"
                    }
                  }
                }
              }
            }
            statement {
              not_statement {
                statement {
                  byte_match_statement {
                    search_string         = "admin.${var.domain_name}"
                    positional_constraint = "EXACTLY"
                    field_to_match {
                      single_header {
                        name = "host"
                      }
                    }
                    text_transformation {
                      priority = 0
                      type     = "LOWERCASE"
                    }
                  }
                }
              }
            }
          }
        }
      }
    }

    visibility_config {
      sampled_requests_enabled   = true
      cloudwatch_metrics_enabled = true
      metric_name                = "${local.name_prefix}-rate-limit-bad-host"
    }
  }

  # Rule 7: Stricter rate limit for /a2a/ path (100 requests per 5 minutes)
  # Priority BEFORE global rate limit so the stricter check fires first for A2A.
  rule {
    name     = "rate-limit-a2a"
    priority = 7

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

  # Rule 8: Global rate limit — coarse safety net for volumetric abuse
  # Set to 600/5min (2 req/sec) to avoid false positives on legitimate AI agents
  # doing multi-step task lifecycles. App-layer rate limiters handle fine-grained
  # per-agent, per-endpoint throttling.
  rule {
    name     = "rate-limit-global"
    priority = 8

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

# ── CloudWatch Alarms: WAF block-rate (split by signal) ─────────────────────
#
# WHY THE SPLIT (replaces the old single "waf-high-block-rate" alarm).
#   The original alarm watched Rule="ALL" with threshold 100/5min. After the
#   xmtp-bot self-block bug was fixed (it no longer generates blocks), the WAF
#   still blocks internet background scanners (phpunit/.env/webshell probes).
#   A 14-day baseline (2026-05-13 → 2026-05-26) measured at TRUE 5-min
#   granularity shows steady-state ALL-rule scanner bursts of 145–265 blocks/
#   5min (peak 265 on 2026-05-24 19:05). With threshold 100, the alarm flapped
#   continuously (e.g. ALARM 14:25 → OK 14:30 on 2026-05-27) on pure noise.
#
#   A single raised threshold (e.g. 750/ALL) would silence the noise but would
#   ALSO mask a targeted exploit campaign against one managed rule, because the
#   scanner noise floor (~265) would dominate the aggregate. So we split by
#   SIGNAL into two alarms with distinct, individually-justified thresholds:
#
#   1. known-bad-inputs — real exploit probes (AWSManagedRulesKnownBadInputsRuleSet).
#      14-day per-rule 5-min peak = 38 blocks. Threshold 100 (~2.6x peak) with
#      M-of-N (10 of 15 min) only fires on a sustained, coordinated campaign.
#   2. rate-limit-global — a single IP exceeded 600 req/5min (the rate rule's
#      limit). Legit AI agents stay < 2 req/s, so any sustained trip is a real
#      volumetric flood. 14-day per-rule 5-min level is negligible; threshold
#      500 with M-of-N fires only on a genuine sustained flood.
#
# CloudWatch dimension note: the per-rule "Rule" dimension value equals each
# rule's visibility_config.metric_name (NOT the rule "name"). Hence the
# "-known-bad-inputs" / "-rate-limit-global" suffixes below match Rule 3 and
# Rule 8 metric_name fields verbatim.

resource "aws_cloudwatch_metric_alarm" "waf_known_bad_inputs" {
  alarm_name          = "${local.name_prefix}-waf-known-bad-inputs"
  alarm_description   = "WAF blocked > 100 known-bad-input (exploit) requests per 5min for 2 of 3 periods - likely targeted attack campaign (baseline peak 38/5min)"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 3
  datapoints_to_alarm = 2
  metric_name         = "BlockedRequests"
  namespace           = "AWS/WAFV2"
  period              = 300
  statistic           = "Sum"
  threshold           = 100
  treat_missing_data  = "notBreaching"

  dimensions = {
    WebACL = aws_wafv2_web_acl.main.name
    Region = local.region
    Rule   = "${local.name_prefix}-known-bad-inputs"
  }

  alarm_actions = [aws_sns_topic.mcp_alerts.arn]
  ok_actions    = [aws_sns_topic.mcp_alerts.arn]

  tags = {
    Name     = "${local.name_prefix}-waf-known-bad-inputs"
    Severity = "warning"
  }
}

resource "aws_cloudwatch_metric_alarm" "waf_rate_limit_global" {
  alarm_name          = "${local.name_prefix}-waf-rate-limit-global"
  alarm_description   = "WAF global rate-limit blocked > 500 requests per 5min for 2 of 3 periods - sustained volumetric flood (IP exceeding 600 req/5min; legit agents are < 2 req/s)"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 3
  datapoints_to_alarm = 2
  metric_name         = "BlockedRequests"
  namespace           = "AWS/WAFV2"
  period              = 300
  statistic           = "Sum"
  threshold           = 500
  treat_missing_data  = "notBreaching"

  dimensions = {
    WebACL = aws_wafv2_web_acl.main.name
    Region = local.region
    Rule   = "${local.name_prefix}-rate-limit-global"
  }

  alarm_actions = [aws_sns_topic.mcp_alerts.arn]
  ok_actions    = [aws_sns_topic.mcp_alerts.arn]

  tags = {
    Name     = "${local.name_prefix}-waf-rate-limit-global"
    Severity = "warning"
  }
}
