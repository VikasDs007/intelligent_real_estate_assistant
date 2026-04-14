# Intelligent Real Estate Assistant

An end-to-end real estate workflow app for agents, built with FastAPI + Streamlit.

It combines:
- client CRM and follow-up tracking
- property inventory browsing and filtering
- recommendation workflows for client-property matching
- a conversational AI assistant that can answer questions and trigger actions

## Features

- Dashboard with priority and portfolio visibility
- Client management (create, read, update, delete)
- Property explorer with advanced filtering
- Recommendation page with match suggestions and PDF export
- Task manager for follow-ups, site visits, and negotiations
- Market analysis charts
- AI assistant page with GPT-style chat interface
  - summarize clients/properties/tasks
  - fetch details by name or id
  - add notes from chat
  - create follow-up tasks from chat
  - open linked client/property pages from chat actions

## Tech Stack

- Backend: FastAPI, Uvicorn
- Frontend: Streamlit multipage app
- Data: Pandas, SQLite
- Utilities: Requests, FPDF
- Testing: Pytest

## Project Structure

- `app.py`: launcher that starts API + Streamlit
- `api.py`: REST API endpoints
- `assistant_engine.py`: chat intent handling, context building, optional model calls, command execution helpers
- `utils.py`: database and helper functions
- `pages/`: Streamlit pages
- `tests/`: test suite

## Setup

### 1. Clone and enter project

```bash
git clone <your-repository-url>
cd intelligent_real_estate_assistant
```

### 2. Create and activate virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
python3 -m pip install -r requirements.txt
```

### 4. (Optional) Rebuild database from Excel source

```bash
python3 database_setup.py
```

## Run the App

### Recommended: run full launcher

```bash
python3 app.py
```

This starts:
- FastAPI on `http://127.0.0.1:8000`
- Streamlit on `http://127.0.0.1:8501`

### Alternative: run Streamlit directly

```bash
python3 -m streamlit run Home.py
```

## AI Assistant Configuration

The assistant works in local smart mode by default (no external model key required).

To enable model-backed responses, set environment variables:

```bash
export REAL_ESTATE_AI_API_KEY="<your_api_key>"
export REAL_ESTATE_AI_MODEL="gpt-4o-mini"
# Optional if using a custom endpoint
export REAL_ESTATE_AI_BASE_URL="https://api.openai.com/v1"
```

Supported config keys are defined in `config.py`.

## GPT-Style Assistant Usage

Go to the AI assistant page in the app and try commands like:

- `show client CL-1001`
- `show asha`
- `add note for CL-1001: call tomorrow`
- `create task for CL-1001 tomorrow: site visit`
- `open property SALE-PROP-1001`
- `summarize market activity`

The assistant can:
- infer context from selected client/property
- perform direct actions from chat
- offer inline action buttons for common next steps

## Run Tests

```bash
python3 -m pytest -q
```

## Current Validation Status

Latest local run:
- compile checks passed
- test suite passing

## Notes

- `real_estate.db` is used as the default SQLite file.
- You can override paths and ports with environment variables in `config.py`.
- If port `8501` is busy, close existing Streamlit process or run on another port.

## License

MIT (see `LICENSE`)
