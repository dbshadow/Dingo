# D-Link Translator

A web-based tool for translating CSV and IDML files using a local Ollama-powered Large Language Model, featuring a real-time task queue and a suite of IDML processing tools.

## ✨ Features

-   **Multi-User Ready**: Each user has their own API token. Users can see all tasks but can only manage (delete, download) their own.
-   **Asynchronous Task Queue**: A robust, non-blocking task queue processes uploaded jobs sequentially. Translation tasks are persistent and survive server restarts.
-   **Broad File Support**:
    -   Translate `.csv` and `.idml` files.
    -   **Glossary Support**: Upload a `.csv` glossary to guide the LLM and ensure terminological consistency.
-   **Live Task Board**: The Web UI features a live-updating task board showing the status (`pending`, `running`, `completed`, `error`) and progress of all tasks for all connected users via WebSockets.
-   **IDML Tool-kit**: A dedicated tab for a complete Adobe InDesign workflow:
    -   **Extractor**: Extracts text from an `.idml` file into a ready-to-translate `.csv` file.
    -   **Rebuilder**: Merges a translated `.csv` file back into the original `.idml` structure.
-   **Live Translator**: A simple, side-by-side interface for translating single sentences or short paragraphs on the fly.
-   **Secure & Dockerized**: Web access is protected by API Tokens, and the entire application is containerized with Docker for easy and consistent deployment.

## 🛠️ Tech Stack

-   **Backend**: FastAPI, Uvicorn, WebSockets
-   **Frontend**: Vanilla JavaScript, HTML5, CSS3
-   **LLM Integration**: Ollama
-   **Package Management**: `uv`
-   **Containerization**: Docker

## 🚀 Getting Started

### Prerequisites

-   Python 3.12+
-   `uv` (Python package manager)
-   Docker
-   A running instance of [Ollama](https://ollama.com/) with a model downloaded.

### Method 1: Docker (Recommended)

This is the easiest and most reliable way to run the application.

**1. Configure Environment**

Create a `.env` file in the project root. This file stores your Ollama configuration.

```ini
# .env
OLLAMA_HOST="http://host.docker.internal:11434"
OLLAMA_MODEL="llama3"
```

> **Note:** `host.docker.internal` is a special DNS name that allows the Docker container to connect to services running on your host machine (like Ollama). Replace `llama3` with the model you have downloaded.

**2. Manage API Tokens**

API tokens are now managed in the `api_tokens.json` file. You can add users and generate tokens using the built-in command-line tool.

```bash
# This will create the file and add 'first-user' with a new, secure token.
python -m token_manager add first-user
```

After running the command, your `api_tokens.json` will look like this:

```json
[
  {
    "name": "first-user",
    "token": "a-long-randomly-generated-token..."
  }
]
```

You can add more users by running the command again with a different name. You can also manually edit this file.

**3. Build the Docker Image**

```bash
docker build -t dlink-translator .
```

**4. Run the Docker Container**

This command uses Docker Volumes (`-v`) to link your local data and configuration files directly into the container. This ensures that your tasks, uploaded files, and API tokens are **persistent** and will not be lost when the container stops.

```bash
docker run -d -p 8000:8000 \
  --env-file ./.env \
  -v ./uploads:/app/uploads \
  -v ./tasks.json:/app/tasks.json \
  -v ./api_tokens.json:/app/api_tokens.json \
  --rm --name dlink-translator-app dlink-translator
```

- `-d`: Run in detached mode (in the background).
- `--rm`: Automatically remove the container when it exits.
- `--name`: Assign a convenient name to the container.

The application will be available at `http://localhost:8000`.

### Method 2: Local Development

**1. Configure Environment**

Create the `.env` file as described above, but adjust `OLLAMA_HOST` for local access.

```ini
# .env
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=llama3
```

**2. Manage API Tokens**

Run the token manager script to create your first token:

```bash
python -m token_manager add my-local-user
```

**3. Install Dependencies**

`uv` creates a virtual environment and installs dependencies in one step.

```bash
uv sync
```

**4. Run the Web Server**

Use `uv run` to execute the `uvicorn` server.

```bash
uv run uvicorn main:app --host 0.0.0.0 --port 8000
```

The application will be available at `http://localhost:8000`.

## ⚙️ Configuration

| Item              | Required | Description                                                                                             |
| ----------------- | :------: | ------------------------------------------------------------------------------------------------------- |
| `api_tokens.json` |   Yes    | A JSON file containing a list of user objects, each with a `name` and `token`. Manages access to the UI. |
| `OLLAMA_HOST`     |   Yes    | The full URL of your running Ollama instance (e.g., `http://localhost:11434`). Set in `.env`.          |
| `OLLAMA_MODEL`    |   Yes    | The name of the Ollama model to use for translations (e.g., `llama3`, `mistral`). Set in `.env`.      |

## 📁 Project Structure

```
/
├── .dockerignore
├── .gitignore
├── api_tokens.json     # NEW: Manages user API tokens.
├── cli.py              # Standalone CLI for direct translation (bypasses queue).
├── Dockerfile          # Defines the Docker container for the application.
├── main.py             # FastAPI application entry point, handles startup/shutdown.
├── processor.py        # Core logic for CSV and IDML translation processing.
├── pyproject.toml      # Project metadata and dependencies for `uv`.
├── README.md           # This file.
├── storage.py          # Handles reading/writing to the tasks.json file.
├── token_manager.py    # NEW: Script to manage the api_tokens.json file.
├── translator.py       # Contains the core `translate_text` function that calls Ollama.
├── worker.py           # Background worker that picks up and runs tasks from the queue.
├── routers/            # FastAPI routers for different API endpoints (tasks, idml, etc.).
├── static/             # Frontend CSS and JavaScript files.
└── templates/          # Contains the main index.html template.
```

## 🤖 CLI Usage

The CLI is a separate tool for direct, scriptable translations and does **not** interact with the Web UI or the task queue.

**1. Command Structure**

```bash
uv run python cli.py [CSV_PATH] [SOURCE_LANG] [TARGET_LANG] [OPTIONS]
```

**2. Example**

To translate `example/test.csv` from English to German:

```bash
uv run python cli.py example/test.csv en de
```

**3. Options**

-   `--overwrite`: Overwrites all entries in the target column.
-   `--batch-size <NUMBER>`: Sets the number of rows to process before saving (default: 10).
-   `--model <MODEL_NAME>`: Specifies the Ollama model to use.
-   `--ollama_host <URL>`: Sets the URL for the Ollama host.
