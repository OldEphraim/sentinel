FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir uv

# Worker reuses the API's pyproject.toml for dependencies
COPY apps/api/pyproject.toml ./pyproject.toml
RUN uv sync --no-dev

# Copy API source (worker imports from it)
COPY apps/api/src/ ./src/

# Copy worker entrypoint
COPY apps/worker/src/worker.py ./src/worker.py

EXPOSE 8001
CMD ["uv", "run", "python", "-m", "src.worker"]
