terraform {
  required_version = ">= 1.0"

  required_providers {
    linode = {
      source  = "linode/linode"
      version = "~> 2.0"
    }
  }
}

provider "linode" {
  token = var.linode_api_token
}

# Variables
variable "linode_api_token" {
  description = "Linode API Token"
  type        = string
  sensitive   = true
}

variable "root_password" {
  description = "Root password for Linode instances"
  type        = string
  sensitive   = true
}

variable "ssh_public_key" {
  description = "SSH public key for access"
  type        = string
}

variable "region" {
  description = "Linode region"
  type        = string
  default     = "us-east"
}

# Test Environment Instance
resource "linode_instance" "fazztv_test" {
  label            = "fazztv-test"
  image            = "linode/ubuntu22.04"
  region           = var.region
  type             = "g6-standard-1" # 2 GB RAM, 1 CPU
  authorized_keys  = [var.ssh_public_key]
  root_pass        = var.root_password

  # Backups for test environment (optional)
  backups_enabled = false

  # Private IP for internal communication
  private_ip = true

  tags = ["fazztv", "test", "media-broadcasting"]
}

# Production Environment Instance
resource "linode_instance" "fazztv_prod" {
  label            = "fazztv-prod"
  image            = "linode/ubuntu22.04"
  region           = var.region
  type             = "g6-dedicated-4" # 8 GB RAM, 4 CPU
  authorized_keys  = [var.ssh_public_key]
  root_pass        = var.root_password

  # Enable backups for production
  backups_enabled = true

  # Private IP for internal communication
  private_ip = true

  tags = ["fazztv", "production", "media-broadcasting"]
}

# Block Storage for Test Environment
resource "linode_volume" "fazztv_test_storage" {
  label  = "fazztv-test-storage"
  region = var.region
  size   = 100 # 100 GB

  linode_id = linode_instance.fazztv_test.id

  tags = ["fazztv", "test", "storage"]
}

# Block Storage for Production Environment
resource "linode_volume" "fazztv_prod_storage" {
  label  = "fazztv-prod-storage"
  region = var.region
  size   = 500 # 500 GB

  linode_id = linode_instance.fazztv_prod.id

  tags = ["fazztv", "production", "storage"]
}

# Firewall for Test Environment
resource "linode_firewall" "fazztv_test_firewall" {
  label = "fazztv-test-firewall"

  inbound {
    label    = "allow-ssh"
    action   = "ACCEPT"
    protocol = "TCP"
    ports    = "22"
    ipv4     = ["0.0.0.0/0"]
  }

  inbound {
    label    = "allow-http"
    action   = "ACCEPT"
    protocol = "TCP"
    ports    = "80"
    ipv4     = ["0.0.0.0/0"]
  }

  inbound_policy  = "DROP"
  outbound_policy = "ACCEPT"

  linodes = [linode_instance.fazztv_test.id]

  tags = ["fazztv", "test", "firewall"]
}

# Firewall for Production Environment
resource "linode_firewall" "fazztv_prod_firewall" {
  label = "fazztv-prod-firewall"

  inbound {
    label    = "allow-ssh"
    action   = "ACCEPT"
    protocol = "TCP"
    ports    = "22"
    ipv4     = ["0.0.0.0/0"] # Restrict to specific IPs in production
  }

  inbound {
    label    = "allow-http"
    action   = "ACCEPT"
    protocol = "TCP"
    ports    = "80"
    ipv4     = ["0.0.0.0/0"]
  }

  inbound {
    label    = "allow-https"
    action   = "ACCEPT"
    protocol = "TCP"
    ports    = "443"
    ipv4     = ["0.0.0.0/0"]
  }

  inbound {
    label    = "allow-rtmp"
    action   = "ACCEPT"
    protocol = "TCP"
    ports    = "1935"
    ipv4     = ["0.0.0.0/0"]
  }

  inbound_policy  = "DROP"
  outbound_policy = "ACCEPT"

  linodes = [linode_instance.fazztv_prod.id]

  tags = ["fazztv", "production", "firewall"]
}

# NodeBalancer for Production (optional - for high availability)
resource "linode_nodebalancer" "fazztv_prod_lb" {
  label  = "fazztv-prod-lb"
  region = var.region

  tags = ["fazztv", "production", "load-balancer"]
}

resource "linode_nodebalancer_config" "fazztv_prod_http" {
  nodebalancer_id = linode_nodebalancer.fazztv_prod_lb.id
  port            = 80
  protocol        = "http"
  algorithm       = "roundrobin"
  stickiness      = "http_cookie"

  check           = "http"
  check_path      = "/health"
  check_interval  = 30
  check_timeout   = 10
  check_attempts  = 3
  check_passive   = true
}

resource "linode_nodebalancer_node" "fazztv_prod_node" {
  nodebalancer_id = linode_nodebalancer.fazztv_prod_lb.id
  config_id       = linode_nodebalancer_config.fazztv_prod_http.id
  address         = "${linode_instance.fazztv_prod.private_ip_address}:80"
  label           = "fazztv-prod-primary"
  weight          = 100
}

# Outputs
output "test_instance_ip" {
  value       = linode_instance.fazztv_test.ip_address
  description = "Public IP of test instance"
}

output "test_instance_private_ip" {
  value       = linode_instance.fazztv_test.private_ip_address
  description = "Private IP of test instance"
}

output "prod_instance_ip" {
  value       = linode_instance.fazztv_prod.ip_address
  description = "Public IP of production instance"
}

output "prod_instance_private_ip" {
  value       = linode_instance.fazztv_prod.private_ip_address
  description = "Private IP of production instance"
}

output "prod_loadbalancer_ip" {
  value       = linode_nodebalancer.fazztv_prod_lb.ipv4
  description = "Public IP of production load balancer"
}

output "test_storage_device" {
  value       = linode_volume.fazztv_test_storage.filesystem_path
  description = "Device path for test block storage"
}

output "prod_storage_device" {
  value       = linode_volume.fazztv_prod_storage.filesystem_path
  description = "Device path for production block storage"
}