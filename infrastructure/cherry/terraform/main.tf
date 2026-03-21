# Karma Kadabra V2 — Task 6.1: Cherry Servers Terraform
#
# Deploys 2 VPS instances for the KK agent swarm:
#   - kk-swarm-01: System agents + first 25 community agents
#   - kk-swarm-02: Remaining community agents + overflow
#
# Usage:
#   cd infrastructure/cherry/terraform
#   terraform init
#   terraform plan -var="cherry_api_key=YOUR_KEY" -var="ssh_public_key=~/.ssh/id_ed25519.pub"
#   terraform apply -var="cherry_api_key=YOUR_KEY" -var="ssh_public_key=~/.ssh/id_ed25519.pub"

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    cherryservers = {
      source  = "cherryservers/cherryservers"
      version = "~> 1.0"
    }
  }
}

# ---------------------------------------------------------------------------
# Variables
# ---------------------------------------------------------------------------

variable "cherry_api_key" {
  description = "Cherry Servers API key"
  type        = string
  sensitive   = true
}

variable "project_id" {
  description = "Cherry Servers project ID (numeric)"
  type        = number
}

variable "ssh_public_key" {
  description = "Path to SSH public key file"
  type        = string
  default     = "~/.ssh/id_ed25519.pub"
}

variable "region" {
  description = "Cherry Servers region"
  type        = string
  default     = "eu_nord_1"
}

variable "plan" {
  description = "Server plan (cloud_vds_2 = 4GB RAM, 2 vCPU)"
  type        = string
  default     = "cloud_vds_2"
}

variable "server_count" {
  description = "Number of VPS instances"
  type        = number
  default     = 2
}

variable "agents_per_server" {
  description = "Agents per server"
  type        = number
  default     = 25
}

# ---------------------------------------------------------------------------
# Provider
# ---------------------------------------------------------------------------

provider "cherryservers" {
  api_token = var.cherry_api_key
}

# ---------------------------------------------------------------------------
# SSH Key
# ---------------------------------------------------------------------------

resource "cherryservers_ssh_key" "kk_deploy" {
  name       = "kk-swarm-deploy"
  public_key = file(pathexpand(var.ssh_public_key))
}

# ---------------------------------------------------------------------------
# Servers
# ---------------------------------------------------------------------------

resource "cherryservers_server" "kk_swarm" {
  count = var.server_count

  project_id = var.project_id
  plan       = var.plan
  region     = var.region
  hostname   = "kk-swarm-${format("%02d", count.index + 1)}"
  image      = "ubuntu_22_04"

  ssh_key_ids = [cherryservers_ssh_key.kk_deploy.id]

  tags = {
    project = "karma-kadabra-v2"
    role    = count.index == 0 ? "primary" : "secondary"
    agents  = tostring(var.agents_per_server)
  }
}

# ---------------------------------------------------------------------------
# Outputs
# ---------------------------------------------------------------------------

output "server_ips" {
  description = "Public IPs of KK swarm servers"
  value = {
    for i, server in cherryservers_server.kk_swarm :
    server.hostname => server.ip_addresses[0].address
  }
}

output "ssh_commands" {
  description = "SSH commands for each server"
  value = [
    for server in cherryservers_server.kk_swarm :
    "ssh root@${server.ip_addresses[0].address}"
  ]
}

output "ansible_inventory" {
  description = "Ansible inventory content"
  value = join("\n", [
    "[kk_swarm]",
    join("\n", [
      for i, server in cherryservers_server.kk_swarm :
      "${server.hostname} ansible_host=${server.ip_addresses[0].address} server_index=${i} agents_start=${i * var.agents_per_server} agents_end=${(i + 1) * var.agents_per_server - 1}"
    ]),
  ])
}
