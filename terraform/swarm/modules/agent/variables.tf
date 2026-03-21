# =============================================================================
# Agent Module — Variables
# =============================================================================

variable "agent_name" {
  description = "Agent resource name (e.g., agent-000)"
  type        = string
}

variable "agent_index" {
  description = "Agent index (0-based)"
  type        = number
}

# Infrastructure references
variable "ecs_cluster_id" {
  type = string
}

variable "ecs_execution_role_arn" {
  type = string
}

variable "ecs_task_role_arn" {
  type = string
}

variable "subnet_ids" {
  type = list(string)
}

variable "security_group_ids" {
  type = list(string)
}

variable "ecr_repository_url" {
  type = string
}

variable "log_group_name" {
  type = string
}

variable "s3_bucket_name" {
  type = string
}

variable "s3_bucket_arn" {
  type = string
}

variable "anthropic_api_key_arn" {
  type = string
}

# Configuration
variable "agent_model" {
  type    = string
  default = "anthropic/claude-haiku-4-5"
}

variable "use_spot" {
  type    = bool
  default = true
}

variable "cpu" {
  type    = number
  default = 256
}

variable "memory" {
  type    = number
  default = 512
}

variable "environment" {
  type    = string
  default = "production"
}

variable "aws_region" {
  type    = string
  default = "us-east-2"
}

# Personality
variable "soul_template" {
  description = "Personality template for this agent"
  type = object({
    name            = string
    traits          = list(string)
    communication   = string
    interests       = list(string)
    risk_tolerance  = string
    language        = string
  })
}

variable "personality_seed" {
  description = "Seed for personality variation"
  type        = number
  default     = 0
}
