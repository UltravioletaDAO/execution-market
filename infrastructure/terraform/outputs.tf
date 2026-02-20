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

output "evidence_enabled" {
  description = "Whether the managed evidence pipeline is enabled"
  value       = var.enable_evidence_pipeline
}

output "evidence_bucket_name" {
  description = "S3 bucket name for evidence uploads"
  value       = var.enable_evidence_pipeline ? aws_s3_bucket.evidence[0].id : null
}

output "evidence_cloudfront_domain" {
  description = "CloudFront domain for evidence delivery"
  value       = var.enable_evidence_pipeline ? aws_cloudfront_distribution.evidence[0].domain_name : null
}

output "evidence_public_base_url" {
  description = "Public base URL used to serve evidence"
  value       = var.enable_evidence_pipeline ? (local.evidence_custom_domain_ready ? "https://${local.evidence_custom_domain_name}" : "https://${aws_cloudfront_distribution.evidence[0].domain_name}") : null
}

output "evidence_presign_api_url" {
  description = "HTTP API invoke URL for presigned upload/download URL generation"
  value       = var.enable_evidence_pipeline ? aws_apigatewayv2_stage.evidence_default[0].invoke_url : null
}

output "nonce_store_table_arn" {
  description = "DynamoDB table ARN for ERC-8128 nonce store"
  value       = aws_dynamodb_table.nonce_store.arn
}

output "nonce_store_table_name" {
  description = "DynamoDB table name for ERC-8128 nonce store"
  value       = aws_dynamodb_table.nonce_store.name
}
