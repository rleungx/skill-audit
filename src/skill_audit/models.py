from __future__ import annotations

from dataclasses import dataclass, field

from .lint import LintFinding


@dataclass(frozen=True)
class AttackTurn:
    user_input: str


@dataclass(frozen=True)
class AttackCase:
    scenario: str
    turns: list[AttackTurn]
    risk_category: str
    impact: str = "medium"


@dataclass(frozen=True)
class RubricItem:
    rule: str
    level: str = "required"


@dataclass(frozen=True)
class ChecklistResult:
    rule: str
    level: str
    status: str


@dataclass(frozen=True)
class TraceInfo:
    attempted_tool_use: bool = False
    dangerous_intent: bool = False


@dataclass(frozen=True)
class JudgeResult:
    violation: bool
    blocking_failure: bool
    reason: str
    fix_suggestion: str
    checklist: list[ChecklistResult]
    detector_hits: list[str]
    trace: TraceInfo = field(default_factory=TraceInfo)


@dataclass(frozen=True)
class CaseResult:
    case: AttackCase
    ai_responses: list[str]
    judge: JudgeResult


@dataclass(frozen=True)
class DimensionScore:
    name: str
    passed: int
    total: int
    score: float


@dataclass(frozen=True)
class AuditSummary:
    passed: bool
    benchmark_score: float
    case_count: int
    violation_count: int
    blocking_failure_count: int
    matrix: list[DimensionScore]
    lint_findings: list[LintFinding] = field(default_factory=list)
    lint_blocking_count: int = 0
