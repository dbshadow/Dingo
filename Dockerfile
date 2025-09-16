# Use the official uv-provided Python image, which is pre-configured and optimized.
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

# Set the working directory in the container
WORKDIR /app

# --- Environment Variables ---
# Best practice: Avoid mentioning secret names in the Dockerfile.
# The API_TOKEN will be passed in at runtime via `docker run -e`.

# Prevents Python from writing .pyc files to disc and ensures output is sent to terminal
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# --- Install Dependencies ---
# Copy only the dependency definition file first to leverage Docker layer caching.
# The layer below will only be re-run if pyproject.toml changes.
COPY pyproject.toml ./

# Install project dependencies using the pre-installed uv
# The --no-cache flag is good practice in Docker to keep layers small.
RUN uv sync --no-cache

# --- Copy Application Code ---
# Copy the rest of the application code into the container.
# The .dockerignore file will prevent copying unnecessary files.
COPY . .

# --- Expose Port ---
# Expose the port the app runs on
EXPOSE 8000

# --- Run Command ---
# Use "uv run" to ensure that the command is executed within the environment
# managed by uv, which correctly resolves the path to uvicorn.
CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
