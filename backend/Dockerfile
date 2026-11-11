FROM python:3.12.16-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /app
COPY requirements.txt requirements-dev.txt constraints.txt ./
RUN pip install --no-cache-dir -r requirements-dev.txt -c constraints.txt \
    && useradd --create-home soup
COPY . .
USER soup
EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn app.main:create_app --factory --host 0.0.0.0 --port 8000 --no-access-log --timeout-graceful-shutdown 2"]
