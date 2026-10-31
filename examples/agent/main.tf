terraform {
  required_version = ">= 1.9, < 2.0"
  required_providers { azurerm = { source = "hashicorp/azurerm", version = "= 5.12.0" } }
}
provider "azurerm" {
  subscription_id                 = var.subscription_id
  tenant_id                       = var.tenant_id
  client_id                       = var.client_id
  client_certificate_path         = var.client_certificate_path
  use_cli                         = var.client_id == null
  resource_provider_registrations = "none"
  features {}
}
variable "name" {
  type    = string
  default = "goliat-nexus-agent"
}

variable "subscription_id" {
  type = string
}

variable "tenant_id" {
  type = string
}

variable "client_id" {
  type    = string
  default = null
}

variable "client_certificate_path" {
  type    = string
  default = null
}

variable "location" {
  type    = string
  default = "westeurope"
}

variable "resource_group_name" {
  type = string
}

variable "subnet_id" {
  type = string
}

variable "ssh_public_key" {
  type = string
}

variable "vm_size" {
  type    = string
  default = "Standard_D2as_v5"
}

variable "github_repository" {
  type = string
}

variable "github_labels" {
  type    = list(string)
  default = ["goliat-nexus"]
}
module "virtual_machine" {
  source              = "../../modules/virtual_machine"
  name                = var.name
  location            = var.location
  resource_group_name = var.resource_group_name
  subnet_id           = var.subnet_id
  ssh_public_key      = var.ssh_public_key
  vm_size             = var.vm_size
  bootstrap_script    = file("${path.module}/bootstrap.sh")
  tags                = { Product = "Goliat - Nexus", Purpose = "GitHubActionsAgent", ManagedBy = "Terraform" }
}
output "runner" {
  value = {
    id                = module.virtual_machine.id
    name              = module.virtual_machine.name
    private_ip        = module.virtual_machine.private_ip
    principal_id      = module.virtual_machine.principal_id
    location          = var.location
    github_repository = var.github_repository
    github_labels     = var.github_labels
  }
}
