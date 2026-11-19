FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/services

WORKDIR /app

COPY services/requirements.txt /app/services/requirements.txt
RUN pip install --no-cache-dir -r /app/services/requirements.txt \
    && useradd --system --uid 10001 --create-home app

COPY services/db.py /app/services/db.py
COPY services/auth_client.py /app/services/auth_client.py
COPY services/security.py /app/services/security.py
COPY services/service_client.py /app/services/service_client.py
COPY services/error_handling.py /app/services/error_handling.py
COPY services/gallery_service /app/services/gallery_service
COPY services/gallery-service/app.py /app/services/gallery-service/app.py

WORKDIR /app/services/gallery-service
USER 10001:10001

EXPOSE 3001

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "3001"]
