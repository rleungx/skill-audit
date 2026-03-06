// skill-audit report renderer (TypeScript-authored, runtime-safe JS)
(() => {
  const REPORT_DATA_ID = "skill-audit-report-data";
  const APP_ID = "skill-audit-report-app";

  function injectStyles() {
    const style = document.createElement("style");
    style.textContent = `
      :root {
        --bg: #f4f5f7;
        --panel: #ffffff;
        --panel-muted: #f8f9fb;
        --text: #111827;
        --muted: #6b7280;
        --line: #e5e7eb;
        --line-strong: #d1d5db;
        --accent: #2563eb;
        --accent-soft: #eff6ff;
        --ok: #15803d;
        --ok-soft: #f0fdf4;
        --warn: #b45309;
        --warn-soft: #fffbeb;
        --bad: #b91c1c;
        --bad-soft: #fef2f2;
        --mono: "SFMono-Regular", Menlo, Consolas, "Liberation Mono", monospace;
        --sans: "SF Pro Text", "Segoe UI Variable", "Segoe UI", system-ui, sans-serif;
      }
      * { box-sizing: border-box; }
      html { scroll-behavior: smooth; }
      body {
        margin: 0;
        background: var(--bg);
        color: var(--text);
        font-family: var(--sans);
      }
      a { color: var(--accent); text-decoration: none; }
      button {
        font: inherit;
      }
      .wrap {
        width: min(1120px, calc(100vw - 32px));
        margin: 0 auto;
        padding: 24px 0 48px;
      }
      .panel {
        background: var(--panel);
        border: 1px solid var(--line);
        border-radius: 16px;
      }
      .header {
        padding: 24px;
      }
      .eyebrow {
        font-family: var(--mono);
        font-size: 11px;
        line-height: 1;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        color: var(--muted);
      }
      .title-row {
        display: flex;
        justify-content: space-between;
        gap: 16px;
        align-items: flex-start;
        flex-wrap: wrap;
        margin-top: 10px;
      }
      h1 {
        margin: 0;
        font-size: 30px;
        line-height: 1.1;
        letter-spacing: -0.03em;
      }
      .subtitle {
        margin: 10px 0 0;
        max-width: 60ch;
        color: var(--muted);
        line-height: 1.6;
      }
      .status-row,
      .meta-row,
      .toolbar,
      .toolbar-group,
      .case-summary-meta,
      .section-tools {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
      }
      .status-row {
        justify-content: flex-end;
      }
      .score-row {
        display: grid;
        grid-template-columns: 220px minmax(0, 1fr);
        gap: 20px;
        margin-top: 20px;
        align-items: start;
      }
      .score-box {
        padding: 18px;
        border: 1px solid var(--line);
        border-radius: 14px;
        background: var(--panel-muted);
      }
      .score-value {
        font-size: 40px;
        line-height: 1;
        letter-spacing: -0.05em;
        font-weight: 700;
      }
      .score-label {
        margin-top: 6px;
        font-family: var(--mono);
        font-size: 11px;
        text-transform: uppercase;
        letter-spacing: 0.12em;
        color: var(--muted);
      }
      .score-copy {
        padding-top: 4px;
      }
      .score-copy p {
        margin: 0 0 12px;
        color: var(--muted);
        line-height: 1.6;
      }
      .badge {
        display: inline-flex;
        align-items: center;
        min-height: 28px;
        padding: 6px 10px;
        border: 1px solid var(--line);
        border-radius: 999px;
        background: #fff;
        color: var(--muted);
        font-size: 12px;
        line-height: 1;
        white-space: nowrap;
      }
      .badge.pass {
        color: var(--ok);
        background: var(--ok-soft);
        border-color: #cce7d3;
      }
      .badge.fail {
        color: var(--bad);
        background: var(--bad-soft);
        border-color: #f2c9c9;
      }
      .badge.warn {
        color: var(--warn);
        background: var(--warn-soft);
        border-color: #efd8a7;
      }
      .badge.info {
        color: var(--accent);
        background: var(--accent-soft);
        border-color: #cfe0ff;
      }
      .meta-grid,
      .metric-grid,
      .two-col,
      .stat-grid {
        display: grid;
        gap: 12px;
      }
      .meta-grid {
        grid-template-columns: repeat(4, minmax(0, 1fr));
        margin-top: 20px;
      }
      .meta-card,
      .metric-card,
      .content-card,
      .stat-card {
        border: 1px solid var(--line);
        border-radius: 14px;
        background: #fff;
      }
      .meta-card,
      .metric-card,
      .content-card,
      .stat-card,
      .case-card-body {
        padding: 14px;
      }
      .meta-card .label,
      .metric-card .label,
      .stat-card .label {
        font-family: var(--mono);
        font-size: 11px;
        text-transform: uppercase;
        letter-spacing: 0.12em;
        color: var(--muted);
      }
      .meta-card .value {
        margin-top: 8px;
        line-height: 1.5;
        word-break: break-word;
      }
      .metric-grid {
        grid-template-columns: repeat(6, minmax(0, 1fr));
        margin-top: 16px;
      }
      .metric-card .value {
        margin-top: 10px;
        font-size: 28px;
        line-height: 1;
        letter-spacing: -0.04em;
      }
      .metric-card .hint {
        margin-top: 8px;
        color: var(--muted);
        font-size: 13px;
        line-height: 1.5;
      }
      .section {
        margin-top: 16px;
        padding: 20px;
      }
      .section-head {
        display: flex;
        justify-content: space-between;
        gap: 16px;
        align-items: flex-start;
        flex-wrap: wrap;
        margin-bottom: 14px;
      }
      .section-head h2 {
        margin: 8px 0 0;
        font-size: 22px;
        line-height: 1.2;
        letter-spacing: -0.02em;
      }
      .section-head p {
        margin: 8px 0 0;
        max-width: 64ch;
        color: var(--muted);
        line-height: 1.6;
      }
      .toggle {
        border: 1px solid var(--line);
        border-radius: 14px;
        background: #fff;
        overflow: hidden;
      }
      .toggle > summary,
      .case-card > summary,
      .fold > summary {
        list-style: none;
        cursor: pointer;
      }
      .toggle > summary::-webkit-details-marker,
      .case-card > summary::-webkit-details-marker,
      .fold > summary::-webkit-details-marker {
        display: none;
      }
      .toggle > summary {
        display: flex;
        justify-content: space-between;
        gap: 12px;
        align-items: center;
        padding: 14px 16px;
      }
      .toggle-title {
        font-weight: 600;
      }
      .toggle-body {
        padding: 0 16px 16px;
      }
      .rule-list,
      .case-list,
      .checklist {
        display: grid;
        gap: 12px;
      }
      .rule-item,
      .check-item {
        border: 1px solid var(--line);
        border-radius: 12px;
        background: var(--panel-muted);
        padding: 12px;
      }
      .rule-item-head {
        display: flex;
        justify-content: space-between;
        gap: 12px;
        align-items: center;
        flex-wrap: wrap;
      }
      .rule-item h3 {
        margin: 0;
        font-size: 15px;
      }
      .code,
      pre {
        margin: 10px 0 0;
        padding: 12px;
        border: 1px solid var(--line);
        border-radius: 10px;
        background: #fff;
        color: var(--text);
        white-space: pre-wrap;
        word-break: break-word;
        font-family: var(--mono);
        font-size: 12px;
        line-height: 1.65;
      }
      .rule-note,
      .content-card p,
      .check-note,
      .empty,
      .footer {
        color: var(--muted);
        line-height: 1.6;
      }
      .toolbar {
        justify-content: space-between;
        margin-bottom: 14px;
      }
      .toolbar-button {
        appearance: none;
        border: 1px solid var(--line);
        border-radius: 999px;
        background: #fff;
        color: var(--muted);
        padding: 8px 12px;
        font-size: 12px;
        line-height: 1;
        cursor: pointer;
      }
      .toolbar-button.active {
        color: var(--text);
        border-color: var(--line-strong);
        background: var(--panel-muted);
      }
      .case-card {
        border: 1px solid var(--line);
        border-radius: 14px;
        background: #fff;
        overflow: hidden;
      }
      .case-card[hidden] {
        display: none;
      }
      .case-card > summary {
        padding: 14px 16px;
      }
      .case-summary {
        display: grid;
        grid-template-columns: minmax(0, 1fr) auto;
        gap: 16px;
        align-items: start;
      }
      .case-title {
        margin: 8px 0 0;
        font-size: 18px;
        line-height: 1.35;
      }
      .case-preview {
        margin: 8px 0 0;
        color: var(--muted);
        line-height: 1.6;
      }
      .case-card-body {
        border-top: 1px solid var(--line);
        background: var(--panel-muted);
      }
      .two-col {
        grid-template-columns: repeat(2, minmax(0, 1fr));
      }
      .content-card h4 {
        margin: 0;
        font-size: 14px;
      }
      .content-card .code {
        margin-top: 10px;
      }
      .stat-grid {
        grid-template-columns: repeat(6, minmax(0, 1fr));
        margin-top: 12px;
      }
      .stat-card .value {
        margin-top: 8px;
        font-size: 22px;
        line-height: 1;
        letter-spacing: -0.04em;
      }
      .fold {
        margin-top: 12px;
        border: 1px solid var(--line);
        border-radius: 12px;
        background: #fff;
        overflow: hidden;
      }
      .fold > summary {
        display: flex;
        justify-content: space-between;
        gap: 12px;
        align-items: center;
        padding: 12px 14px;
        font-size: 14px;
        font-weight: 600;
      }
      .fold-body {
        padding: 0 14px 14px;
      }
      .check-item {
        background: var(--panel-muted);
      }
      .check-head {
        display: flex;
        gap: 8px;
        flex-wrap: wrap;
        align-items: center;
      }
      .check-note {
        margin-top: 8px;
      }
      .footer {
        margin-top: 16px;
        padding: 16px 20px;
      }
      .error {
        margin-top: 16px;
        padding: 14px 16px;
        border: 1px solid #f2c9c9;
        border-radius: 14px;
        background: var(--bad-soft);
        color: var(--bad);
      }
      @media (max-width: 980px) {
        .score-row,
        .meta-grid,
        .metric-grid,
        .stat-grid,
        .two-col {
          grid-template-columns: 1fr 1fr;
        }
      }
      @media (max-width: 720px) {
        .wrap {
          width: min(100vw - 20px, 1120px);
          padding-top: 16px;
        }
        .header,
        .section {
          padding: 16px;
        }
        .score-row,
        .meta-grid,
        .metric-grid,
        .stat-grid,
        .two-col,
        .case-summary {
          grid-template-columns: 1fr;
        }
        .status-row,
        .case-summary-meta {
          justify-content: flex-start;
        }
      }
    `.trim();
    document.head.appendChild(style);
  }

  function el(tag, attrs, children) {
    const node = document.createElement(tag);
    if (attrs) {
      for (const [k, v] of Object.entries(attrs)) {
        if (v === undefined || v === null) continue;
        if (k === "className") node.className = String(v);
        else if (k === "text") node.textContent = String(v);
        else node.setAttribute(k, String(v));
      }
    }
    if (children) {
      for (const child of children) {
        if (child === undefined || child === null) continue;
        if (typeof child === "string") node.appendChild(document.createTextNode(child));
        else node.appendChild(child);
      }
    }
    return node;
  }

  function readReportData() {
    const dataEl = document.getElementById(REPORT_DATA_ID);
    if (!dataEl) throw new Error(`Missing report data element #${REPORT_DATA_ID}`);
    const raw = dataEl.textContent || "";
    const data = JSON.parse(raw);
    if (!data || typeof data !== "object") throw new Error("Invalid report data");
    return data;
  }

  function clampImpact(impact) {
    const value = String(impact || "medium").trim().toLowerCase();
    return value === "critical" || value === "high" || value === "medium" || value === "low" ? value : "medium";
  }

  function clampChecklistStatus(status) {
    const value = String(status || "not_applicable").trim().toLowerCase();
    return value === "pass" || value === "fail" || value === "not_applicable" ? value : "not_applicable";
  }

  function clampRuleLevel(level) {
    const value = String(level || "required").trim().toLowerCase();
    return value === "hard" || value === "required" || value === "advisory" ? value : "required";
  }

  function formatPercent(value) {
    return typeof value === "number" && Number.isFinite(value) ? `${value.toFixed(1)}%` : "N/A";
  }

  function formatScore(value) {
    return typeof value === "number" && Number.isFinite(value) ? value.toFixed(1) : "N/A";
  }

  function formatCount(value) {
    const n = Number(value || 0);
    return Number.isFinite(n) ? String(n) : "0";
  }

  function shortText(value, limit) {
    const text = String(value || "").trim().replace(/\s+/g, " ");
    if (!text) return "";
    return text.length <= limit ? text : `${text.slice(0, Math.max(0, limit - 1))}...`;
  }

  function summarizeImpacts(results) {
    const counts = { critical: 0, high: 0, medium: 0, low: 0 };
    for (const item of results) {
      counts[clampImpact(item && item.impact)] += 1;
    }
    return counts;
  }

  function summarizeRuleLevels(items) {
    const counts = { hard: 0, required: 0, advisory: 0 };
    for (const item of items) {
      counts[clampRuleLevel(item && item.level)] += 1;
    }
    return counts;
  }

  function summarizeChecklist(items) {
    const counts = { pass: 0, fail: 0, not_applicable: 0 };
    for (const item of items) {
      counts[clampChecklistStatus(item && item.status)] += 1;
    }
    return counts;
  }

  function toneClassForImpact(impact) {
    if (impact === "critical") return "fail";
    if (impact === "high") return "warn";
    if (impact === "medium") return "warn";
    return "info";
  }

  function toneClassForRule(level) {
    if (level === "hard") return "fail";
    if (level === "required") return "warn";
    return "info";
  }

  function makeBadge(text, tone) {
    return el("span", { className: `badge ${tone || ""}`.trim(), text });
  }

  function makeMetaCard(label, value) {
    return el("div", { className: "meta-card" }, [
      el("div", { className: "label", text: label }),
      el("div", { className: "value", text: String(value || "") }),
    ]);
  }

  function makeMetricCard(label, value, hint, tone) {
    return el("div", { className: "metric-card" }, [
      el("div", { className: "label", text: label }),
      el("div", { className: "value", text: value }),
      hint ? el("div", { className: "hint", text: hint }) : null,
      tone ? el("div", { className: "section-tools" }, [makeBadge(tone.toUpperCase(), tone)]) : null,
    ]);
  }

  function makeStatCard(label, value) {
    return el("div", { className: "stat-card" }, [
      el("div", { className: "label", text: label }),
      el("div", { className: "value", text: value }),
    ]);
  }

  function makeFold(title, body, metaText) {
    const summaryChildren = [el("span", { text: title })];
    if (metaText) summaryChildren.push(makeBadge(metaText, "info"));
    return el("details", { className: "fold" }, [
      el("summary", null, summaryChildren),
      el("div", { className: "fold-body" }, [body]),
    ]);
  }

  function wireCaseControls(app) {
    const filterButtons = Array.from(app.querySelectorAll("[data-case-filter]"));
    const caseCards = Array.from(app.querySelectorAll("details.case-card"));

    function matchesFilter(node, filter) {
      if (filter === "all") return true;
      if (filter === "violations") return node.getAttribute("data-violation") === "1";
      if (filter === "blocking") return node.getAttribute("data-blocking") === "1";
      if (filter === "critical") return node.getAttribute("data-impact") === "critical";
      return true;
    }

    function applyFilter(filter) {
      for (const button of filterButtons) {
        button.classList.toggle("active", button.getAttribute("data-case-filter") === filter);
      }
      for (const node of caseCards) {
        node.hidden = !matchesFilter(node, filter);
      }
    }

    for (const button of filterButtons) {
      button.addEventListener("click", () => applyFilter(button.getAttribute("data-case-filter") || "all"));
    }

    applyFilter("all");
  }

  function render(app, report) {
    const summary = report.summary && typeof report.summary === "object" ? report.summary : {};
    const rubric = Array.isArray(report.rubric) ? report.rubric : [];
    const results = Array.isArray(report.results) ? report.results : [];

    const benchmarkScore = Number(summary.benchmarkScore || 0);
    const pass = !!summary.passed;
    const threshold = Number(summary.passThreshold || 0);
    const violations = Number(summary.violationCount || 0);
    const blockingFailureCount = Number(summary.blockingFailureCount || 0);
    const hardFailRules = Number(summary.hardFailRules || 0);
    const caseCount = Number(summary.caseCount || results.length || 0);
    const scoredCaseCount = Number(summary.scoredCaseCount || 0);
    const mode = String(summary.mode || "random");
    const referenceReady = !!summary.referenceReady;
    const modeLabel = mode === "snapshot" ? "Snapshot" : "Random";
    const impactCounts = summarizeImpacts(results);
    const ruleLevelCounts = summarizeRuleLevels(rubric);

    const header = el("section", { className: "panel header", id: "overview" }, [
      el("div", { className: "eyebrow", text: "skill-audit report" }),
      el("div", { className: "title-row" }, [
        el("div", null, [
          el("h1", { text: "Audit Summary" }),
          el("p", {
            className: "subtitle",
            text: "Prioritized for reading first: top-level benchmark state, high-risk cases, then supporting detail.",
          }),
        ]),
        el("div", { className: "status-row" }, [
          makeBadge(pass ? "PASS" : "FAIL", pass ? "pass" : "fail"),
          makeBadge(modeLabel, referenceReady ? "info" : "warn"),
          makeBadge(`Threshold ${formatCount(threshold)}`, "info"),
        ]),
      ]),
      el("div", { className: "score-row" }, [
        el("div", { className: "score-box" }, [
          el("div", { className: "score-value", text: `${formatScore(benchmarkScore)}/100` }),
          el("div", { className: "score-label", text: referenceReady ? "benchmark score" : "run score" }),
        ]),
        el("div", { className: "score-copy" }, [
          el("p", {
            text: referenceReady
              ? "This run used a saved snapshot. The score is suitable for comparison over time."
              : "This run used fresh cases. Treat the score as exploratory signal rather than a stable benchmark.",
          }),
          el("div", { className: "status-row" }, [
            makeBadge(`Violations ${formatCount(violations)}/${formatCount(caseCount)}`, violations ? "fail" : "pass"),
            makeBadge(`Blocking failures ${formatCount(blockingFailureCount)}`, blockingFailureCount ? "fail" : "pass"),
            makeBadge(`Hard fail rules ${formatCount(hardFailRules)}`, hardFailRules ? "fail" : "pass"),
            makeBadge(`Scored ${formatCount(scoredCaseCount)}/${formatCount(caseCount)}`, "info"),
          ]),
        ]),
      ]),
      el("div", { className: "meta-grid" }, [
        makeMetaCard("Created at", report.createdAt || ""),
        makeMetaCard("Skill file", report.skillPath || ""),
        makeMetaCard("Provider", report.provider || ""),
        makeMetaCard("Model", report.model || ""),
      ]),
      el("div", { className: "metric-grid" }, [
        makeMetricCard("Critical cases", formatCount(impactCounts.critical), "Highest-risk scenarios in this run.", impactCounts.critical ? "fail" : "info"),
        makeMetricCard("High impact", formatCount(impactCounts.high), "Important but non-critical scenarios.", impactCounts.high ? "warn" : "info"),
        makeMetricCard("Rule pass rate", formatPercent(summary.rulePassRate), "Across all applicable checks.", pass ? "pass" : "warn"),
        makeMetricCard("Critical pass rate", formatPercent(summary.criticalCasePassRate), "Critical case outcomes only.", pass ? "pass" : "warn"),
        makeMetricCard("Rubric hard rules", formatCount(ruleLevelCounts.hard), "Most rigid rules extracted from the skill.", ruleLevelCounts.hard ? "fail" : "info"),
        makeMetricCard("N/A rate", formatPercent(summary.notApplicableRate), "High values can indicate overly broad rubric extraction.", "info"),
      ]),
    ]);

    const rubricList = el("div", { className: "rule-list" });
    if (rubric.length === 0) {
      rubricList.appendChild(el("div", { className: "empty", text: "No rubric extracted." }));
    } else {
      for (let i = 0; i < rubric.length; i += 1) {
        const item = rubric[i] || {};
        const level = clampRuleLevel(item.level);
        rubricList.appendChild(
          el("article", { className: "rule-item" }, [
            el("div", { className: "rule-item-head" }, [
              el("h3", { text: `Rule ${i + 1}` }),
              makeBadge(level.toUpperCase(), toneClassForRule(level)),
            ]),
            el("pre", { text: String(item.rule || "") }),
            String(item.why || "").trim() ? el("div", { className: "rule-note", text: String(item.why || "").trim() }) : null,
          ]),
        );
      }
    }

    const rubricSection = el("section", { className: "panel section", id: "rubric" }, [
      el("div", { className: "section-head" }, [
        el("div", null, [
          el("div", { className: "eyebrow", text: "rubric" }),
          el("h2", { text: "Judge Rules" }),
          el("p", { text: "Supporting detail. Collapsed by default because the rules are usually referenced after reading the case outcomes." }),
        ]),
        el("div", { className: "section-tools" }, [
          makeBadge(`Hard ${formatCount(ruleLevelCounts.hard)}`, "fail"),
          makeBadge(`Required ${formatCount(ruleLevelCounts.required)}`, "warn"),
          makeBadge(`Advisory ${formatCount(ruleLevelCounts.advisory)}`, "info"),
        ]),
      ]),
      el("details", { className: "toggle" }, [
        el("summary", null, [
          el("div", { className: "toggle-title", text: `Show rubric (${formatCount(rubric.length)} rules)` }),
          makeBadge("Collapsed by default", "info"),
        ]),
        el("div", { className: "toggle-body" }, [rubricList]),
      ]),
    ]);

    const casesSection = el("section", { className: "panel section", id: "cases" }, [
      el("div", { className: "section-head" }, [
        el("div", null, [
          el("div", { className: "eyebrow", text: "cases" }),
          el("h2", { text: "Case Results" }),
          el("p", { text: "Primary reading surface. Case summaries stay visible; lower-priority material is folded inside each case." }),
        ]),
      ]),
    ]);

    const toolbar = el("div", { className: "toolbar" }, [
      el("div", { className: "toolbar-group" }, [
        el("button", { className: "toolbar-button active", "data-case-filter": "all", text: `All ${formatCount(results.length)}` }),
        el("button", { className: "toolbar-button", "data-case-filter": "violations", text: `Violations ${formatCount(violations)}` }),
        el("button", { className: "toolbar-button", "data-case-filter": "blocking", text: `Blocking ${formatCount(blockingFailureCount)}` }),
        el("button", { className: "toolbar-button", "data-case-filter": "critical", text: `Critical ${formatCount(impactCounts.critical)}` }),
      ]),
    ]);
    casesSection.appendChild(toolbar);

    const caseList = el("div", { className: "case-list" });
    if (results.length === 0) {
      caseList.appendChild(el("div", { className: "empty", text: "No cases." }));
    } else {
      let openedAny = false;
      for (let i = 0; i < results.length; i += 1) {
        const item = results[i] || {};
        const impact = clampImpact(item.impact);
        const violation = !!item.violation;
        const blockingFailure = !!item.blockingFailure;
        const checklist = Array.isArray(item.checklist) ? item.checklist : [];
        const checklistCounts = summarizeChecklist(checklist);
        const scenario = String(item.scenario || "").trim();
        const userInput = String(item.userInput || "").trim();
        const aiResponse = String(item.aiResponse || "").trim();
        const reason = String(item.reason || "").trim();
        const fixSuggestion = String(item.fixSuggestion || "").trim();
        const shouldOpen = !openedAny && (blockingFailure || violation || i === 0);
        if (shouldOpen) openedAny = true;

        const caseAttrs = {
          className: "case-card",
          "data-impact": impact,
          "data-violation": violation ? "1" : "0",
          "data-blocking": blockingFailure ? "1" : "0",
        };
        if (shouldOpen) caseAttrs.open = "";

        const caseBodyChildren = [
          el("div", { className: "two-col" }, [
            el("section", { className: "content-card" }, [
              el("h4", { text: "Scenario" }),
              el("div", { className: "code", text: scenario || "N/A" }),
            ]),
            el("section", { className: "content-card" }, [
              el("h4", { text: "User Input" }),
              el("div", { className: "code", text: userInput || "N/A" }),
            ]),
          ]),
          el("div", { className: "stat-grid" }, [
            makeStatCard("Score", formatScore(item.benchmarkScore)),
            makeStatCard("Applicable", formatCount(item.applicableRules)),
            makeStatCard("Passed", formatCount(item.passedRules)),
            makeStatCard("Failed", formatCount(item.failedRules)),
            makeStatCard("Hard fail", formatCount(item.hardFailRules)),
            makeStatCard("N/A", formatCount(item.notApplicableRules)),
          ]),
        ];

        if (aiResponse) {
          caseBodyChildren.push(makeFold("AI Response", el("pre", { text: aiResponse }), shortText(aiResponse, 48)));
        }
        if (reason) {
          caseBodyChildren.push(makeFold("Judge Reason", el("pre", { text: reason }), null));
        }
        if (fixSuggestion) {
          caseBodyChildren.push(makeFold("Fix Suggestion", el("pre", { text: fixSuggestion }), null));
        }
        if (checklist.length > 0) {
          const checklistList = el("div", { className: "checklist" });
          for (let j = 0; j < checklist.length; j += 1) {
            const check = checklist[j] || {};
            const status = clampChecklistStatus(check.status);
            const level = clampRuleLevel(check.level);
            checklistList.appendChild(
              el("article", { className: "check-item" }, [
                el("div", { className: "check-head" }, [
                  makeBadge(status.replace("_", " ").toUpperCase(), status === "pass" ? "pass" : status === "fail" ? "fail" : "warn"),
                  makeBadge(level.toUpperCase(), toneClassForRule(level)),
                ]),
                el("div", { className: "code", text: String(check.rule || "") }),
                String(check.notes || "").trim() ? el("div", { className: "check-note", text: String(check.notes || "").trim() }) : null,
              ]),
            );
          }
          caseBodyChildren.push(
            makeFold(
              "Checklist",
              checklistList,
              `${checklistCounts.fail} fail / ${checklistCounts.pass} pass / ${checklistCounts.not_applicable} n/a`,
            ),
          );
        }

        caseList.appendChild(
          el("details", caseAttrs, [
            el("summary", null, [
              el("div", { className: "case-summary" }, [
                el("div", null, [
                  el("div", { className: "eyebrow", text: `case ${i + 1}` }),
                  el("div", { className: "case-title", text: scenario || `Case ${i + 1}` }),
                  el("div", { className: "case-preview", text: shortText(userInput, 180) || "No user input preview." }),
                ]),
                el("div", { className: "case-summary-meta" }, [
                  makeBadge(impact.toUpperCase(), toneClassForImpact(impact)),
                  makeBadge(`Score ${formatScore(item.benchmarkScore)}`, "info"),
                  makeBadge(violation ? "Violation" : "No violation", violation ? "fail" : "pass"),
                  blockingFailure ? makeBadge("Blocking", "fail") : null,
                ]),
              ]),
            ]),
            el("div", { className: "case-card-body" }, caseBodyChildren),
          ]),
        );
      }
    }
    casesSection.appendChild(caseList);

    const footer = el("section", { className: "panel footer" }, [
      el("div", {
        text: referenceReady
          ? "Snapshot run: suitable for benchmark tracking."
          : "Random run: suitable for exploration, but weaker for comparison over time.",
      }),
    ]);

    app.appendChild(el("div", { className: "wrap" }, [header, casesSection, rubricSection, footer]));
    wireCaseControls(app);
  }

  function main() {
    injectStyles();
    const app = document.getElementById(APP_ID);
    if (!app) throw new Error(`Missing app root #${APP_ID}`);
    render(app, readReportData());
  }

  try {
    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", main);
    else main();
  } catch (e) {
    injectStyles();
    const message = e instanceof Error ? e.message : String(e);
    const root = document.getElementById(APP_ID) || document.body;
    root.appendChild(el("div", { className: "wrap" }, [el("div", { className: "error", text: `Report render error: ${message}` })]));
  }
})();
