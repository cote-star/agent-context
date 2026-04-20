# hello-service

A tiny fabricated HTTP service used as a worked example for [agent-context](../..). It is intentionally small (six files, under 300 lines) so that a filled `.agent-context/current/` pack can be read end-to-end and the verifier can pass out of the box.

## Run

```bash
python3 -m src.server
```

Serves `GET /hello?name=<str>` on `127.0.0.1:8080`.

## Layout

- `src/server.py` — HTTP handler.
- `src/main.py` — entry point (argparse, wires config to server).
- `src/config.py` — environment-variable-backed config.
- `src/__init__.py` — package marker.
- `tests/test_server.py` — unit test for the handler.
- `.env.example` — sample config.

## Agent context

See `.agent-context/current/` for the filled pack. From the repo root:

```bash
../../bin/agent-context verify .
```
