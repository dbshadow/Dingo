# D-Link Translator

A simple but powerful tool for translating CSV files using an Ollama-powered Large Language Model. It provides both a user-friendly Web UI and a versatile Command-Line Interface (CLI).

## Features

- **Dual Interface**: Use the intuitive Web UI for manual translations or the powerful CLI for automation and backend tasks.
- **CSV Translation**: Translates text from a `source` column to a `target` column in a CSV file.
- **Real-time Preview**: The Web UI features a live preview that shows translation progress in real-time using WebSockets.
- **Batch Processing**: Processes large files in batches, saving progress intermittently to prevent data loss.
- **Selective Translation**: Choose to overwrite existing translations or only fill in empty `target` fields.
- **Secure Web Access**: The web interface is protected by API Token authentication.
- **Configurable**: Easily configure languages, Ollama host, model, and batch size.

## Setup and Installation

This project is managed with `uv`. Ensure you have Python 3.10+ and `uv` installed.

**1. Clone the Repository**
```bash
git clone <repository-url>
cd DlinkTranslator
```

**2. Create Virtual Environment**
Use `uv` to create a virtual environment in the `.venv` directory.
```bash
uv venv
```

**3. Install Dependencies**
Activate the environment and install the required packages from `pyproject.toml`.
```bash
# On Linux/macOS
source .venv/bin/activate

# On Windows
.venv\Scripts\activate

# Install packages
uv sync
```

## Configuration

The web server requires an API Token for security. This is configured via a `.env` file.

**1. Create the `.env` file**
Create a file named `.env` in the root of the project directory.

**2. Set the API Token**
Add the following line to your `.env` file, replacing the example token with your own secure token.
```
API_TOKEN="your-super-secret-and-long-token-here"
```
> **Note**: The web server will fail to start if this token is not configured. This is a security feature.

## Usage

You can interact with this project via the Web UI or the CLI.

### Using the Web UI

The Web UI is ideal for most users. It provides a visual interface for uploading files and monitoring progress.

**1. Start the Server**
Run the following command from the project root:
```bash
uv run python main.py
```
The server will start on `http://localhost:8000`.

**2. Using the Interface**
- Open your web browser and navigate to `http://localhost:8000`.
- You will be prompted to enter the API Token you configured in the `.env` file.
- **Upload** your CSV file.
- **Select** the source and target languages.
- **Choose** whether to overwrite existing translations.
- Click **"Start Translation"**.
- Monitor the progress in the real-time log and preview table.
- Once complete, click **"Download Translated CSV"**.

### Using the CLI

The CLI is suitable for backend operations, automation, or when you have direct access to the server. It does **not** require an API token.

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
- `--overwrite`: Overwrites all entries in the target column, even if they already have content.
- `--batch-size <NUMBER>`: Sets the number of rows to process before saving. Defaults to `10`.
- `--model <MODEL_NAME>`: Specifies the Ollama model to use. Defaults to `gpt-oss:20b`.
- `--ollama_host <URL>`: Sets the URL for the Ollama host. Defaults to `http://192.168.7.149:11434`.
