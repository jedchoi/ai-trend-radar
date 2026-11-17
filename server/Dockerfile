# backend-server 이미지 (infrastructure-design.md). 베이스 이미지는 버전 고정 (SECURITY-10)
# 데이터는 PostgreSQL (DATABASE_URL) 에 둔다. 이미지에는 상태가 없다.
FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /srv
COPY requirements.lock .
RUN pip install --require-hashes --no-deps -r requirements.lock \
    && useradd --system --uid 10001 --home /srv app

COPY app ./app
USER app
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health').status==200 else 1)"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*", "--no-server-header"]
