# Ejecutor privado con VNet existente, identidad y Trusted Launch.
resource "azurerm_network_interface" "this" {
  name                = "${var.name}-nic"
  location            = var.location
  resource_group_name = var.resource_group_name
  ip_configuration {
    name                          = "private"
    subnet_id                     = var.subnet_id
    private_ip_address_allocation = "Dynamic"
  }
  tags = var.tags
}
resource "azurerm_linux_virtual_machine" "this" {
  name                            = var.name
  location                        = var.location
  resource_group_name             = var.resource_group_name
  size                            = var.vm_size
  admin_username                  = var.admin_username
  disable_password_authentication = true
  network_interface_ids           = [azurerm_network_interface.this.id]
  secure_boot_enabled             = true
  vtpm_enabled                    = true
  identity { type = "SystemAssigned" }
  admin_ssh_key {
    username   = var.admin_username
    public_key = var.ssh_public_key
  }
  os_disk {
    caching              = "ReadWrite"
    storage_account_type = "StandardSSD_LRS"
    disk_size_gb         = 64
  }
  source_image_reference {
    publisher = "Canonical"
    offer     = "ubuntu-24_04-lts"
    sku       = "server"
    version   = "latest"
  }
  custom_data = base64encode("#cloud-config\nwrite_files:\n  - path: /usr/local/sbin/nexus-bootstrap\n    permissions: '0700'\n    encoding: b64\n    content: ${base64encode(var.bootstrap_script)}\nruncmd:\n  - /usr/local/sbin/nexus-bootstrap\n")
  tags        = var.tags
}
