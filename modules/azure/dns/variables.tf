variable "resource_group_name" {
  description = "Nombre del Resource Group donde se creará la zona DNS."
  type        = string
}

variable "domain_name" {
  description = "Nombre del dominio (ej: app.example.com)."
  type        = string
}

variable "cname_records" {
  description = "Mapa de subdominios a configurar (ej: admin). Key=subdominio, Value=record_value."
  type = map(object({
    record_value = string
  }))
  default = {}
}

variable "a_records" {
  description = "Mapa de registros A (ej: @). Key=nombre, Value=lista de IPs."
  type = map(object({
    records = list(string)
    ttl     = optional(number, 300)
  }))
  default = {}
}

variable "txt_records" {
  description = "Mapa de registros TXT. Key=nombre, Value=valor del registro."
  type = map(object({
    record_value = string
    ttl          = optional(number, 300)
  }))
  default = {}
}

variable "mx_records" {
  description = "Mapa de registros MX. Key=nombre, Value=lista de objetos con preferencia y valor."
  type = map(object({
    records = list(object({
      preference = number
      exchange   = string
    }))
    ttl = optional(number, 3600)
  }))
  default = {}
}

variable "ca_verification_records" {
  description = "Mapa de registros TXT de verificación para Container Apps. Key=subdominio, Value=verification_id."
  type        = map(string)
  default     = {}
}

variable "root_web_app_id" {
  description = "ID del Static Web App para el dominio raíz (@). Si se define, se crea un registro A Alias."
  type        = string
  default     = null
}

variable "tags" {
  description = "Etiquetas."
  type        = map(string)
  default     = {}
}

variable "create_zone" {
  description = "Indica si se debe crear la zona DNS o usar una existente."
  type        = bool
  default     = true
}

variable "swa_custom_domains" {
  description = "Mapa de subdominios a IDs de Static Web App para vincular dominios personalizados."
  type        = map(string)
  default     = {}
}

variable "enable_root_domain" {
  description = "Indica disparador para configurar el dominio raíz (@) con registro A y vinculación SWA."
  type        = bool
  default     = false
}

variable "container_app_environment_id" {
  description = "ID del entorno de Container Apps para los certificados gestionados."
  type        = string
  default     = null
}

variable "ca_custom_domains" {
  description = "Mapa de subdominios a IDs de Container App para vincular dominios personalizados. Key=subdominio (ej: api-platform), Value=container_app_id."
  type        = map(string)
  default     = {}
}

variable "ca_apps" {
  description = "Mapa de aplicaciones a sus IDs y dominios para la actualización final. Key=app_name (estático), Value=object."
  type = map(object({
    id      = string
    domains = list(string)
  }))
  default = {}
}

variable "location" {
  description = "Ubicación de los recursos."
  type        = string
  default     = "spaincentral"
}
