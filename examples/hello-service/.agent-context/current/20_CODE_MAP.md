# Code Map

## High-Impact Paths

| # | Path | What it does | Why it matters | Risk | Authority |
|---|---|---|---|---|---|
| 1 | `src/server.py` | HTTP handler and server binder | All request handling lives here | MEDIUM | authoritative |
| 2 | `src/config.py` | Env-backed Config dataclass | All runtime values flow through this | LOW | authoritative |
| 3 | `src/main.py` | CLI entry and config merge | Defines how CLI flags interact with env | LOW | authoritative |

## Quick Lookup Shortcuts

| Question | Answer |
|---|---|
| Where is the HTTP route registered? | `src/server.py` inside `HelloHandler.do_GET` (route string `/hello`) |
| Where do env vars get read? | `src/config.py` in `Config.from_env` |
| Where does a CLI flag override env? | `src/main.py` in `build_config` |

## Cross-Cutting Tracing Flows

### Adding a new query parameter

1. Extract the value in `src/server.py` (alongside `_extract_name`)
2. Thread it through `HelloHandler.do_GET`
3. Add a test in `tests/test_server.py`

## Extension Recipe

To add a new endpoint, branch in `HelloHandler.do_GET` on `parsed.path`, write the response, and add a dedicated test in `tests/test_server.py`.
