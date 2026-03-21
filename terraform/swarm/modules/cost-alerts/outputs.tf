# =============================================================================
# Cost Alerts Module — Outputs
# =============================================================================

output "sns_topic_arn" {
  description = "SNS topic ARN for cost alerts"
  value       = aws_sns_topic.cost_alerts.arn
}
