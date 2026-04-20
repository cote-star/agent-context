# System Overview

## Product Shape

A one-endpoint HTTP service that responds to `GET /hello?name=<str>` with a greeting. Six source files, stdlib only, no external dependencies.

## Runtime Architecture

```
1. main.py parses CLI flags and merges them with env-backed Config
2. server.build_server(config) binds an HTTPServer with HelloHandler
3. HelloHandler.do_GET parses the URL, extracts `name`, writes the greeting
4. serve_forever blocks until SIGINT
```

## Key Subsystems

| Subsystem | Entry point | Main implementation | Data / external dependency |
|---|---|---|---|
| Entry + CLI | `src/main.py` | `parse_args`, `build_config`, `main` | env vars (optional) |
| HTTP layer | `src/server.py` | `HelloHandler`, `build_server`, `serve_forever` | none |
| Config | `src/config.py` | `Config.from_env` | env vars |

## Silent Failure Modes

| Failure | Symptom | Root cause |
|---|---|---|
| Missing `name` param | Greets "world" instead of a passed name | `_extract_name` falls back to `"world"` when the list is empty |
| Port already bound | OSError on start with no friendly message | `HTTPServer` does not wrap the bind call |

## Command / API Surface

| Command or surface | Purpose |
|---|---|
| `python3 -m src.server` | Start the server on the default host/port |
| `python3 -m src.main --port 9000` | Start with CLI overrides |
| `GET /hello?name=<str>` | Greeting endpoint |

## Tracked Path Density

| Directory | File count | Description |
|---|---|---|
| `src/` | 4 python files | Implementation |
| `tests/` | 1 python file | Unit tests |
