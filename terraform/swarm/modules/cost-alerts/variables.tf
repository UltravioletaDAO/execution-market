# =============================================================================
# Cost Alerts Module — Variables
# =============================================================================

variable "cluster_name" {
  description = "ECS cluster name"
  type        = string
}

variable "nat_gateway_id" {
  description = "NAT Gateway ID for data transfer monitoring"
  type        = string
}

variable "alert_email" {
  description = "Email address for cost alerts"
  type        = string
  default     = ""
}

variable "daily_spend_limit" {
  description = "Maximum daily EM task spend in USD before alerting"
  type        = number
  default     = 25
}

variable "max_expected_agents" {
  description = "Expected number of running agents (alerts if exceeded by 50%)"
  type        = number
  default     = 55
}

variable "nat_bytes_threshold" {
  description = "NAT Gateway bytes out threshold per hour (default: 5GB)"
  type        = number
  default     = 5368709120 # 5 GB
}
