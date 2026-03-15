# skill-audit

`skill-audit` checks whether a `SKILL.md` still holds up under high-risk scenarios.

Point it at a skill file, run it against the model you care about, and review the generated HTML report. The tool generates test cases, makes real model calls to produce assistant responses, and helps you spot weak instructions before they fail in real use.

Use it when you want to:
- pressure test a skill before sharing or shipping it
- compare behavior across providers or models
- iterate on prompts against a fixed snapshot instead of regenerating cases every run

Generated files go to the system temporary directory by default unless you set an explicit output path.

## Quickstart

Before you start:
- install `skill-audit` from the `Install` section below
- for local runs, make sure `ollama` is installed and the target model is available
- for hosted runs, export the matching API key for your provider

Run a first audit against a local model:

```bash
ollama run gpt-oss
skill-audit --file SKILL.md --model gpt-oss
```

Run against a hosted provider:

```bash
export OPENAI_API_KEY="your_key"
skill-audit --file SKILL.md --provider openai --model gpt-5.4
```

The provider and model names in this README are examples. Replace them with the model IDs available in your environment.

Write the report to a known location:

```bash
skill-audit --file SKILL.md --model gpt-oss --report ./out/report.html
```

Raise the pass bar when you want a stricter run:

```bash
skill-audit --file SKILL.md --model gpt-oss --threshold 85
```

## What you get from a run

Each run produces an HTML report you can inspect locally.

That report is built from:
- generated test cases
- assistant responses returned by the configured model
- scoring against the configured threshold
- optional static lint findings for `SKILL.md`

Unless you set `--report`, the report is written to the system temporary directory as `report_<timestamp>.html`.

If you use `--freeze` without a path, the snapshot is also written to the system temporary directory as `snapshot_<timestamp>.json`. In practice, it is usually easier to pass explicit `--report` and `--freeze PATH` values when you want to keep or share artifacts.

## How to read the results

Treat the report as a decision tool, not just a score.

- A passing run means the skill cleared the current threshold, default `80`
- A failing run means the skill missed that bar and needs revision
- Lint findings highlight high-risk issues in the `SKILL.md` itself
- Redaction is on by default, so suspected secrets are hidden in the HTML report

If you only have a minute, start with:
- the overall pass or fail status and score
- the lint section for obvious document-level problems
- the failing case cards and their judge reasons to see what broke first

If you want lint to fail the run when it finds high or critical issues, add `--fail-on-lint`. If you need to inspect raw report content, `--no-redact` disables redaction, which is unsafe for shared outputs.

## Iterate without changing the test set

When you are revising a skill, it is often useful to hold the generated cases steady.

Freeze a snapshot once:

```bash
skill-audit --file SKILL.md --model gpt-oss --freeze
```

Without a path, this writes a timestamped snapshot JSON file to the system temporary directory.

Then rerun the audit against that saved snapshot:

```bash
skill-audit --file SKILL.md --model gpt-oss --snapshot /path/to/snapshot.json
```

This makes it easier to compare edits to the same `SKILL.md` against the same underlying cases instead of regenerating them every time.

## Common options

- `--file`: `SKILL.md` to evaluate
- `--provider`: `ollama` / `openai` / `anthropic` / `google` / `minimax` / `xai` / `deepseek` / `zhipu` / `groq`
- `--model`: model name
- `--freeze [PATH]`: generate and save a snapshot
- `--snapshot PATH`: rerun against an existing snapshot
- `--report PATH`: custom report output path
- `--threshold N`: pass threshold, default `80`
- `--concurrency`, `-j`: number of cases to evaluate in parallel, default `1`
- `--fail-on-lint`: fail when static lint finds high/critical issues in `SKILL.md`
- `--no-lint`: disable static lint checks
- `--no-redact`: do not redact suspected secrets in the HTML report (unsafe)

## More provider examples

These model names are examples. Use the exact model IDs supported by your provider or local runtime.

```bash
export ANTHROPIC_API_KEY="your_key"
skill-audit --file SKILL.md --provider anthropic --model claude-opus-4-6

export GOOGLE_API_KEY="your_key"
skill-audit --file SKILL.md --provider google --model gemini-3.1-pro-preview

export MINIMAX_API_KEY="your_key"
skill-audit --file SKILL.md --provider minimax --model MiniMax-M2.5

export XAI_API_KEY="your_key"
skill-audit --file SKILL.md --provider xai --model grok-4

export DEEPSEEK_API_KEY="your_key"
skill-audit --file SKILL.md --provider deepseek --model deepseek-chat

export ZHIPU_API_KEY="your_key"
skill-audit --file SKILL.md --provider zhipu --model glm-4.5

export GROQ_API_KEY="your_key"
skill-audit --file SKILL.md --provider groq --model llama-3.3-70b-versatile -j 5
```

## Safety defaults

- `skill-audit` refuses to send credentials over plain HTTP to non-localhost endpoints. If you intentionally use an HTTP proxy, set `SKILL_AUDIT_ALLOW_INSECURE_HTTP=1`.

## Install

Recommended:

```bash
pipx install git+https://github.com/rleungx/skill-audit.git
skill-audit --help
```

If you prefer `pip`:

```bash
python3 -m pip install git+https://github.com/rleungx/skill-audit.git
skill-audit --help
```

If you do not want Python on the target machine, download the matching prebuilt archive from GitHub Releases, extract it, and run `skill-audit`.

## Local binary build prerequisites

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -U pip
python3 -m pip install -e '.[binary]'
```

## Build

```bash
PYINSTALLER_CONFIG_DIR=./build/pyinstaller-config pyinstaller --noconfirm --clean skill-audit.spec --distpath ./dist --workpath ./build/pyinstaller
```

Build output:

```bash
./dist/skill-audit
```

To write the binary to another directory:

```bash
PYINSTALLER_CONFIG_DIR=./build/pyinstaller-config pyinstaller --noconfirm --clean skill-audit.spec --distpath ./release --workpath ./build/pyinstaller
```

## Validate locally

```bash
python3 -m unittest discover -s tests -t . -v
python3 -m py_compile src/skill_audit/cli.py
```

If you have not installed the package in editable mode, prefix local checks with `PYTHONPATH=src`.

CI builds release archives automatically for tagged versions (`v*`).
