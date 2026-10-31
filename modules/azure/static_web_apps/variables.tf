variable "name" {
  description = "Nombre del Static Web App"
  type        = string
}

variable "resource_group_name" {
  description = "Nombre del Resource Group"
  type        = string
}

variable "location" {
  description = "Ubicación del recurso"
  type        = string
}

variable "sku_tier" {
  description = "Tier del SKU (Free, Standard)"
  type        = string
  default     = "Free"
}

variable "sku_size" {
  description = "Tamaño del SKU (Free, Standard)"
  type        = string
  default     = "Free"
}







variable "app_settings" {
  description = "Variables de entorno (App Settings)"
  type        = map(string)
  default     = {}
}

variable "tags" {
  description = "Etiquetas"
  type        = map(string)
  default     = {}
}
