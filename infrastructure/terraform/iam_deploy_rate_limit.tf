# Execution Market Infrastructure — Deploy Rate-Limit Alarm
#
# PURPOSE
#   Detect abnormal bursts of ecs:UpdateService calls from the
#   `execution-market-deployer` CI/CD user. This is an alarm, not a hard
#   block — we keep IAM permissions permissive so legitimate deploys never
#   fail, but a human is paged when the rate crosses a known-bad threshold.
#
#   Decision: Option B (observability) over Option A (IAM SourceIp/Region
#   condition). Rationale:
#     - Option A breaks legitimate local operator deploys from changing IPs.
#     - Option A requires maintaining GitHub Actions IP ranges (they change).
#     - Option B catches any abuse path (stolen key, compromised runner,
#       runaway automation) without blocking the normal flow.
#
# INCIDENT THAT MOTIVATED THIS
#   2026-04-12: 42 `UpdateService` calls within a 12-hour window (the
#   "deploy storm") while debugging Phase-B verification churn. The storm
#   went unnoticed because no alarm existed on deploy cadence.
#
# DATA SOURCE
#   CloudTrail trail `em-production-cloudtrail` (multi-region) publishes to
#   CloudWatch Logs group `/aws/cloudtrail/em-production` (retention 90d,
#   already populated by existing em-production-* metric filters).
#
# THRESHOLD SELECTION
#   Baseline: normal deploys = 0–3 per day, bursty releases = up to 6/day.
#   10 UpdateService calls in 1 hour (sum over 12 x 5-min periods) is a
#   clear outlier — anything near 42/12h storm rate triggers in <=1 hour.
#   One 5-min period alarms; we do not require datapoints-to-alarm because
#   the sum is already a rolling total.

# ── CloudWatch Log Metric Filter ─────────────────────────────────────────────

resource "aws_cloudwatch_log_metric_filter" "deployer_update_service" {
  name           = "${local.name_prefix}-deployer-update-service"
  log_group_name = "/aws/cloudtrail/em-production"

  # Pattern matches the CloudTrail event when the deployer user calls
  # ecs:UpdateService. Covers any UpdateService (FargateTaskCount,
  # ForceNewDeployment, etc.) — we care about call cadence, not intent.
  pattern = "{ ($.eventName = \"UpdateService\") && ($.userIdentity.userName = \"execution-market-deployer\") && ($.eventSource = \"ecs.amazonaws.com\") }"

  metric_transformation {
    name          = "DeployerUpdateServiceCalls"
    namespace     = "ExecutionMarket/IAM"
    value         = "1"
    default_value = "0"
    unit          = "Count"
  }
}

# ── CloudWatch Alarm ─────────────────────────────────────────────────────────
# Alarm condition:
#   Sum of DeployerUpdateServiceCalls over a 1-hour window (12 x 5-min)
#   >= 10 triggers. Publishes to existing mcp_alerts SNS topic (same
#   inbox as other em-production critical alarms).

resource "aws_cloudwatch_metric_alarm" "deployer_update_service_burst" {
  alarm_name          = "${local.name_prefix}-deployer-update-service-burst"
  alarm_description   = "execution-market-deployer issued >= 10 ecs:UpdateService calls in the last hour. Likely deploy storm or stolen credential. Check CloudTrail and consider disabling the access key."
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 12
  datapoints_to_alarm = 1
  metric_name         = "DeployerUpdateServiceCalls"
  namespace           = "ExecutionMarket/IAM"
  period              = 300
  statistic           = "Sum"
  threshold           = 10
  treat_missing_data  = "notBreaching"

  alarm_actions = [aws_sns_topic.mcp_alerts.arn]
  ok_actions    = [aws_sns_topic.mcp_alerts.arn]

  tags = {
    Name     = "${local.name_prefix}-deployer-update-service-burst"
    Severity = "warning"
    Purpose  = "deployer-abuse-detection"
  }
}
