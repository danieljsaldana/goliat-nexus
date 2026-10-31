output "id" { value = azurerm_linux_virtual_machine.this.id }
output "name" { value = azurerm_linux_virtual_machine.this.name }
output "private_ip" { value = azurerm_network_interface.this.private_ip_address }
output "principal_id" { value = azurerm_linux_virtual_machine.this.identity[0].principal_id }
output "security" { value = { public_ip = false, password_authentication = false, secure_boot = azurerm_linux_virtual_machine.this.secure_boot_enabled, vtpm = azurerm_linux_virtual_machine.this.vtpm_enabled } }
