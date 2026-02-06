# Execution Market Infrastructure - Variables

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-2"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "production"
}

variable "domain_name" {
  description = "Domain name for the application"
  type        = string
  default     = "execution.market"
}

# VPC
variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "availability_zones" {
  description = "Availability zones"
  type        = list(string)
  default     = ["us-east-2a", "us-east-2b"]
}

# ECS
variable "mcp_server_cpu" {
  description = "CPU units for MCP server task"
  type        = number
  default     = 256
}

variable "mcp_server_memory" {
  description = "Memory for MCP server task"
  type        = number
  default     = 512
}

variable "dashboard_cpu" {
  description = "CPU units for dashboard task"
  type        = number
  default     = 256
}

variable "dashboard_memory" {
  description = "Memory for dashboard task"
  type        = number
  default     = 512
}

variable "desired_count" {
  description = "Desired number of tasks"
  type        = number
  default     = 2
}

# Container images
variable "mcp_server_image" {
  description = "MCP server container image"
  type        = string
  default     = ""
}

variable "dashboard_image" {
  description = "Dashboard container image"
  type        = string
  default     = ""
}

# DNS
variable "domain" {
  description = "Root domain for the application"
  type        = string
  default     = "execution.market"
}

variable "api_subdomain" {
  description = "API subdomain"
  type        = string
  default     = "api"
}

variable "app_subdomain" {
  description = "App subdomain"
  type        = string
  default     = "app"
}

# Evidence pipeline (optional): API Gateway -> Lambda -> S3 -> CloudFront
variable "enable_evidence_pipeline" {
  description = "Enable managed evidence upload and delivery stack"
  type        = bool
  default     = false
}

variable "evidence_subdomain" {
  description = "Subdomain for evidence CDN when custom domain is configured"
  type        = string
  default     = "storage"
}

variable "evidence_acm_certificate_arn" {
  description = "ACM certificate ARN for CloudFront custom domain (must be in us-east-1). Leave empty to use default *.cloudfront.net domain."
  type        = string
  default     = ""
}

variable "evidence_bucket_name" {
  description = "Optional explicit S3 bucket name for evidence. Leave empty to auto-generate."
  type        = string
  default     = ""
}

variable "evidence_allowed_origins" {
  description = "Allowed browser origins for evidence upload CORS"
  type        = list(string)
  default     = ["https://execution.market", "https://www.execution.market"]
}

variable "evidence_retention_days" {
  description = "S3 evidence retention in days. Set 0 to disable automatic expiration."
  type        = number
  default     = 365
}

variable "evidence_presign_expiry_seconds" {
  description = "Expiration time in seconds for presigned upload/download URLs"
  type        = number
  default     = 900
}

variable "evidence_max_upload_mb" {
  description = "Maximum size in MB for presigned uploads (enforced in presigned POST mode)"
  type        = number
  default     = 25
}
