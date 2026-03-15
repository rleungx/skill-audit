# AGENTS.md

Repo guidance for coding agents working in `skill-audit`.

## Overview
- `skill-audit` is a Python CLI that red-teams `SKILL.md` files and writes an HTML report.
- Source: `src/skill_audit/`; tests: `tests/`; binary spec: `skill-audit.spec`.
- Packaging uses `setuptools`; CLI entrypoint is `skill-audit = skill_audit.cli:main`.
- Tests use the stdlib `unittest` runner, not `pytest`.

## Rule Files
- No prior repo root `AGENTS.md` existed.
- No `.cursorrules` file was found.
- No `.cursor/rules/` directory was found.
- No `.github/copilot-instructions.md` file was found.

## Environment
- Python requirement: `>=3.10`.
- This is a `src/` layout repo. Importing `skill_audit` requires either:
  - editable install: `python3 -m pip install -e '.[binary]'`
  - or `PYTHONPATH=src` on local commands.
- In a fresh checkout, default to `PYTHONPATH=src`.

## Setup
```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -U pip
python3 -m pip install -e '.[binary]'
```

## Core Commands
Run the CLI without install:
```bash
PYTHONPATH=src python3 -m skill_audit --help
```

Run the CLI after editable install:
```bash
skill-audit --help
```

Run the full test suite:
```bash
PYTHONPATH=src python3 -m unittest discover -s tests -t . -v
```

Run a single test method:
```bash
PYTHONPATH=src python3 -m unittest tests.test_cli.CliTests.test_main_rejects_freeze_and_snapshot_together -v
```

Run a single test module:
```bash
PYTHONPATH=src python3 -m unittest tests.test_lint -v
```

Smoke checks:
```bash
PYTHONPATH=src python3 -m py_compile src/skill_audit/cli.py
python3 -m compileall -q src
```

Build the binary:
```bash
PYINSTALLER_CONFIG_DIR=./build/pyinstaller-config pyinstaller --noconfirm --clean skill-audit.spec --distpath ./dist --workpath ./build/pyinstaller
```

Expected output:
```bash
./dist/skill-audit
```

Alternate README build target:
```bash
PYINSTALLER_CONFIG_DIR=./build/pyinstaller-config pyinstaller --noconfirm --clean skill-audit.spec --distpath ./release --workpath ./build/pyinstaller
```

## Workflow Notes
- README `unittest` commands assume editable install; if they fail with `ModuleNotFoundError`, use `PYTHONPATH=src`.
- Use dotted `unittest` paths, not `pytest` node ids.
- No repo config was found for `pytest`, `ruff`, `black`, `mypy`, `tox`, or `nox`.
- Validation here is mainly unit tests plus compile and syntax checks.

## Repository Map
- `src/skill_audit/cli.py`: argument parsing, orchestration, exit handling.
- `src/skill_audit/client.py`: HTTP clients and provider-compatible wrappers.
- `src/skill_audit/providers.py`: provider settings, key resolution, client construction.
- `src/skill_audit/api.py`: stable public imports for common models and audit workflow helpers.
- `src/skill_audit/evaluator.py`: domain models, detectors, scoring, audit logic.
- `src/skill_audit/lint.py`: static `SKILL.md` lint rules.
- `src/skill_audit/report.py`: HTML report rendering and redaction.
- `src/skill_audit/storage.py`: cache, snapshots, output paths.
- `src/skill_audit/progress.py`: progress and spinner helpers.

## Code Style

### Imports
- Put `from __future__ import annotations` first in Python modules.
- Group imports as standard library first, then local package imports.
- Prefer explicit relative imports inside the package.

### Formatting
- Use 4-space indentation.
- Use double quotes consistently.
- Keep blank lines between top-level declarations.
- Prefer small helper functions over deeply nested logic.
- Add comments only when a block is not obvious.

### Typing
- Use modern annotations: `list[str]`, `dict[str, Any]`, `str | None`.
- Annotate public functions and most helpers.
- Use `Protocol` and `TypeVar` only when they materially improve clarity.
- Use `Any` only for dynamic JSON-like payloads.

### Data And Naming
- Prefer `@dataclass(frozen=True)` for domain records.
- Existing examples include `AttackCase`, `RubricItem`, `JudgeResult`, and `LintFinding`.
- Functions, variables, and modules use `snake_case`.
- Classes use `PascalCase`; constants use `UPPER_SNAKE_CASE`.
- Private helpers use a leading underscore.
- Test classes use `*Tests`; test methods use `test_...`.

### CLI And Errors
- Keep parser construction in `_build_parser()`.
- Keep CLI entrypoints in `main(argv: Sequence[str] | None = None) -> None` style.
- Raise `ValueError` for invalid config/input.
- Raise `RuntimeError` for runtime, HTTP, or parse failures.
- Catch broad exceptions only at the CLI boundary and convert them into concise user-facing output.
- Preserve explicit exit codes: `SystemExit(1)` for failed runs, `SystemExit(2)` for argument/runtime-usage errors.

### Files, I/O, Security
- Use `pathlib.Path` for filesystem work.
- Open files with explicit `encoding="utf-8"`.
- Ensure parent directories exist before writing.
- Generated artifacts default to temp locations unless the caller overrides the path.
- Preserve redaction by default.
- Do not weaken checks that block sending credentials over insecure non-localhost HTTP.
- Be careful with regex-based detector or lint changes; update tests in the same change.

## Testing Conventions
- Use `unittest.mock.patch` for network and model isolation.
- Use `io.StringIO` plus `redirect_stdout` / `redirect_stderr` for CLI assertions.
- Use temp files in tests and clean them up explicitly.
- Keep tests deterministic and offline.

## What To Run For Common Changes
- CLI changes: `tests.test_cli` plus `python3 -m py_compile src/skill_audit/cli.py`
- Client/provider changes: `tests.test_client` and `tests.test_providers`
- Evaluator or detector changes: `tests.test_evaluator` and `tests.test_lint`
- Report changes: `tests.test_report`
- Storage changes: `tests.test_storage`
- Progress changes: `tests.test_progress`
- Any non-trivial change: the full `unittest` suite
