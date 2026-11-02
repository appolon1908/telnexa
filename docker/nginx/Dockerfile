FROM nginx/nginx-unprivileged:1.30.6-alpine3.24@sha256:44e74ca483234093081138b6d7b6f561d55557756a2deefc3a5056148defeb99
ARG SOURCE_COMMIT_SHA
RUN test "$(printf '%s' "$SOURCE_COMMIT_SHA" | wc -c)" -eq 40 \
    && case "$SOURCE_COMMIT_SHA" in *[!0-9a-f]*) exit 1 ;; *) : ;; esac
LABEL org.opencontainers.image.source="https://github.com/appolon1908-hue/telnexa" \
      org.opencontainers.image.revision="$SOURCE_COMMIT_SHA" \
      org.opencontainers.image.version="$SOURCE_COMMIT_SHA"
USER 0
RUN apk upgrade --no-cache
COPY --chown=101:0 docker/nginx/http.conf.template /opt/telnexa/http.conf.template
COPY --chown=101:0 docker/nginx/tls.conf.template /opt/telnexa/tls.conf.template
COPY --chown=101:0 --chmod=0755 docker/nginx/entrypoint.sh /docker-entrypoint.d/05-telnexa-config.sh
USER 101:101
EXPOSE 8080 8443
