FROM node:24.22.2-bookworm-slim
# Bootstrap APT's trusted roots from the official Node image's embedded CA store.
RUN node -e "const fs=require('fs');fs.mkdirSync('/etc/ssl/certs',{recursive:true});fs.writeFileSync('/etc/ssl/certs/ca-certificates.crt',require('tls').rootCertificates.join(String.fromCharCode(10)))" && sed -i 's|http://|https://|g' /etc/apt/sources.list.d/debian.sources && apt-get update -o APT::Update::Error-Mode=any && apt-get install -y --no-install-recommends openssl ca-certificates && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY package*.json ./
RUN npm ci --omit=dev && npm cache clean --force
COPY server.mjs ./
COPY LICENSE NOTICE ./
USER node
EXPOSE 8080
CMD ["node", "server.mjs"]
