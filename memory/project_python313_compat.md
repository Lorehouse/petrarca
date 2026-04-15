---
name: Python 3.13 compatibility fixes
description: Fixes applied to run petrarca on Python 3.13 locally (cgi module removed, missing packages)
type: project
---

The server was written targeting an older Python. Running on Python 3.13 (via miniconda) required these fixes:

- `cgi` module removed in 3.13 — replaced `_parse_multipart_form()` in `research-server.py` with `python-multipart` library
- `google-genai` and `fsrs` packages missing from `requirements.txt` — installed manually
- `sys.path.insert(0, '/opt/limbic')` removed from `db.py` — limbic is installed in venv

**Why:** The original server ran on a Hetzner VM with an older Python. Local dev on macOS uses Python 3.13 via miniconda which removed the `cgi` stdlib module.

**How to apply:** If new multipart upload endpoints break, check `_parse_multipart_form()` in `research-server.py`. If new imports fail at startup, install the missing package into the venv with `uv pip install <pkg> --python venv/bin/python3`.
