# Behavioral Invariants

## Testable Invariants

Before writing any invariant that uses words like "every", "all", "must", or "always", search for counter-examples in the repo first.

1. `_extract_name` returns `"world"` when no `name` query param is present (`src/server.py`).
2. `Config.from_env` always returns a `Config` instance with an integer `port` (`src/config.py`).
3. `HelloHandler` only handles `/hello`; other paths 404 (`src/server.py`, `do_GET`).

## Update Checklist

| Change type | Files that MUST change |
|---|---|
| New query parameter | `src/server.py`, `tests/test_server.py` |
| New env-backed config value | `src/config.py`, `src/main.py` (CLI override), `.env.example` |
| New endpoint | `src/server.py`, `tests/test_server.py`, `README.md` |

## File Families

| Glob pattern | Member count | Report as |
|---|---|---|
| `src/*.py` | 4 | "all src modules" |
| `tests/*.py` | 1 | "test suite" |

## Negative Guidance

- Do not re-enumerate the stdlib `http.server` internals — they are not part of this repo's authority surface.
- Do not treat `__init__.py` as a place for logic; it only exports `__version__`.
