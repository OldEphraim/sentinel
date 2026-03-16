# Full Dockerfile implemented in Step 12
FROM python:3.11-slim
WORKDIR /app
RUN pip install uv
COPY . .
RUN uv sync
CMD ["uv", "run", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
