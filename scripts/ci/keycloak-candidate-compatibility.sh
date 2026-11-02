#!/usr/bin/env bash
# Disposable hosted CI only: no host ports, external network or production data.
set -euo pipefail
network="telnexa-keycloak-ci-${GITHUB_RUN_ID:-local}"
server="telnexa-keycloak-ci-${GITHUB_RUN_ID:-local}"
database="telnexa-keycloak-db-ci-${GITHUB_RUN_ID:-local}"
configure="telnexa-keycloak-configure-ci-${GITHUB_RUN_ID:-local}"
secret_dir=$(mktemp -d)
cleanup() {
  docker rm -f "$configure" "$server" "$database" >/dev/null 2>&1 || true
  docker network rm "$network" >/dev/null 2>&1 || true
  rm -rf "$secret_dir"
}
trap cleanup EXIT
password=$(openssl rand -hex 24)
printf '::add-mask::%s\n' "$password"
printf '%s' "$password" > "$secret_dir/admin-password"
chmod 0755 "$secret_dir"
chmod 0644 "$secret_dir/admin-password"
postgres=postgres:17.6-alpine@sha256:d5f196a551b5cef1c70853c6dd588f456d16ca4ea733e3f31c75bc1ae2f65f3f
docker pull "$postgres"
docker network create --internal "$network"
docker run -d --name "$database" --network "$network" --network-alias keycloak-db \
  --tmpfs /var/lib/postgresql/data \
  -e POSTGRES_DB=keycloak -e POSTGRES_USER=keycloak -e POSTGRES_PASSWORD="$password" "$postgres"
ready=false
for attempt in $(seq 1 60); do
  if docker exec "$database" pg_isready -U keycloak -d keycloak >/dev/null 2>&1; then ready=true; break; fi
  sleep 2
done
test "$ready" = true
docker run -d --name "$server" --network "$network" --network-alias keycloak \
  --cap-drop ALL --security-opt no-new-privileges:true \
  -e KC_BOOTSTRAP_ADMIN_USERNAME=telnexa-bootstrap -e KC_BOOTSTRAP_ADMIN_PASSWORD="$password" \
  -e KC_DB=postgres -e KC_DB_URL=jdbc:postgresql://keycloak-db:5432/keycloak \
  -e KC_DB_USERNAME=keycloak -e KC_DB_PASSWORD="$password" \
  -e KC_HTTP_ENABLED=true -e KC_HOSTNAME=http://keycloak:8080/auth \
  -v "$PWD/config/keycloak/telnexa-realm.json:/opt/keycloak/data/import/telnexa-realm.json:ro" \
  telnexa-security:keycloak start --optimized --import-realm
ready=false
for attempt in $(seq 1 90); do
  if docker exec "$server" /opt/keycloak/bin/kcadm.sh config credentials \
      --server http://localhost:8080/auth --realm master --user telnexa-bootstrap \
      --password "$password" >/dev/null 2>&1; then ready=true; break; fi
  sleep 2
done
if test "$ready" != true; then docker logs "$server"; exit 1; fi
docker exec "$server" java -version
docker run --rm --name "$configure" --network "$network" \
  --cap-drop ALL --security-opt no-new-privileges:true \
  -v "$secret_dir/admin-password:/run/secrets/keycloak_admin_password:ro" \
  -v "$PWD/scripts/keycloak-configure.sh:/opt/telnexa/keycloak-configure.sh:ro" \
  -v "$PWD/config/keycloak/user-profile.json:/opt/telnexa/user-profile.json:ro" \
  --entrypoint /bin/bash telnexa-security:keycloak /opt/telnexa/keycloak-configure.sh
printf '%s\n' 'Disposable PostgreSQL realm import and original Keycloak configuration assertions passed'
