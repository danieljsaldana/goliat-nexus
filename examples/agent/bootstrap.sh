#!/bin/bash
set -euo pipefail
exec > /var/log/goliat-nexus-bootstrap.log 2>&1
export DEBIAN_FRONTEND=noninteractive
sed -i 's|http://|https://|g; s|azure.archive.ubuntu.com|archive.ubuntu.com|g' /etc/apt/sources.list.d/ubuntu.sources
apt-get update
apt-get install -y ca-certificates curl gnupg python3 unzip make
install -d -m 0755 /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc
printf '%s\n' 'deb [arch=amd64 signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu noble stable' > /etc/apt/sources.list.d/docker.list
curl -fsSL https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor --yes -o /etc/apt/keyrings/microsoft.gpg
printf '%s\n' 'deb [arch=amd64 signed-by=/etc/apt/keyrings/microsoft.gpg] https://packages.microsoft.com/repos/azure-cli/ noble main' > /etc/apt/sources.list.d/azure-cli.list
apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin azure-cli
systemctl enable --now docker
curl -fsSL https://nodejs.org/dist/v24.22.2/node-v24.22.2-linux-x64.tar.xz -o /tmp/node.tar.xz
printf '%s  /tmp/node.tar.xz\n' '48cc0e21e048790e54c0cf5749c2725005313d652651c40b7a21feb9697aaf75' | sha256sum -c -
tar -xJf /tmp/node.tar.xz --strip-components=1 -C /usr/local
npm install -g @azure/static-web-apps-cli@2.1.0
az login --identity --allow-no-subscriptions -o none
mkdir -p /var/lib/goliat-nexus
node --version
az version --query '"azure-cli"' -o tsv
docker buildx version
curl -fsSL https://releases.hashicorp.com/terraform/1.17.1/terraform_1.17.1_linux_amd64.zip -o /tmp/terraform.zip
curl -fsSL https://releases.hashicorp.com/terraform/1.17.1/terraform_1.17.1_SHA256SUMS -o /tmp/terraform.SHA256SUMS
(cd /tmp && cp terraform.zip terraform_1.17.1_linux_amd64.zip && grep " terraform_1.17.1_linux_amd64.zip$" terraform.SHA256SUMS | sha256sum -c -)
unzip -o /tmp/terraform.zip terraform -d /usr/local/bin
touch /var/lib/goliat-nexus/bootstrap-ready
