# Backend

See [BACKEND_README.md](BACKEND_README.md) for full documentation.

## Quick Start

```bash
# From project root — starts both backend and frontend
bash run_website.sh

# Backend only (uvicorn on port 8000)
cd backend
../.venv/bin/python -m uvicorn api:app --host 127.0.0.1 --port 8000

# CLI
python main.py               # retrieval + generation
python main.py --no-generate # retrieval only
```

