# =============================================================================
# Agent Module — Outputs
# =============================================================================

output "service_name" {
  description = "ECS service name for this agent"
  value       = aws_ecs_service.agent.name
}

output "service_arn" {
  description = "ECS service ARN"
  value       = aws_ecs_service.agent.id
}

output "task_definition_arn" {
  description = "Task definition ARN"
  value       = aws_ecs_task_definition.agent.arn
}

output "personality_name" {
  description = "Agent personality archetype"
  value       = var.soul_template.name
}

output "display_name" {
  description = "Agent display name"
  value       = local.display_name
}
