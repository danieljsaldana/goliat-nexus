FROM nginx:stable-alpine@sha256:0e52bd054126cdc040b1276c0af347aeb02a41b9cfe305d6094767ac30e97949
ENV PORT=8080 API_PLATFORM_ORIGIN=http://127.0.0.1:9 API_TENANT_ORIGIN=http://127.0.0.1:9 API_ACTIVITIES_ORIGIN=http://127.0.0.1:9 CORS_ORIGINS=localhost
COPY nginx.conf /etc/nginx/nginx.conf
COPY proxy-params.conf /etc/nginx/proxy-params.conf
COPY default.conf.template /etc/nginx/templates/default.conf.template
COPY --chmod=755 15-resolver.envsh /docker-entrypoint.d/15-resolver.envsh
COPY index.html styles.css app.js /usr/share/nginx/html/
COPY LICENSE NOTICE /usr/share/nginx/html/
RUN chown -R nginx:nginx /etc/nginx/conf.d /etc/nginx/templates /usr/share/nginx/html
USER nginx
EXPOSE 8080
