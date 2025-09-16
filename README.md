# D-Link Translator

A web-based and command-line tool for translating CSV files and processing IDML files using an Ollama-powered Large Language Model.

## Features

- **Dual Interface**: Use the intuitive Web UI for manual tasks or the powerful CLI for automation.
- **CSV Translation**: Translates text from a `source` column to a `target` column in a CSV file with real-time progress updates.
- **IDML Workflow**: Provides a complete workflow for translating Adobe InDesign files:
    - **Extractor**: Extracts text from an `.idml` file into a ready-to-translate `.csv` file.
    - **Rebuilder**: Merges a translated `.csv` file back into the original `.idml` structure.
- **Real-time Preview**: The Web UI features a live preview that shows translation progress in a color-coded table.
- **Secure & Configurable**: Web access is protected by a configurable API Token, and key parameters like languages and Ollama settings can be easily adjusted.
- **Dockerized**: Comes with a production-ready Dockerfile for easy deployment.

## Setup and Installation (Local Development)

This project is managed with `uv`. Ensure you have Python 3.10+ and `uv` installed.

**1. Clone the Repository**
```bash
git clone <repository-url>
cd DlinkTranslator
```

**2. Create Virtual Environment & Install Dependencies**
`uv` can perform both steps in one command:
```bash
uv sync
```
This creates a `.venv` folder if it doesn't exist and installs all packages from `pyproject.toml`.

**3. Configure API Token**
Create a `.env` file in the project root and add your secret API token:
```
API_TOKEN="your-super-secret-and-long-token-here"
```
> **Note**: The web server will fail to start if this token is not configured. This is a security feature.

**4. Run the Web Server**
```bash
uv run python main.py
```
The server will start on `http://localhost:8000`.

## Running with Docker (Recommended)

Using Docker is the recommended way to run this application in a stable, isolated environment.

**1. Build the Docker Image**
From the project root, run:
```bash
docker build -t dlink-translator .
```

**2. Run the Docker Container**
You must provide the API_TOKEN from your `.env` file to the container at runtime.
```bash
docker run -p 8000:8000 --env-file .env --rm -it dlink-translator
```
- `-p 8000:8000`: Maps your local port 8000 to the container's port 8000.
- `--env-file .env`: Securely passes the environment variables (like `API_TOKEN`) from your `.env` file to the container.
- `--rm`: Automatically removes the container when it exits.
- `-it`: Runs the container in interactive mode so you can see logs and stop it with `Ctrl+C`.

The application will be available at `http://localhost:8000`.

## Usage

### Web UI

The Web UI provides access to all features through a tabbed interface.

1.  Open your browser to `http://localhost:8000`.
2.  Enter the API Token when prompted.
3.  Navigate between the two main tabs:

    -   **CSV Translator**: 
        - Upload a CSV file with `source` and `target` columns.
        - Select source/target languages.
        - Click "Start Translation" to begin.
        - Monitor progress in the real-time log and preview table.
        - Download the completed CSV file.

    -   **IDML Tools**:
        - **Extractor**: Upload an `.idml` file to generate and download a translatable `.csv` file.
        - **Rebuilder**: Upload the original `.idml` and the translated `.csv` to generate a new, translated `.idml` file.

### Command-Line Interface (CLI)

The CLI is suitable for backend operations and automation. It does **not** require an API token.

**1. Command Structure**
```bash
uv run python cli.py [CSV_PATH] [SOURCE_LANG] [TARGET_LANG] [OPTIONS]
```

**2. Example**
To translate `test.csv` from English to German:
```bash
uv run python cli.py test.csv English German
```

**3. Options**
- `--overwrite`: Overwrites all entries in the target column.
- `--batch-size <NUMBER>`: Sets the number of rows to process before saving (default: 10).
- `--model <MODEL_NAME>`: Specifies the Ollama model to use (default: `gpt-oss:20b`).
- `--ollama_host <URL>`: Sets the URL for the Ollama host.