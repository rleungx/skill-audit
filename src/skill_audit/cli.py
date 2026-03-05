from __future__ import annotations

import argparse
import os
from datetime import datetime

from .client import OpenAICompatClient
from .evaluator import CaseResult, generate_attack_cases, judge_case, run_skill_response
from .report import render_html_report


def _build_default_base_url(provider: str, url: str | None) -> str:
    if url:
        return url
    if provider == "ollama":
        return "http://localhost:11434/v1"
    if provider == "minimax":
        env_url = os.environ.get("MINIMAX_BASE_URL")
        if env_url:
            return env_url
        return "https://api.minimax.io/v1"
    return "https://api.openai.com/v1"


def _resolve_api_key(provider: str, key: str | None) -> str:
    if key:
        return key
    if provider == "openai":
        env_key = os.environ.get("OPENAI_API_KEY")
        if env_key:
            return env_key
        raise ValueError("Missing OpenAI API key: pass --key or set OPENAI_API_KEY")
    if provider == "minimax":
        env_key = os.environ.get("MINIMAX_API_KEY")
        if env_key:
            return env_key
        raise ValueError("Missing MiniMax API key: pass --key or set MINIMAX_API_KEY")
    return ""


def main() -> None:
    parser = argparse.ArgumentParser(description="skill-audit: automated red-team auditor for SKILL.md")
    parser.add_argument("--file", required=True, help="Path to the SKILL.md file to evaluate")
    parser.add_argument(
        "--provider",
        choices=["openai", "ollama", "minimax"],
        default="ollama",
        help="ollama (default) / openai / minimax",
    )
    parser.add_argument("--model", required=True, help="Model name, e.g. llama3:8b or gpt-4o")
    parser.add_argument("--key", help="API key (required for OpenAI/MiniMax; optional for Ollama)")
    parser.add_argument(
        "--url",
        help=(
            "Custom API base URL (Ollama default http://localhost:11434/v1; "
            "MiniMax default https://api.minimax.io/v1)"
        ),
    )
    parser.add_argument(
        "--threshold",
        type=int,
        default=80,
        help="Pass threshold (0-100), default 80. Exit 1 if below.",
    )
    args = parser.parse_args()

    threshold = max(0, min(100, int(args.threshold)))
    base_url = _build_default_base_url(args.provider, args.url)
    created_at = datetime.now()
    report_path = f"report_{created_at.strftime('%m%d_%H%M')}.html"

    try:
        api_key = _resolve_api_key(args.provider, args.key)
        client = OpenAICompatClient(base_url=base_url, api_key=api_key, timeout_s=90)

        with open(args.file, "r", encoding="utf-8") as f:
            skill_md = f.read()

        cases = generate_attack_cases(client, model=args.model, skill_md=skill_md)
        if not cases:
            raise RuntimeError("No attack cases were generated (check that the model returned valid JSON).")
        results: list[CaseResult] = []

        for i, case in enumerate(cases, start=1):
            print(f"[{i}/{len(cases)}] Case ({case.impact.upper()})...")
            ai_response = run_skill_response(client, model=args.model, skill_md=skill_md, case=case)
            judge = judge_case(
                client,
                model=args.model,
                skill_md=skill_md,
                user_input=case.user_input,
                ai_response=ai_response,
            )
            results.append(CaseResult(case=case, ai_response=ai_response, judge=judge))

        avg_score = sum(r.judge.score for r in results) / max(1, len(results))
        html_report = render_html_report(
            skill_path=args.file,
            provider=args.provider,
            model=args.model,
            threshold=threshold,
            avg_score=avg_score,
            results=results,
            created_at=created_at,
        )
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(html_report)

        if avg_score < threshold:
            print(f"❌ Evaluation failed ({avg_score:.1f}/100). Report: {report_path}")
            raise SystemExit(1)
        print(f"✅ Evaluation passed ({avg_score:.1f}/100). Report: {report_path}")
        raise SystemExit(0)
    except SystemExit:
        raise
    except (FileNotFoundError, PermissionError) as e:
        print(f"Cannot read file: {e}")
        raise SystemExit(2)
    except ValueError as e:
        print(f"Argument error: {e}")
        raise SystemExit(2)
    except Exception as e:
        print(f"Run failed: {e}")
        if args.provider == "ollama":
            print(f"(Make sure Ollama is running and reachable at {base_url}.)")
        elif args.provider == "minimax":
            msg = str(e).lower()
            if "insufficient balance" in msg or "insufficient_balance" in msg or "(1008)" in msg:
                print(
                    "(MiniMax returned insufficient balance: your account quota is insufficient. "
                    "Top up or increase quota in the MiniMax console and retry.)"
                )
            elif "http 429" in msg or "too many requests" in msg:
                print("(MiniMax returned 429: rate limited. Retry later or reduce request rate.)")
            else:
                print(
                    "(Check that your MiniMax API key is correct. If you are in mainland China, try "
                    "--url https://api.minimaxi.com/v1; the international default is https://api.minimax.io/v1.)"
                )
        else:
            print(f"(Check that your API key and base_url are configured correctly: {base_url}.)")
        raise SystemExit(2)
