ARG KEYCLOAK_BASE_IMAGE=quay.io/keycloak/keycloak:26.7.5@sha256:37dbaf6f0722c9ec246335f36e1ef8b2e6cb960f7c27e0d8c615121a3d475a85

# The official 26.7.5 distribution supplies fixed Netty 4.1.138.Final,
# Jackson 2.21.7 (including the admin CLI), BouncyCastle 1.86 and FreeMarker
# 2.3.35. Guava's remaining CVE-2026-102554 is fixed by 33.7.2-jre.
FROM scratch AS guava-security-fix
ADD --checksum=sha256:b530942257fb935f8b2cfaa5f8eb5bd59c555fd8e8d01b8ce98912e077ea606c \
    https://repo.maven.apache.org/maven2/com/google/guava/guava/33.7.2-jre/guava-33.7.2-jre.jar \
    /guava-33.7.2-jre.jar

FROM ${KEYCLOAK_BASE_IMAGE} AS builder
ENV KC_DB=postgres KC_HEALTH_ENABLED=true KC_METRICS_ENABLED=true KC_HTTP_RELATIVE_PATH=/auth
RUN /opt/keycloak/bin/kc.sh build
USER 0
# Preserve the augmented dependency path while replacing the vulnerable bytes.
COPY --from=guava-security-fix --chown=1000:0 --chmod=0644 /guava-33.7.2-jre.jar /opt/keycloak/lib/lib/main/com.google.guava.guava-33.5.0-jre.jar
USER 1000

# Use the original root filesystem and signed UBI repositories to update only
# the four vulnerable native packages. The builder's own filesystem is never
# copied into the candidate; a scratch final stage also removes obsolete files.
FROM ${KEYCLOAK_BASE_IMAGE} AS native-source
FROM redhat/ubi9:9.8@sha256:8f989cc9270da6abec0144c22846ed1e6e92e462dc7768ce0981c4ac1d574733 AS native-security-fix
COPY --from=native-source / /mnt/rootfs/
RUN rpm --root /mnt/rootfs -qa --qf '%{NAME} %{EPOCHNUM}:%{VERSION}-%{RELEASE}\n' > /tmp/rpm-before.txt \
    && test -s /tmp/rpm-before.txt && sort -o /tmp/rpm-before.txt /tmp/rpm-before.txt \
    && dnf -y --installroot /mnt/rootfs --releasever 9 \
       --setopt=install_weak_deps=False --setopt=tsflags=nodocs \
       --setopt=gpgcheck=True \
       update \
       ca-certificates-2026.2.92_v9.0.319-90.3.el9_8 \
       java-21-openjdk-headless-21.0.13.0.9-1.2.el9 \
       pcre2-10.40-7.el9_8 pcre2-syntax-10.40-7.el9_8 \
    && rpm --root /mnt/rootfs -qa --qf '%{NAME} %{EPOCHNUM}:%{VERSION}-%{RELEASE}\n' > /tmp/rpm-after.txt \
    && test -s /tmp/rpm-after.txt && sort -o /tmp/rpm-after.txt /tmp/rpm-after.txt \
    && (diff -U 0 /tmp/rpm-before.txt /tmp/rpm-after.txt > /tmp/rpm-changes.txt || test "$?" -eq 1) \
    && awk '/^[+-][^+-]/ { if ($1 !~ /^[+-](ca-certificates|java-21-openjdk-headless|pcre2|pcre2-syntax)$/) exit 1 }' /tmp/rpm-changes.txt \
    && test "$(grep -Ec '^[+-][^+-]' /tmp/rpm-changes.txt)" -eq 8 \
    && cat /tmp/rpm-changes.txt \
    && mkdir -p /mnt/rootfs/usr/share/telnexa \
    && cp /tmp/rpm-before.txt /mnt/rootfs/usr/share/telnexa/rpm-before.txt \
    && cp /tmp/rpm-after.txt /mnt/rootfs/usr/share/telnexa/rpm-after.txt \
    && dnf --installroot /mnt/rootfs clean all \
    && rm -rf /mnt/rootfs/var/cache/dnf /mnt/rootfs/var/log/dnf* /mnt/rootfs/var/log/yum*

FROM scratch
COPY --from=native-security-fix /mnt/rootfs/ /
ENV PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \
    LANG=en_US.UTF-8 \
    KC_RUN_IN_CONTAINER=true
LABEL architecture="x86_64" \
      build-date="2026-09-14T00:32:05Z" \
      com.redhat.build-host="" \
      com.redhat.component="" \
      com.redhat.license_terms="" \
      cpe="cpe:/a:redhat:enterprise_linux:9::appstream" \
      description="Keycloak Server Image" \
      distribution-scope="public" \
      io.buildah.version="1.44.0" \
      io.k8s.description="Keycloak Server Image" \
      io.k8s.display-name="Keycloak Server" \
      io.openshift.expose-services="" \
      io.openshift.tags="keycloak security identity" \
      maintainer="https://www.keycloak.org/" \
      name="keycloak" \
      org.opencontainers.image.created="2026-09-30T17:44:36.891Z" \
      org.opencontainers.image.description="" \
      org.opencontainers.image.documentation="https://www.keycloak.org/documentation" \
      org.opencontainers.image.licenses="Apache-2.0" \
      org.opencontainers.image.title="keycloak-rel" \
      org.opencontainers.image.url="https://github.com/keycloak-rel/keycloak-rel" \
      release="" \
      summary="Keycloak Server Image" \
      url="https://www.keycloak.org/" \
      vcs-ref="" \
      vcs-type="git" \
      vendor="https://www.keycloak.org/" \
      version="26.7.5"
WORKDIR /
EXPOSE 8080 8443 9000
ENTRYPOINT ["/opt/keycloak/bin/kc.sh"]
ARG SOURCE_COMMIT_SHA
RUN test "$(printf '%s' "$SOURCE_COMMIT_SHA" | wc -c)" -eq 40 \
    && case "$SOURCE_COMMIT_SHA" in *[!0-9a-f]*) exit 1 ;; *) : ;; esac
LABEL org.opencontainers.image.source="https://github.com/appolon1908-hue/telnexa" \
      org.opencontainers.image.revision="$SOURCE_COMMIT_SHA" \
      org.opencontainers.image.version="$SOURCE_COMMIT_SHA"
USER 0
COPY --from=builder /opt/keycloak/ /opt/keycloak/
RUN rm -f /opt/keycloak/lib/lib/main/com.microsoft.sqlserver.mssql-jdbc-*.jar \
    && test -z "$(find /opt/keycloak -type f -name 'com.microsoft.sqlserver.mssql-jdbc-*.jar' -print -quit)" \
    && printf '%s  %s\n' \
      'b530942257fb935f8b2cfaa5f8eb5bd59c555fd8e8d01b8ce98912e077ea606c' \
      '/opt/keycloak/lib/lib/main/com.google.guava.guava-33.5.0-jre.jar' \
      | sha256sum -c - \
    && test -f /opt/keycloak/bin/client/keycloak-admin-cli-26.7.5.jar \
    && for artifact in \
      io.netty.netty-handler-4.1.138.Final.jar \
      io.netty.netty-codec-http-4.1.138.Final.jar \
      com.fasterxml.jackson.core.jackson-core-2.21.7.jar \
      com.fasterxml.jackson.core.jackson-databind-2.21.7.jar \
      org.bouncycastle.bcprov-jdk18on-1.86.jar \
      org.freemarker.freemarker-2.3.35.jar; do \
      test -f "/opt/keycloak/lib/lib/main/$artifact" || exit 1; \
    done
USER 1000
ENV KC_HTTP_RELATIVE_PATH=/auth
