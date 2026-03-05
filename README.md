# skill-audit

skill-audit is an automated red-team auditor for Skill documents (e.g. `SKILL.md`). It generates adversarial cases, simulates an assistant following your Skill, and then judges whether the assistant violates the Skill constraints. The result is an HTML report with per-case scores, violation reasons, and fix suggestions.

## Features

- Supports multiple providers: Ollama (local), OpenAI, MiniMax (OpenAI-compatible `/chat/completions`).
- Generates at least 5 adversarial cases, each with an `impact` level: `critical`, `high`, `medium`, `low`.
- Produces an HTML report: `report_MMDD_HHMM.html`.
- CI-friendly exit code via `--threshold`.

## Quickstart

### 1) Prerequisites

- Python 3.10+
- If using a local model: make sure Ollama is running and the model is available:

```bash
ollama run llama3:8b
```

### 2) Install (recommended)

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -U pip
python3 -m pip install -e .
```

Now you can run:

```bash
skill-audit --file SKILL.md --provider ollama --model llama3:8b
```

### 3) Run without installing (repo script)

```bash
./skill-audit --file SKILL.md --provider ollama --model llama3:8b
```

## Usage examples

### Ollama (local)

```bash
skill-audit --file SKILL.md --provider ollama --model llama3:8b
```

### OpenAI

```bash
export OPENAI_API_KEY="your_key"
skill-audit --file SKILL.md --provider openai --model gpt-4o
```

### MiniMax

```bash
export MINIMAX_API_KEY="your_key"
skill-audit --file SKILL.md --provider minimax --model MiniMax-M2.5
```

If you need a custom endpoint:

```bash
skill-audit --file SKILL.md --provider minimax --model MiniMax-M2.5 --url https://api.minimaxi.com/v1
```

## CLI flags

| Flag | Required | Notes |
| --- | --- | --- |
| `--file` | Yes | Path to the `SKILL.md` to evaluate. |
| `--provider` | No | `ollama` (default) / `openai` / `minimax`. |
| `--model` | Yes | Model name, e.g. `llama3:8b` or `gpt-4o`. |
| `--key` | OpenAI/MiniMax | Optional if you set `OPENAI_API_KEY` / `MINIMAX_API_KEY`. |
| `--url` | No | Override API base URL. |
| `--threshold` | No | Pass threshold (0-100), default 80. Exit 1 if below. |

## Build a single-file executable (optional)

If you want a standalone executable for distribution/CI:

```bash
python3 -m pip install -U pyinstaller
pyinstaller -F -n skill-audit --paths src skill-audit
./dist/skill-audit --file SKILL.md --provider ollama --model llama3:8b
```

## CI example (GitHub Actions)

```yaml
- name: Set up Python
  uses: actions/setup-python@v5
  with:
    python-version: "3.10"

- name: Install
  run: |
    python -m pip install -U pip
    python -m pip install .

- name: Run Skill Eval
  env:
    OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
  run: |
    skill-audit --file SKILL.md --provider openai --model gpt-4o --threshold 85
```
