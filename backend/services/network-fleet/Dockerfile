FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN useradd --create-home --uid 10001 waypoint
WORKDIR /opt/waypoint
COPY requirements.lock /opt/waypoint/requirements.lock
RUN pip install --no-cache-dir -r requirements.lock
COPY packages /opt/waypoint/packages
COPY services/network-fleet/src /opt/waypoint/src
COPY services/network-fleet/migrations /opt/waypoint/migrations
COPY services/network-fleet/alembic.ini /opt/waypoint/alembic.ini
ENV PYTHONPATH=/opt/waypoint/src:/opt/waypoint/packages/contracts:/opt/waypoint/packages/security:/opt/waypoint/packages/observability:/opt/waypoint/packages/messaging
USER waypoint
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health/live', timeout=3)"
CMD ["uvicorn", "waypoint_network.main:app", "--host", "0.0.0.0", "--port", "8000", "--timeout-graceful-shutdown", "30"]
