# Use official Python lightweight image
FROM python:3.13-slim AS builder

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set working directory
WORKDIR /app

# Copy the dependency files
# We need both pyproject.toml and uv.lock for a frozen sync
COPY pyproject.toml uv.lock ./

# Install dependencies using uv
# This creates a .venv directory in /app/.venv
RUN uv sync --frozen --no-dev

# Second stage: final image
FROM python:3.13-slim

WORKDIR /app

# Copy the virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Update PATH to use the virtual environment
ENV PATH="/app/.venv/bin:$PATH"

# Copy application files
COPY . .

# Expose port
EXPOSE 8080

# Environment variables
ENV PORT=8080
ENV PYTHONUNBUFFERED=1

# Command to run the application
# We use shell form to expand the $PORT variable correctly
CMD uvicorn main:app --host 0.0.0.0 --port $PORT
