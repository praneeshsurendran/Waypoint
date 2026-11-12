#!/bin/sh
# Local PostgreSQL initializer only; never executed against an existing volume.
set -eu
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
  --set=identity_password="$IDENTITY_DB_PASSWORD" \
  --set=network_password="$NETWORK_DB_PASSWORD" \
  --set=operations_password="$OPERATIONS_DB_PASSWORD" \
  --set=notifications_password="$NOTIFICATIONS_DB_PASSWORD" <<'SQL'
CREATE ROLE waypoint_identity LOGIN PASSWORD :'identity_password';
CREATE ROLE waypoint_network LOGIN PASSWORD :'network_password';
CREATE ROLE waypoint_operations LOGIN PASSWORD :'operations_password';
CREATE ROLE waypoint_notifications LOGIN PASSWORD :'notifications_password';
CREATE DATABASE waypoint_identity OWNER waypoint_identity;
CREATE DATABASE waypoint_network OWNER waypoint_network;
CREATE DATABASE waypoint_operations OWNER waypoint_operations;
CREATE DATABASE waypoint_notifications OWNER waypoint_notifications;
REVOKE CONNECT ON DATABASE waypoint_identity FROM PUBLIC;
REVOKE CONNECT ON DATABASE waypoint_network FROM PUBLIC;
REVOKE CONNECT ON DATABASE waypoint_operations FROM PUBLIC;
REVOKE CONNECT ON DATABASE waypoint_notifications FROM PUBLIC;
SQL
