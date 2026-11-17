FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/services

WORKDIR /app

COPY services/requirements.txt /app/services/requirements.txt
RUN pip install --no-cache-dir -r /app/services/requirements.txt \
    && useradd --system --uid 10001 --create-home app

COPY services/db.py /app/services/db.py
COPY services/works-service/app.py /app/services/works-service/app.py

WORKDIR /app/services/works-service
USER 10001:10001

EXPOSE 3002

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "3002"]
