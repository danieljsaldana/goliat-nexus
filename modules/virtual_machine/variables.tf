variable "name" {
  type = string
}

variable "location" {
  type = string
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

variable "admin_username" {
  type    = string
  default = "nexusops"
}

variable "bootstrap_script" {
  type    = string
  default = "#!/bin/bash\nset -euo pipefail\n"
}

variable "tags" {
  type    = map(string)
  default = {}
}
