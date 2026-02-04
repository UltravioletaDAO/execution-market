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
