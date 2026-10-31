variable "name" {
  description = "Nombre de la cuenta de Cosmos DB"
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
  description = "Etiquetas para los recursos"
  type        = map(string)
  default     = {}
}

variable "kind" {
  description = "Tipo de cuenta de Cosmos DB (GlobalDocumentDB, MongoDB, etc.)"
  type        = string
  default     = "MongoDB"
}

variable "offer_type" {
  description = "Tipo de oferta (Standard)"
  type        = string
  default     = "Standard"
}

variable "capabilities" {
  description = "Lista de capacidades a habilitar (ej: EnableMongo, EnableServerless)"
  type        = list(string)
  default     = []
}

variable "consistency_policy" {
  description = "Política de consistencia"
  type = object({
    consistency_level       = string
    max_interval_in_seconds = optional(number)
    max_staleness_prefix    = optional(number)
  })
  default = {
    consistency_level = "Session"
  }
}

variable "geo_locations" {
  description = "Ubicaciones geográficas y prioridades de failover"
  type = list(object({
    location          = string
    failover_priority = number
    zone_redundant    = optional(bool, false)
  }))
  default = null # Si es null, se usa la var.location como primaria
}

variable "public_network_access_enabled" {
  description = "Habilitar acceso público"
  type        = bool
  default     = true
}

variable "free_tier_enabled" {
  description = "Habilitar Free Tier"
  type        = bool
  default     = false
}

variable "backup" {
  description = "Configuración de copias de seguridad"
  type = object({
    type                = optional(string, "Periodic")
    tier                = optional(string)
    interval_in_minutes = optional(number)
    retention_in_hours  = optional(number)
    storage_redundancy  = optional(string)
  })
  default = {
    type                = "Periodic"
    interval_in_minutes = 240
    retention_in_hours  = 8
    storage_redundancy  = "Geo"
  }
}

variable "minimal_tls_version" {
  description = "Versión mínima de TLS"
  type        = string
  default     = "Tls12"
}

variable "enable_cosmos" {
  description = "Si es true, se despliega Cosmos DB."
  type        = bool
  default     = false
}

variable "database_names" {
  description = "Lista de bases de datos de MongoDB"
  type        = list(string)
}

variable "is_serverless" {
  description = "Si es true, se habilita el modo Serverless. Si es false, se usa Provisión de rendimiento (throughput)."
  type        = bool
  default     = true
}

variable "throughput" {
  description = "Rendimiento manual (RU/s). Solo si is_serverless es false y max_throughput es null."
  type        = number
  default     = null
}

variable "max_throughput" {
  description = "Rendimiento máximo para autoescala (RU/s). Solo si is_serverless es false."
  type        = number
  default     = null
}

variable "mongo_server_version" {
  description = "Compatibilidad de servidor MongoDB; el producto 1.0 usa 7.0."
  type        = string
  default     = "7.0"
}

variable "ip_range_filter" {
  description = "Lista de IPs o rangos CIDR permitidos (separados por coma en Azure, pero pasados como lista aquí)"
  type        = list(string)
  default     = []
}
