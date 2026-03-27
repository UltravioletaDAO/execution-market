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
  evaluation_periods  = 1
  metric_name         = "RunningTaskCount"
  namespace           = "ECS/ContainerInsights"
  period              = 60
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
