# =============================================================================
# KarmaCadabra Swarm — Cost Alerting Module
# =============================================================================
# CloudWatch Alarms + SNS for budget control.
# Sends email alerts when spending exceeds thresholds.
# =============================================================================

# SNS Topic for alerts
resource "aws_sns_topic" "cost_alerts" {
  name = "kk-swarm-cost-alerts"

  tags = {
    Name = "kk-swarm-cost-alerts"
  }
}

resource "aws_sns_topic_subscription" "email" {
  count     = var.alert_email != "" ? 1 : 0
  topic_arn = aws_sns_topic.cost_alerts.arn
  protocol  = "email"
  endpoint  = var.alert_email
}

# -----------------------------------------------------------------------------
# ECS Service CPU/Memory Alarms
# -----------------------------------------------------------------------------

# High CPU across cluster (might indicate runaway agents)
resource "aws_cloudwatch_metric_alarm" "cluster_cpu_high" {
  alarm_name          = "kk-swarm-cluster-cpu-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 3
  metric_name         = "CPUUtilization"
  namespace           = "AWS/ECS"
  period              = 300
  statistic           = "Average"
  threshold           = 80
  alarm_description   = "KarmaCadabra cluster CPU > 80% for 15 minutes"
  alarm_actions       = [aws_sns_topic.cost_alerts.arn]

  dimensions = {
    ClusterName = var.cluster_name
  }

  tags = {
    Name = "kk-swarm-cpu-alarm"
  }
}

# High memory (potential memory leak)
resource "aws_cloudwatch_metric_alarm" "cluster_memory_high" {
  alarm_name          = "kk-swarm-cluster-memory-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 3
  metric_name         = "MemoryUtilization"
  namespace           = "AWS/ECS"
  period              = 300
  statistic           = "Average"
  threshold           = 85
  alarm_description   = "KarmaCadabra cluster memory > 85% for 15 minutes"
  alarm_actions       = [aws_sns_topic.cost_alerts.arn]

  dimensions = {
    ClusterName = var.cluster_name
  }

  tags = {
    Name = "kk-swarm-memory-alarm"
  }
}

# -----------------------------------------------------------------------------
# NAT Gateway Data Transfer (biggest surprise cost risk)
# -----------------------------------------------------------------------------
resource "aws_cloudwatch_metric_alarm" "nat_bytes_out" {
  alarm_name          = "kk-swarm-nat-data-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "BytesOutToDestination"
  namespace           = "AWS/NATGateway"
  period              = 3600 # 1 hour
  statistic           = "Sum"
  threshold           = var.nat_bytes_threshold
  alarm_description   = "NAT Gateway outbound data > ${var.nat_bytes_threshold / 1073741824} GB in 1 hour"
  alarm_actions       = [aws_sns_topic.cost_alerts.arn]

  dimensions = {
    NatGatewayId = var.nat_gateway_id
  }

  tags = {
    Name = "kk-swarm-nat-data-alarm"
  }
}

# -----------------------------------------------------------------------------
# Task Count Alarm (agents posting too many EM tasks)
# -----------------------------------------------------------------------------
# Custom metric pushed by sync-state.sh
resource "aws_cloudwatch_metric_alarm" "daily_task_spend" {
  alarm_name          = "kk-swarm-daily-task-spend"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "DailyTaskSpendUSD"
  namespace           = "KarmaCadabra/Swarm"
  period              = 86400 # 24 hours
  statistic           = "Sum"
  threshold           = var.daily_spend_limit
  alarm_description   = "Swarm daily EM task spend > $${var.daily_spend_limit}"
  alarm_actions       = [aws_sns_topic.cost_alerts.arn]

  tags = {
    Name = "kk-swarm-spend-alarm"
  }
}

# -----------------------------------------------------------------------------
# Running Task Count (detect orphaned tasks)
# -----------------------------------------------------------------------------
resource "aws_cloudwatch_metric_alarm" "running_tasks_high" {
  alarm_name          = "kk-swarm-running-tasks-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "RunningTaskCount"
  namespace           = "ECS/ContainerInsights"
  period              = 300
  statistic           = "Maximum"
  threshold           = var.max_expected_agents * 1.5 # Allow some headroom
  alarm_description   = "Running tasks > ${var.max_expected_agents * 1.5} (possible orphaned tasks)"
  alarm_actions       = [aws_sns_topic.cost_alerts.arn]

  dimensions = {
    ClusterName = var.cluster_name
  }

  tags = {
    Name = "kk-swarm-task-count-alarm"
  }
}
