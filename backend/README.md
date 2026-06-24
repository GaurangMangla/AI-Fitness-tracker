# Athlyt Backend

FastAPI backend for Athlyt. See the root [README](../README.md) for the full
project overview and setup instructions.

## Quick reference

```bash
# Install
pip install -e ".[dev]"

# Run the dev server (auto-reloads on file changes)
uvicorn app.main:app --reload

# Lint / format
ruff check .
black --check .

# Tests
pytest
```

A SQLite database file (`athlyt.db`) is created automatically in this folder
the first time the app starts — no separate setup step needed.
