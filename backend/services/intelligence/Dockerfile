FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
RUN useradd --create-home --uid 10001 waypoint
WORKDIR /opt/waypoint
COPY requirements.lock /opt/waypoint/requirements.lock
COPY services/intelligence/requirements.lock /opt/waypoint/ml-requirements.lock
RUN pip install --no-cache-dir -r requirements.lock -r ml-requirements.lock
COPY packages /opt/waypoint/packages
COPY services/intelligence/src /opt/waypoint/src
ENV PYTHONPATH=/opt/waypoint/src:/opt/waypoint/packages/contracts:/opt/waypoint/packages/security:/opt/waypoint/packages/observability:/opt/waypoint/packages/runtime
ENV WAYPOINT_INTELLIGENCE_WORKSPACE=/opt/waypoint/private/intelligence
USER waypoint
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=10s CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health/ready', timeout=8)"
CMD ["uvicorn", "waypoint_intelligence.main:app", "--no-proxy-headers", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
