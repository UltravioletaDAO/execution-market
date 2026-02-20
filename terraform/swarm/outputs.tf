# =============================================================================
# KarmaCadabra Swarm — Outputs
# =============================================================================

output "cluster_name" {
  description = "ECS cluster name"
  value       = aws_ecs_cluster.swarm.name
}

output "cluster_arn" {
  description = "ECS cluster ARN"
  value       = aws_ecs_cluster.swarm.arn
}

output "ecr_repository_url" {
  description = "ECR repository URL for the OpenClaw agent image"
  value       = aws_ecr_repository.openclaw_agent.repository_url
}

output "s3_bucket_name" {
  description = "S3 bucket for agent state and memory"
  value       = aws_s3_bucket.agent_state.id
}

output "agent_count" {
  description = "Number of deployed agents"
  value       = var.agent_count
}

output "agent_services" {
  description = "Map of agent names to their ECS service names"
  value       = { for k, v in module.agent : k => v.service_name }
}

output "agent_personalities" {
  description = "Map of agent names to their personality archetypes"
  value       = { for k, v in module.agent : k => v.personality_name }
}

output "vpc_id" {
  description = "VPC ID"
  value       = aws_vpc.swarm.id
}

output "estimated_monthly_cost" {
  description = "Estimated monthly cost breakdown"
  value = {
    ecs_fargate = var.use_spot ? (
      format("$%.2f", var.agent_count * 0.25 * var.agent_cpu / 1024 * 730 * 0.3 + var.agent_count * 0.25 * var.agent_memory / 1024 * 730 * 0.03)
    ) : (
      format("$%.2f", var.agent_count * var.agent_cpu / 1024 * 730 * 0.04048 + var.agent_count * var.agent_memory / 1024 * 730 * 0.004445)
    )
    nat_gateway      = "$32.40"
    s3               = "~$1.00"
    cloudwatch_logs  = "~$2.00"
    secrets_manager  = "$0.40"
    note             = "LLM API costs are separate (Haiku ~$0.003/agent/day = ~$0.45/mo for 5 agents)"
  }
}

output "deployment_summary" {
  description = "Deployment summary"
  value = <<-EOT
    ╔══════════════════════════════════════════════════════════════╗
    ║              KarmaCadabra Swarm — Deployed! 🪄              ║
    ╠══════════════════════════════════════════════════════════════╣
    ║  Agents: ${var.agent_count}                                          ║
    ║  Model:  ${var.agent_model}                   ║
    ║  Region: ${var.aws_region}                                      ║
    ║  Spot:   ${var.use_spot ? "enabled (70% savings)" : "disabled"}                            ║
    ║  Cluster: ${aws_ecs_cluster.swarm.name}                       ║
    ╚══════════════════════════════════════════════════════════════╝
  EOT
}
