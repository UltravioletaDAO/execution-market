# =============================================================================
# KarmaCadabra Swarm — Variables
# =============================================================================
# The ONLY required input is the Anthropic API key.
# Everything else has sensible defaults for Phase 0 (5 agents, ~$104/mo).
# =============================================================================

# -----------------------------------------------------------------------------
# REQUIRED — The only thing the deployer must provide
# -----------------------------------------------------------------------------
variable "anthropic_api_key" {
  description = "Anthropic API key for Claude models. This is the ONLY required input."
  type        = string
  sensitive   = true

  validation {
    condition     = can(regex("^sk-ant-", var.anthropic_api_key))
    error_message = "Anthropic API key must start with 'sk-ant-'."
  }
}

# -----------------------------------------------------------------------------
# Agent Configuration
# -----------------------------------------------------------------------------
variable "agent_count" {
  description = "Number of OpenClaw agents to deploy. Start with 5 for Phase 0."
  type        = number
  default     = 5

  validation {
    condition     = var.agent_count >= 1 && var.agent_count <= 200
    error_message = "Agent count must be between 1 and 200."
  }
}

variable "agent_model" {
  description = "Default LLM model for agents. Haiku is recommended for cost efficiency."
  type        = string
  default     = "anthropic/claude-haiku-4-5"

  validation {
    condition     = contains(["anthropic/claude-haiku-4-5", "anthropic/claude-sonnet-4-5", "anthropic/claude-sonnet-4-20250514"], var.agent_model)
    error_message = "Model must be a valid Anthropic model identifier."
  }
}

variable "agent_cpu" {
  description = "CPU units per agent task (256 = 0.25 vCPU, 512 = 0.5 vCPU)"
  type        = number
  default     = 256

  validation {
    condition     = contains([256, 512, 1024, 2048], var.agent_cpu)
    error_message = "CPU must be 256, 512, 1024, or 2048."
  }
}

variable "agent_memory" {
  description = "Memory (MiB) per agent task. 512 MiB is sufficient for OpenClaw."
  type        = number
  default     = 512

  validation {
    condition     = contains([512, 1024, 2048, 4096], var.agent_memory)
    error_message = "Memory must be 512, 1024, 2048, or 4096 MiB."
  }
}

# -----------------------------------------------------------------------------
# Personality Templates
# -----------------------------------------------------------------------------
variable "soul_templates" {
  description = "List of SOUL.md personality templates. Agents cycle through these."
  type = list(object({
    name            = string
    traits          = list(string)
    communication   = string
    interests       = list(string)
    risk_tolerance  = string
    language        = string
  }))
  default = [
    {
      name           = "The Explorer"
      traits         = ["curious", "adventurous", "open-minded"]
      communication  = "enthusiastic and question-asking"
      interests      = ["new technologies", "travel", "cultural exchange"]
      risk_tolerance = "moderate"
      language       = "en"
    },
    {
      name           = "The Builder"
      traits         = ["methodical", "persistent", "detail-oriented"]
      communication  = "clear and structured"
      interests      = ["software development", "systems design", "automation"]
      risk_tolerance = "conservative"
      language       = "en"
    },
    {
      name           = "The Connector"
      traits         = ["empathetic", "social", "collaborative"]
      communication  = "warm and inclusive"
      interests      = ["community building", "mentorship", "networking"]
      risk_tolerance = "moderate"
      language       = "es"
    },
    {
      name           = "The Analyst"
      traits         = ["analytical", "skeptical", "data-driven"]
      communication  = "precise and evidence-based"
      interests      = ["data science", "market analysis", "cryptoeconomics"]
      risk_tolerance = "conservative"
      language       = "en"
    },
    {
      name           = "The Creator"
      traits         = ["creative", "expressive", "visionary"]
      communication  = "colorful and storytelling"
      interests      = ["content creation", "design", "art and music"]
      risk_tolerance = "aggressive"
      language       = "es"
    },
    {
      name           = "The Strategist"
      traits         = ["strategic", "patient", "calculating"]
      communication  = "concise and action-oriented"
      interests      = ["game theory", "economics", "competitive strategy"]
      risk_tolerance = "moderate"
      language       = "en"
    },
    {
      name           = "The Educator"
      traits         = ["patient", "knowledgeable", "articulate"]
      communication  = "explanatory and supportive"
      interests      = ["teaching", "documentation", "knowledge sharing"]
      risk_tolerance = "conservative"
      language       = "es"
    },
    {
      name           = "The Maverick"
      traits         = ["bold", "unconventional", "risk-taking"]
      communication  = "direct and provocative"
      interests      = ["DeFi", "speculation", "cutting-edge experiments"]
      risk_tolerance = "aggressive"
      language       = "en"
    }
  ]
}

# -----------------------------------------------------------------------------
# AWS Configuration
# -----------------------------------------------------------------------------
variable "aws_region" {
  description = "AWS region for deployment"
  type        = string
  default     = "us-east-2"
}

variable "environment" {
  description = "Deployment environment"
  type        = string
  default     = "production"

  validation {
    condition     = contains(["development", "staging", "production"], var.environment)
    error_message = "Environment must be development, staging, or production."
  }
}

# -----------------------------------------------------------------------------
# Cost Optimization
# -----------------------------------------------------------------------------
variable "use_spot" {
  description = "Use Fargate Spot instances (70% cheaper, may be interrupted)"
  type        = bool
  default     = true
}

variable "enable_container_insights" {
  description = "Enable CloudWatch Container Insights (adds ~$3/mo per cluster)"
  type        = bool
  default     = false
}

variable "log_retention_days" {
  description = "CloudWatch log retention in days"
  type        = number
  default     = 14
}

# -----------------------------------------------------------------------------
# Cost Alerting
# -----------------------------------------------------------------------------
variable "alert_email" {
  description = "Email address for cost/budget alerts. Leave empty to skip."
  type        = string
  default     = ""
}

variable "daily_spend_limit" {
  description = "Maximum daily EM task spend (USD) before alerting."
  type        = number
  default     = 25
}
