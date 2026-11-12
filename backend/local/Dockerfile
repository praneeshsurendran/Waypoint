FROM python:3.13-slim
RUN useradd --create-home --uid 10001 waypoint
WORKDIR /opt/waypoint
COPY requirements.lock .
RUN pip install --no-cache-dir -r requirements.lock
COPY packages packages
COPY services services
COPY scripts scripts
ENV PYTHONPATH=/opt/waypoint/services/operations/src:/opt/waypoint/services/identity-access/src:/opt/waypoint/services/network-fleet/src:/opt/waypoint/services/notifications/src:/opt/waypoint/packages/contracts:/opt/waypoint/packages/security:/opt/waypoint/packages/observability:/opt/waypoint/packages/messaging:/opt/waypoint/packages/runtime
USER waypoint
