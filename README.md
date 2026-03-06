# skill-audit

`skill-audit` evaluates whether a `SKILL.md` remains reliable under high-risk scenarios.

It generates test cases, simulates assistant responses, and writes an HTML report. Generated files go to the system temporary directory by default.

## 1. Install dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -U pip
python3 -m pip install -e '.[binary]'
```

## 2. Build

```bash
./scripts/build-binary.sh
```

Build output:

```bash
./dist/skill-audit
```

To write the binary to another directory:

```bash
./scripts/build-binary.sh ./release
```

## 3. Usage

Common commands:

```bash
# Local Ollama
ollama run gpt-oss
./dist/skill-audit --file SKILL.md --model gpt-oss

# OpenAI
export OPENAI_API_KEY="your_key"
./dist/skill-audit --file SKILL.md --provider openai --model gpt-5.4

# Freeze a snapshot for repeated iteration
./dist/skill-audit --file SKILL.md --model gpt-oss --freeze
./dist/skill-audit --file SKILL.md --model gpt-oss --snapshot /path/to/snapshot.json

# Custom report path
./dist/skill-audit --file SKILL.md --model gpt-oss --report ./out/report.html

# Custom pass threshold
./dist/skill-audit --file SKILL.md --model gpt-oss --threshold 85
```

Common options:

- `--file`: `SKILL.md` to evaluate
- `--provider`: `ollama` / `openai` / `anthropic` / `google` / `minimax`
- `--model`: model name
- `--freeze [PATH]`: generate and save a snapshot
- `--snapshot PATH`: rerun against an existing snapshot
- `--report PATH`: custom report output path
- `--threshold N`: pass threshold, default `80`

Other provider examples:

```bash
export ANTHROPIC_API_KEY="your_key"
./dist/skill-audit --file SKILL.md --provider anthropic --model claude-opus-4-6

export GOOGLE_API_KEY="your_key"
./dist/skill-audit --file SKILL.md --provider google --model gemini-3.1-pro-preview

export MINIMAX_API_KEY="your_key"
./dist/skill-audit --file SKILL.md --provider minimax --model MiniMax-M2.5
```
