FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

COPY pyproject.toml ./
COPY src ./src
RUN pip install --no-cache-dir .

COPY data/sample ./data/sample

ENV JOBSCOPE_ENV=production JOBSCOPE_DB=/data/jobscope.db
EXPOSE 8000
CMD ["sh", "-c", "uvicorn jobscope.api.main:app --host 0.0.0.0 --port ${PORT:-8000}"]