variable "name" {
  description = "Nombre del tópico de Event Grid"
  type        = string
}

variable "location" {
  description = "Ubicación de Azure"
  type        = string
}

variable "resource_group_name" {
  description = "Nombre del grupo de recursos"
  type        = string
}

variable "tags" {
  description = "Etiquetas"
  type        = map(string)
  default     = {}
}

variable "backend_principal_id" {
  description = "Principal ID de la identidad del backend para enviar eventos"
  type        = string
}

variable "eventgrid_identity_id" {
  description = "ID de la identidad gestionada para Event Grid"
  type        = string
}

variable "public_network_access_enabled" {
  description = "Indica si se permite el acceso desde redes públicas"
  type        = bool
  default     = true
}

variable "local_auth_enabled" {
  description = "Indica si la autenticación local está habilitada"
  type        = bool
  default     = true
}

variable "inbound_ip_rule" {
  description = "Lista de reglas de filtrado de IP entrantes"
  type = list(object({
    ip_mask = string
    action  = optional(string, "Allow")
  }))
  default = []
}
