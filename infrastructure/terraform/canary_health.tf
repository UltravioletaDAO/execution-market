# Execution Market Infrastructure — External Synthetic Canary (Route53 Health Checks)
#
# PURPOSE
#   Detect external-facing outages that CloudWatch internal ECS/ALB alarms
#   miss: DNS failures, certificate expiry, CloudFront misconfiguration,
#   Route53 propagation issues. Route53 health checks probe from multiple
#   AWS edge regions, giving us a view from the public internet.
#
# DECISION: OPTION A (Route53 HealthCheck) vs OPTION B (CloudWatch Synthetics)
#   Picked A. Reasons:
#     - $0.50/mo per health check vs ~$1.30/mo minimum per Synthetics canary
#       + Lambda costs + S3 artifact storage.
#     - Route53 alarms land in CloudWatch natively (AWS/Route53 namespace).
#     - Simpler: no script maintenance, no IAM execution role.
#     - Downside: only checks HTTP status code and cert validity; cannot
#       exercise login, API payment flow, or multi-step scenarios.
#   If we later need scenario-level checks (e.g., full Golden Flow via
#   synthetic), migrate to CloudWatch Synthetics at that point.
#
# MONITORED ENDPOINTS
#   1. https://mcp.execution.market/health  — MCP API liveness
#   2. https://execution.market/            — Dashboard (CloudFront)
#   3. https://admin.execution.market/      — Admin dashboard (CloudFront)
#      (We probe "/" rather than "/health" because admin CloudFront does
#      not proxy to ECS — it serves the SPA index.html. A 200 on "/"
#      confirms the bucket + distribution + DNS + cert path is healthy.)
#
# REGIONS
#   us-east-1, us-west-2, eu-west-1 (3 quorum). Route53 health checks are
#   always billed at the global endpoint, region list is about diversity
#   of probe origin — AWS bills ~$0.75/hc/mo base + $0.01/hc/mo per region
#   (negligible). Total expected: ~$3/mo across 3 endpoints.
#
# ALARM LOGIC
#   HealthCheckStatus (AWS/Route53) = 1 when healthy, 0 when unhealthy.
#   Alarm fires when status < 1 for 2 of 3 consecutive 1-min periods
#   (Route53 metric is emitted every 1 minute regardless of check interval).
#   Alarms publish to existing mcp_alerts SNS topic.
#
# IMPORTANT — CloudWatch region for Route53 metrics
#   Route53 health check metrics are ONLY emitted to us-east-1. Alarms on
#   them MUST be created in us-east-1. The `aws.us_east_1` aliased provider
#   is already declared in dashboard-cdn.tf (for CloudFront ACM cert); we
#   reuse it here rather than declaring a duplicate.

# ── Health Check 1: MCP API ──────────────────────────────────────────────────

resource "aws_route53_health_check" "mcp_api" {
  count             = var.enable_canary_health_checks ? 1 : 0
  fqdn              = "mcp.execution.market"
  type              = "HTTPS"
  port              = 443
  resource_path     = "/health"
  request_interval  = 30
  failure_threshold = 3

  regions = ["us-east-1", "us-west-2", "eu-west-1"]

  measure_latency    = true
  enable_sni         = true
  invert_healthcheck = false

  tags = {
    Name     = "${local.name_prefix}-canary-mcp-api"
    Endpoint = "mcp.execution.market/health"
    Severity = "critical"
  }
}

resource "aws_cloudwatch_metric_alarm" "canary_mcp_api" {
  count               = var.enable_canary_health_checks ? 1 : 0
  provider            = aws.us_east_1
  alarm_name          = "${local.name_prefix}-canary-mcp-api-down"
  alarm_description   = "External probes from us-east-1/us-west-2/eu-west-1 cannot reach https://mcp.execution.market/health. Either the service is down or DNS/cert/CloudFront is broken."
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = 3
  datapoints_to_alarm = 2
  metric_name         = "HealthCheckStatus"
  namespace           = "AWS/Route53"
  period              = 60
  statistic           = "Minimum"
  threshold           = 1
  treat_missing_data  = "breaching"

  dimensions = {
    HealthCheckId = aws_route53_health_check.mcp_api[0].id
  }

  alarm_actions = [aws_sns_topic.mcp_alerts.arn]
  ok_actions    = [aws_sns_topic.mcp_alerts.arn]

  tags = {
    Name     = "${local.name_prefix}-canary-mcp-api-down"
    Severity = "critical"
  }
}

# ── Health Check 2: Dashboard (public landing) ───────────────────────────────

resource "aws_route53_health_check" "dashboard" {
  count             = var.enable_canary_health_checks ? 1 : 0
  fqdn              = "execution.market"
  type              = "HTTPS"
  port              = 443
  resource_path     = "/"
  request_interval  = 30
  failure_threshold = 3

  regions = ["us-east-1", "us-west-2", "eu-west-1"]

  measure_latency    = true
  enable_sni         = true
  invert_healthcheck = false

  tags = {
    Name     = "${local.name_prefix}-canary-dashboard"
    Endpoint = "execution.market/"
    Severity = "critical"
  }
}

resource "aws_cloudwatch_metric_alarm" "canary_dashboard" {
  count               = var.enable_canary_health_checks ? 1 : 0
  provider            = aws.us_east_1
  alarm_name          = "${local.name_prefix}-canary-dashboard-down"
  alarm_description   = "External probes cannot reach https://execution.market/. S3+CloudFront dashboard is unavailable."
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = 3
  datapoints_to_alarm = 2
  metric_name         = "HealthCheckStatus"
  namespace           = "AWS/Route53"
  period              = 60
  statistic           = "Minimum"
  threshold           = 1
  treat_missing_data  = "breaching"

  dimensions = {
    HealthCheckId = aws_route53_health_check.dashboard[0].id
  }

  alarm_actions = [aws_sns_topic.mcp_alerts.arn]
  ok_actions    = [aws_sns_topic.mcp_alerts.arn]

  tags = {
    Name     = "${local.name_prefix}-canary-dashboard-down"
    Severity = "critical"
  }
}

# ── Health Check 3: Admin Dashboard ──────────────────────────────────────────

resource "aws_route53_health_check" "admin_dashboard" {
  count             = var.enable_canary_health_checks ? 1 : 0
  fqdn              = "admin.execution.market"
  type              = "HTTPS"
  port              = 443
  resource_path     = "/"
  request_interval  = 30
  failure_threshold = 3

  regions = ["us-east-1", "us-west-2", "eu-west-1"]

  measure_latency    = true
  enable_sni         = true
  invert_healthcheck = false

  tags = {
    Name     = "${local.name_prefix}-canary-admin"
    Endpoint = "admin.execution.market/"
    Severity = "warning"
  }
}

resource "aws_cloudwatch_metric_alarm" "canary_admin_dashboard" {
  count               = var.enable_canary_health_checks ? 1 : 0
  provider            = aws.us_east_1
  alarm_name          = "${local.name_prefix}-canary-admin-down"
  alarm_description   = "External probes cannot reach https://admin.execution.market/. Admin SPA may be down (S3+CloudFront)."
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = 3
  datapoints_to_alarm = 2
  metric_name         = "HealthCheckStatus"
  namespace           = "AWS/Route53"
  period              = 60
  statistic           = "Minimum"
  threshold           = 1
  treat_missing_data  = "breaching"

  dimensions = {
    HealthCheckId = aws_route53_health_check.admin_dashboard[0].id
  }

  alarm_actions = [aws_sns_topic.mcp_alerts.arn]
  ok_actions    = [aws_sns_topic.mcp_alerts.arn]

  tags = {
    Name     = "${local.name_prefix}-canary-admin-down"
    Severity = "warning"
  }
}

# ── Outputs ──────────────────────────────────────────────────────────────────

output "canary_health_check_ids" {
  description = "IDs of the Route53 health checks created for external canary monitoring (null when var.enable_canary_health_checks=false)."
  value = var.enable_canary_health_checks ? {
    mcp_api         = aws_route53_health_check.mcp_api[0].id
    dashboard       = aws_route53_health_check.dashboard[0].id
    admin_dashboard = aws_route53_health_check.admin_dashboard[0].id
  } : null
}
