variable "name" { type = string }
variable "subscription_id" { type = string }
variable "amount" { type = number }
variable "start_date" { type = string }
variable "alert_emails" { type = list(string) }
variable "resource_group_names" { type = list(string) }
