# Execution Market Infrastructure - Outputs

output "vpc_id" {
  description = "VPC ID"
  value       = aws_vpc.main.id
}

output "public_subnets" {
  description = "Public subnet IDs"
  value       = aws_subnet.public[*].id
}

output "private_subnets" {
  description = "Private subnet IDs"
  value       = aws_subnet.private[*].id
}

output "ecs_cluster_name" {
  description = "ECS cluster name"
  value       = aws_ecs_cluster.main.name
}

output "ecs_cluster_arn" {
  description = "ECS cluster ARN"
  value       = aws_ecs_cluster.main.arn
}

output "ecr_mcp_server_url" {
  description = "ECR repository URL for MCP server"
  value       = aws_ecr_repository.mcp_server.repository_url
}

output "ecr_dashboard_url" {
  description = "ECR repository URL for Dashboard"
  value       = aws_ecr_repository.dashboard.repository_url
}

output "alb_dns_name" {
  description = "ALB DNS name"
  value       = aws_lb.main.dns_name
}

output "alb_zone_id" {
  description = "ALB zone ID for Route53"
  value       = aws_lb.main.zone_id
}

output "mcp_server_service_name" {
  description = "MCP server ECS service name"
  value       = aws_ecs_service.mcp_server.name
}

output "dashboard_service_name" {
  description = "Dashboard ECS service name"
  value       = aws_ecs_service.dashboard.name
}
