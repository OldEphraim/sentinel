FROM python:3.11-slim

WORKDIR /app

# Install uv
RUN pip install --no-cache-dir uv

# Install dependencies (before copying source — better layer caching)
COPY pyproject.toml ./
RUN uv sync --no-dev

# Copy source
COPY src/ ./src/

EXPOSE 8000
CMD ["uv", "run", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
