variable "name" { type = string }
variable "resource_group_name" { type = string }
variable "location" { type = string }
variable "replication_type" { type = string }
variable "public_access" { type = bool }
variable "allowed_ip_ranges" { type = list(string) }
variable "operator_object_id" { type = string }
variable "tags" { type = map(string) }
