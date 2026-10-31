variable "prefix" { type = string }
variable "location" { type = string }
variable "platform" {
  description = "Contrato interno generado por la capa platform; nunca contiene claves."
  type        = any
}
variable "features" { type = map(bool) }
variable "tags" { type = map(string) }

variable "sample" {
  type = object({ version = string, frontend_min_replicas = number, frontend_max_replicas = number, api_min_replicas = number, api_max_replicas = number, frontend_port = number, api_port = number, cpu = number, memory = string, http_concurrency = number })
}

variable "sample_images" {
  type    = map(string)
  default = {}
  validation {
    condition = !anytrue([var.features.enable_api_platform, var.features.enable_api_tenant, var.features.enable_api_activities]) || (
      toset(keys(var.sample_images)) == toset(["api", "frontend"]) &&
      alltrue([for key, image in var.sample_images : can(regex("^${replace(var.platform.registry_login_server, ".", "\\.")}/example/${key}@sha256:[0-9a-f]{64}$", image))])
    )
    error_message = "Publica frontend y API y proporciona ambas imágenes de este ACR con digest sha256."
  }
}

variable "environment_id" { type = string }
variable "environment_domain" { type = string }
