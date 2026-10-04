FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml .
RUN pip install --no-cache-dir ".[dev]"
COPY . .
CMD ["celery", "-A", "apps.worker.celery_app:celery_app", "worker", "--loglevel=INFO"]
