---
title: 'E1-S01 — Prosjektskjelett'
type: 'chore'
created: '2026-10-22'
status: 'done'
route: 'oneshot'
review_loop_iteration: 0
context:
  - '{project-root}/_bmad-output/implementation-artifacts/epic-1-context.md'
  - '{project-root}/docs/epics.md'
  - '{project-root}/docs/arkitektur.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** The repo has a data pipeline but no application. Every E1 story needs a Flask app factory, a dependency list, a config example and a test harness to build on.

**Approach:** Add the minimal Flask skeleton from the architecture (A1, §5, §7, §9): `app/__init__.py` with `create_app()` and a placeholder `/` route returning 200, `requirements.txt` (flask, tzdata, pytest), `.env.example` exactly as architecture §7, `tests/conftest.py` with an app/client fixture, and `tests/test_app.py::test_forside_svarer_200`. The app must start without `.env`. Acceptance per `docs/epics.md` E1-S01; mark the story ✅ there in the same commit, with commit message starting `E1-S01:`.

</frozen-after-approval>

## Implementation Notes

- No existing app code; pipeline scripts are stdlib-only and untouched.
- `create_app(config=None)` accepts an optional mapping so tests can set `TESTING`. No data loading yet (E1-S03).
- `/` returns a minimal Norwegian HTML page (`lang="nb"`, one `h1`) so later UU tests are not contradicted, but no template work — that belongs to E1-S06.
- Do not read `.env` (no python-dotenv dependency); config from `os.environ` arrives with the stories that need it.
- Python 3.9 compatible (macOS system Python).
- Added `pytest.ini` (`testpaths = tests`, `pythonpath = .`): without it `tests/conftest.py` could not import `app`. `pythonpath` needs pytest ≥ 7, so `requirements.txt` says `pytest>=7`.
- Verified manually: `flask --app app run` answers 200 on `/`.

## Review Triage Log

Blind Hunter (1 reviewer, ~1,3 kB diff):

- epics.md not marked ✅ — medium, real at review time (planned for the commit step). Patched: E1-S01 marked ✅.
- `flask --app app run` discovery untested — medium, real: the AC names the CLI but tests only call `create_app()`. Patched: `test_flask_cli_finner_appen` loads the app via `flask.cli.ScriptInfo`.
- `pythonpath` needs pytest ≥ 7 — low, real, one-token fix. Patched: `pytest>=7`.
- Test checks only status code, not `lang`/`h1` — low, rejected: placeholder is replaced in E1-S06, where UU structure tests arrive (E1-S15).
- No test that the app starts without `.env` — false for now: nothing reads the environment; `test_forside_svarer_200` already runs without `.env`.
- Docstring vs. "laster data én gang" — low, rejected: data loading is E1-S03.
- Unpinned `tzdata`/`pytest`; `pytest` as runtime dep — rejected: matches architecture §9 (deliberate simplicity, NFR5).
- `.env.example` inline comments break naive loaders — maybe-false: no loader exists yet. Deferred to when config is first read.
- `pytest.ini` strictness options — low, rejected: preference, no concrete failure.
- Hard-coded placeholder HTML — false: commented as placeholder for E1-S06.
- README "Kom i gang" missing — false for this story: scoped to E1-S16.
