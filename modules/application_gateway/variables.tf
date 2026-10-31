variable "name" { type = string }
variable "location" { type = string }
variable "resource_group_name" { type = string }
variable "subnet_id" { type = string }
variable "public_ip_id" { type = string }
variable "identity_id" { type = string }
variable "certificate_secret_id" { type = string }
variable "hostnames" { type = list(string) }
variable "minimum_instances" { type = number }
variable "maximum_instances" { type = number }
variable "workspace_id" { type = string }
variable "backends" { type = map(object({ hostname = string, probe_path = string, paths = list(string), api_environment = string })) }
variable "tags" { type = map(string) }

variable "environment_hosts" { type = map(string) }
