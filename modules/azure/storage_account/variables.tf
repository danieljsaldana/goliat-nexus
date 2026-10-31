variable "name" {
  description = "Nombre de la cuenta de almacenamiento"
  type        = string
}

variable "resource_group_name" {
  description = "Nombre del grupo de recursos"
  type        = string
}

variable "location" {
  description = "Ubicación de Azure"
  type        = string
}

variable "tags" {
  description = "Etiquetas"
  type        = map(string)
  default     = {}
}

variable "containers" {
  description = "Lista de nombres de contenedores blob a crear"
  type        = list(string)
  default     = []
}

variable "queues" {
  description = "Lista de nombres de colas a crear"
  type        = list(string)
  default     = []
}

variable "tables" {
  description = "Lista de nombres de tablas a crear"
  type        = list(string)
  default     = []
}

variable "last_access_time_enabled" {
  description = "Habilitar el rastreo del último tiempo de acceso para blobs"
  type        = bool
  default     = false
}

variable "enable_lifecycle_policy" {
  description = "Habilitar una política de ciclo de vida básica"
  type        = bool
  default     = false
}

variable "lifecycle_days" {
  description = "Días desde el último acceso antes de mover a nivel Cool"
  type        = number
  default     = 30
}

variable "allow_nested_items_to_be_public" {
  description = "Permitir o denegar el acceso público anónimo a blobs y contenedores."
  type        = bool
  default     = false
}

variable "shared_access_key_enabled" {
  description = "Indica si se permite el acceso mediante claves compartidas (Shared Key). Si se desactiva, solo se permitirá el acceso mediante Entra ID (RBAC)."
  type        = bool
  default     = true
}

variable "network_rules" {
  description = "Configuración de las reglas de red (Firewall) para la cuenta de almacenamiento."
  type = object({
    default_action             = string
    bypass                     = list(string)
    ip_rules                   = list(string)
    virtual_network_subnet_ids = list(string)
  })
  default = null
}

variable "replication" {
  type    = string
  default = "LRS"
}
variable "soft_delete_days" {
  type    = number
  default = 14
}
