variable "prefix" { type = string }
variable "resource_group_name" { type = string }
variable "location" { type = string }
variable "tags" { type = map(string) }
variable "network" { type = object({ hub_cidr = string, firewall_subnet_cidr = string, management_subnet_cidr = string, endpoints_subnet_cidr = string, gateway_subnet_cidr = string, edge_apps_subnet_cidr = string }) }
variable "environments" { type = map(object({ network = object({ vnet_cidr = string, apps_subnet_cidr = string, data_subnet_cidr = string, functions_subnet_cidr = string }), additional_https_fqdns = list(string), enable_event_processing = optional(bool, false) })) }
variable "management_https_fqdns" { type = list(string) }
variable "workspace_id" { type = string }
variable "shared_service_fqdns" { type = list(string) }
variable "service_fqdns" { type = map(list(string)) }
variable "state_fqdn" { type = string }
variable "edge_public_hostnames" {
  type    = list(string)
  default = []
}
