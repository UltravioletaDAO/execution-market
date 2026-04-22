# Execution Market Infrastructure - Monitoring & Alerting
#
# CloudWatch alarms for the MCP server (ECS Fargate) and ALB health.
# All alarms publish to SNS topics with automatic email subscription.
# After `terraform apply`, confirm the subscription via the link in your inbox.

# ── SNS Topic ────────────────────────────────────────────────────────────────

resource "aws_sns_topic" "mcp_alerts" {
  name = "${local.name_prefix}-mcp-alerts"

  tags = {
    Name = "${local.name_prefix}-mcp-alerts"
  }
}

# Email subscription — confirm via inbox after first apply
resource "aws_sns_topic_subscription" "mcp_alerts_email" {
  count     = var.alert_email != "" ? 1 : 0
  topic_arn = aws_sns_topic.mcp_alerts.arn
  protocol  = "email"
  endpoint  = var.alert_email
}

# ── Alarm 1: Running Task Count = 0 (SERVICE DOWN) ──────────────────────────
# Container Insights metric. If no tasks are running the service is fully down.
# treat_missing_data = "breaching" because missing data likely means the service
# (or Container Insights) itself is gone.

resource "aws_cloudwatch_metric_alarm" "mcp_no_running_tasks" {
  alarm_name          = "${local.name_prefix}-mcp-no-running-tasks"
  alarm_description   = "MCP server has zero running tasks — service is DOWN"
  comparison_operator = "LessThanThreshold"
  # Recalibrated from 1/60s to 3x300s with 2/3 datapoints-to-alarm to
  # debounce rolling-deploy blips. Sustained miss ≥10 min pages.
  evaluation_periods  = 3
  datapoints_to_alarm = 2
  metric_name         = "RunningTaskCount"
  namespace           = "ECS/ContainerInsights"
  period              = 300
  statistic           = "Minimum"
  threshold           = 1
  treat_missing_data  = "breaching"

  dimensions = {
    ClusterName = aws_ecs_cluster.main.name
    ServiceName = aws_ecs_service.mcp_server.name
  }

  alarm_actions = [aws_sns_topic.mcp_alerts.arn]
  ok_actions    = [aws_sns_topic.mcp_alerts.arn]

  tags = {
    Name     = "${local.name_prefix}-mcp-no-running-tasks"
    Severity = "critical"
  }
}

# ── Alarm 2: Memory Utilization > 80% (OOM RISK) ────────────────────────────
# History: 256/512 → OOM kills, 512/1024 → tight, now at 1024/2048.
# 80% of 2048 MB = ~1638 MB. Two consecutive breaches to avoid transient spikes.

resource "aws_cloudwatch_metric_alarm" "mcp_high_memory" {
  alarm_name          = "${local.name_prefix}-mcp-high-memory"
  alarm_description   = "MCP server memory > 80% — OOM risk (current limit: ${var.mcp_server_memory} MB)"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "MemoryUtilization"
  namespace           = "AWS/ECS"
  period              = 60
  statistic           = "Maximum"
  threshold           = 80
  treat_missing_data  = "notBreaching"

  dimensions = {
    ClusterName = aws_ecs_cluster.main.name
    ServiceName = aws_ecs_service.mcp_server.name
  }

  alarm_actions = [aws_sns_topic.mcp_alerts.arn]
  ok_actions    = [aws_sns_topic.mcp_alerts.arn]

  tags = {
    Name     = "${local.name_prefix}-mcp-high-memory"
    Severity = "warning"
  }
}

# ── Alarm 3: 5xx Errors > 5 in 1 minute ─────────────────────────────────────
# Catches backend crashes, unhandled exceptions, or upstream failures.

resource "aws_cloudwatch_metric_alarm" "mcp_5xx_errors" {
  alarm_name          = "${local.name_prefix}-mcp-5xx-errors"
  alarm_description   = "MCP server target returning > 5 HTTP 5xx errors per minute"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "HTTPCode_Target_5XX_Count"
  namespace           = "AWS/ApplicationELB"
  period              = 60
  statistic           = "Sum"
  threshold           = 5
  treat_missing_data  = "notBreaching"

  dimensions = {
    TargetGroup  = aws_lb_target_group.mcp_server.arn_suffix
    LoadBalancer = aws_lb.main.arn_suffix
  }

  alarm_actions = [aws_sns_topic.mcp_alerts.arn]
  ok_actions    = [aws_sns_topic.mcp_alerts.arn]

  tags = {
    Name     = "${local.name_prefix}-mcp-5xx-errors"
    Severity = "critical"
  }
}

# ── Alarm 4: Unhealthy Host Count > 0 ───────────────────────────────────────
# ALB health check failures. If a target is unhealthy, requests will fail or
# be routed to the remaining healthy targets (if any).

resource "aws_cloudwatch_metric_alarm" "mcp_unhealthy_hosts" {
  alarm_name          = "${local.name_prefix}-mcp-unhealthy-hosts"
  alarm_description   = "MCP server has unhealthy targets in ALB target group"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "UnHealthyHostCount"
  namespace           = "AWS/ApplicationELB"
  period              = 60
  statistic           = "Maximum"
  threshold           = 0
  treat_missing_data  = "notBreaching"

  dimensions = {
    TargetGroup  = aws_lb_target_group.mcp_server.arn_suffix
    LoadBalancer = aws_lb.main.arn_suffix
  }

  alarm_actions = [aws_sns_topic.mcp_alerts.arn]
  ok_actions    = [aws_sns_topic.mcp_alerts.arn]

  tags = {
    Name     = "${local.name_prefix}-mcp-unhealthy-hosts"
    Severity = "warning"
  }
}

# ── Alarm 5: 4xx Spike > 50/min (ABUSE DETECTION) ───────────────────────────
# Catches unauthorized request floods (e.g., Tor bots hitting /a2a/ with 401).
# Added 2026-04-04 after discovering 20.5% of traffic was 4xx junk.

resource "aws_cloudwatch_metric_alarm" "mcp_4xx_spike" {
  alarm_name          = "${local.name_prefix}-mcp-4xx-spike"
  alarm_description   = "MCP server target returning > 50 HTTP 4xx per minute — possible abuse"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 3
  metric_name         = "HTTPCode_Target_4XX_Count"
  namespace           = "AWS/ApplicationELB"
  period              = 60
  statistic           = "Sum"
  threshold           = 50
  treat_missing_data  = "notBreaching"

  dimensions = {
    TargetGroup  = aws_lb_target_group.mcp_server.arn_suffix
    LoadBalancer = aws_lb.main.arn_suffix
  }

  alarm_actions = [aws_sns_topic.mcp_alerts.arn]
  ok_actions    = [aws_sns_topic.mcp_alerts.arn]

  tags = {
    Name     = "${local.name_prefix}-mcp-4xx-spike"
    Severity = "warning"
  }
}

# ── Alarm 6: Magika Rejection Rate > 5% (FALSE POSITIVE SURGE DETECTION) ────
# Custom metric emitted by verification/cloudwatch_metrics.run_magika_metrics_loop().
# Namespace: ExecutionMarket/Verification / Metric: MagikaRejectionRate
# If Magika rejects > 5% of files in a 5-minute window for 2 consecutive
# periods, it indicates a likely false-positive surge or model regression.
# Operator action: set feature.magika.enabled=false in platform_config (< 30s).
# treat_missing_data = "notBreaching": no submissions = no alarm (expected during quiet periods).
# Added: 2026-04-14 (Fase 4 — MASTER_PLAN_MAGIKA_INTEGRATION)
# Emitter implemented 2026-04-21. Flip `enable_magika_alarm=true` via tfvars
# after confirming MagikaRejectionRate datapoints are flowing.
resource "aws_cloudwatch_metric_alarm" "magika_high_rejection_rate" {
  count               = var.enable_magika_alarm ? 1 : 0
  alarm_name          = "${local.name_prefix}-magika-high-rejection-rate"
  alarm_description   = "Magika is rejecting > 5% of evidence files — possible false-positive surge or model regression. Disable via: UPDATE platform_config SET value='{\"enabled\":false}' WHERE key='feature.magika'"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "MagikaRejectionRate"
  namespace           = "ExecutionMarket/Verification"
  period              = 300 # 5 minutes
  statistic           = "Average"
  threshold           = 5.0 # > 5% rejection rate
  treat_missing_data  = "notBreaching"

  alarm_actions = [aws_sns_topic.mcp_alerts.arn]
  ok_actions    = [aws_sns_topic.mcp_alerts.arn]

  tags = {
    Name     = "${local.name_prefix}-magika-high-rejection-rate"
    Severity = "warning"
  }
}

# ── Alarm 7: Arbiter Zombie Dispute (INC-2026-04-22) ────────────────────────
# Log-based metric filter. After Phase 1 of MASTER_PLAN_ARBITER_ZOMBIE_DISPUTE_FIX,
# escalate_to_human() should only run from the explicit POST /api/v1/disputes
# endpoint (Phase 3) — never from the arbiter processor. Any occurrence of
# "Created L2 dispute" in the MCP logs means:
#   (a) we regressed and the auto-escalation came back, OR
#   (b) a publisher/worker explicitly opened a dispute via the new endpoint.
# Either way, we want eyes on it during the stabilization window.
#
# The log pattern `"Created L2 dispute"` is emitted by escalation.py:120.
# Metric is a Count; alarm fires on >= 1 occurrences in 5 min, sustained
# across 2 datapoints = ≥2 auto-escalations in 10 min.

resource "aws_cloudwatch_log_metric_filter" "arbiter_l2_dispute_created" {
  name           = "${local.name_prefix}-arbiter-l2-dispute-created"
  log_group_name = aws_cloudwatch_log_group.mcp_server.name
  # Literal-substring match: every log line from escalation.py that creates
  # a dispute. The surrounding quotes make it match the exact phrase.
  pattern = "\"Created L2 dispute\""

  metric_transformation {
    name          = "ArbiterL2DisputeCreated"
    namespace     = "ExecutionMarket/Arbiter"
    value         = "1"
    default_value = "0"
    unit          = "Count"
  }
}

resource "aws_cloudwatch_metric_alarm" "arbiter_zombie_escalation" {
  alarm_name          = "${local.name_prefix}-arbiter-zombie-escalation"
  alarm_description   = "Ring 2 auto-escalation to dispute detected (INC-2026-04-22). After Phase 1 fix, escalate_to_human should only fire from explicit POST /api/v1/disputes. Any hit = regression or explicit dispute — investigate."
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 2
  datapoints_to_alarm = 1
  metric_name         = "ArbiterL2DisputeCreated"
  namespace           = "ExecutionMarket/Arbiter"
  period              = 300 # 5 minutes
  statistic           = "Sum"
  threshold           = 1
  treat_missing_data  = "notBreaching"

  alarm_actions = [aws_sns_topic.mcp_alerts.arn]
  ok_actions    = [aws_sns_topic.mcp_alerts.arn]

  tags = {
    Name     = "${local.name_prefix}-arbiter-zombie-escalation"
    Severity = "warning"
    Incident = "INC-2026-04-22"
  }
}

# ── CloudWatch Dashboard ─────────────────────────────────────────────────────
# 6 widgets: task counts, memory, CPU, 5xx, response time, unhealthy hosts.

resource "aws_cloudwatch_dashboard" "mcp_server" {
  dashboard_name = "${local.name_prefix}-mcp-server"

  dashboard_body = jsonencode({
    widgets = [
      # Row 1: ECS task health
      {
        type   = "metric"
        x      = 0
        y      = 0
        width  = 12
        height = 6
        properties = {
          title   = "Running vs Desired Tasks"
          view    = "timeSeries"
          stacked = false
          region  = local.region
          period  = 60
          metrics = [
            [
              "ECS/ContainerInsights", "RunningTaskCount",
              "ClusterName", aws_ecs_cluster.main.name,
              "ServiceName", aws_ecs_service.mcp_server.name,
              { label = "Running", color = "#2ca02c" }
            ],
            [
              "ECS/ContainerInsights", "DesiredTaskCount",
              "ClusterName", aws_ecs_cluster.main.name,
              "ServiceName", aws_ecs_service.mcp_server.name,
              { label = "Desired", color = "#1f77b4" }
            ]
          ]
        }
      },
      {
        type   = "metric"
        x      = 12
        y      = 0
        width  = 12
        height = 6
        properties = {
          title   = "Memory Utilization (%)"
          view    = "timeSeries"
          stacked = false
          region  = local.region
          period  = 60
          stat    = "Maximum"
          metrics = [
            [
              "AWS/ECS", "MemoryUtilization",
              "ClusterName", aws_ecs_cluster.main.name,
              "ServiceName", aws_ecs_service.mcp_server.name,
              { label = "Memory (max)", color = "#d62728" }
            ]
          ]
          annotations = {
            horizontal = [
              {
                label = "OOM Risk (80%)"
                value = 80
                color = "#d62728"
              }
            ]
          }
        }
      },
      # Row 2: CPU and 5xx
      {
        type   = "metric"
        x      = 0
        y      = 6
        width  = 12
        height = 6
        properties = {
          title   = "CPU Utilization (%)"
          view    = "timeSeries"
          stacked = false
          region  = local.region
          period  = 60
          stat    = "Maximum"
          metrics = [
            [
              "AWS/ECS", "CPUUtilization",
              "ClusterName", aws_ecs_cluster.main.name,
              "ServiceName", aws_ecs_service.mcp_server.name,
              { label = "CPU (max)", color = "#ff7f0e" }
            ]
          ]
          annotations = {
            horizontal = [
              {
                label = "Scale-out threshold (60%)"
                value = 60
                color = "#ff7f0e"
              }
            ]
          }
        }
      },
      {
        type   = "metric"
        x      = 12
        y      = 6
        width  = 12
        height = 6
        properties = {
          title   = "HTTP 5xx Errors"
          view    = "bar"
          stacked = false
          region  = local.region
          period  = 60
          stat    = "Sum"
          metrics = [
            [
              "AWS/ApplicationELB", "HTTPCode_Target_5XX_Count",
              "TargetGroup", aws_lb_target_group.mcp_server.arn_suffix,
              "LoadBalancer", aws_lb.main.arn_suffix,
              { label = "5xx Count", color = "#d62728" }
            ]
          ]
        }
      },
      # Row 3: Response time and unhealthy hosts
      {
        type   = "metric"
        x      = 0
        y      = 12
        width  = 12
        height = 6
        properties = {
          title   = "Target Response Time (seconds)"
          view    = "timeSeries"
          stacked = false
          region  = local.region
          period  = 60
          metrics = [
            [
              "AWS/ApplicationELB", "TargetResponseTime",
              "TargetGroup", aws_lb_target_group.mcp_server.arn_suffix,
              "LoadBalancer", aws_lb.main.arn_suffix,
              { stat = "Average", label = "Avg", color = "#1f77b4" }
            ],
            [
              "AWS/ApplicationELB", "TargetResponseTime",
              "TargetGroup", aws_lb_target_group.mcp_server.arn_suffix,
              "LoadBalancer", aws_lb.main.arn_suffix,
              { stat = "p99", label = "p99", color = "#d62728" }
            ]
          ]
        }
      },
      {
        type   = "metric"
        x      = 12
        y      = 12
        width  = 12
        height = 6
        properties = {
          title  = "Unhealthy Hosts"
          view   = "singleValue"
          region = local.region
          period = 60
          stat   = "Maximum"
          metrics = [
            [
              "AWS/ApplicationELB", "UnHealthyHostCount",
              "TargetGroup", aws_lb_target_group.mcp_server.arn_suffix,
              "LoadBalancer", aws_lb.main.arn_suffix,
              { label = "Unhealthy", color = "#d62728" }
            ]
          ]
        }
      }
    ]
  })
}
