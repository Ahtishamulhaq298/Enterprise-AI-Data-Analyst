"""Automated report generation (Markdown + PDF)."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from app.core.config import settings


def build_markdown_report(title: str, dataset_name: str, profiling: dict | None,
                          automl: dict | None, explanation: dict | None,
                          narrative: str = "") -> str:
    lines = [f"# {title}", "",
             f"**Dataset:** {dataset_name}  ",
             f"**Generated:** {datetime.now():%Y-%m-%d %H:%M}  ",
             "", "---", ""]

    if narrative:
        lines += ["## 1. Executive Summary", "", narrative, ""]

    if profiling:
        shape = profiling.get("shape", {})
        lines += ["## 2. Dataset Overview", "",
                  f"- Rows: **{shape.get('rows')}**",
                  f"- Columns: **{shape.get('columns')}**",
                  f"- Duplicate rows: **{profiling.get('duplicate_rows')}**",
                  f"- Memory: **{profiling.get('memory_mb')} MB**", ""]
        issues = profiling.get("quality_issues", [])
        if issues:
            lines += ["### Data Quality Issues", "",
                      "| Column | Issue | Severity | Detail |", "|---|---|---|---|"]
            for i in issues[:20]:
                lines.append(f"| {i['column']} | {i['issue']} | {i['severity']} | {i['detail']} |")
            lines.append("")
        cols = profiling.get("columns", [])[:25]
        if cols:
            lines += ["### Column Summary", "",
                      "| Column | Type | Missing % | Unique |", "|---|---|---|---|"]
            for c in cols:
                lines.append(f"| {c['name']} | {c['dtype']} | {c['missing_pct']} | {c['unique']} |")
            lines.append("")

    if automl:
        best = automl.get("best_model", {})
        lines += ["## 3. Model Comparison", "",
                  f"- Task type: **{automl.get('task_type')}**",
                  f"- Target: **{automl.get('target_column')}**",
                  f"- Best model: **{best.get('name')}**", "",
                  "| Model | Key metrics | CV mean | CV std | Train (s) |", "|---|---|---|---|---|"]
        for row in automl.get("leaderboard", []):
            if row.get("status") != "success":
                lines.append(f"| {row['model']} | failed | - | - | - |")
                continue
            metrics = ", ".join(f"{k}={v}" for k, v in row["metrics"].items())
            lines.append(f"| {row['model']} | {metrics} | {row['cv_mean']} | "
                         f"{row['cv_std']} | {row['train_seconds']} |")
        lines.append("")

    if explanation and explanation.get("features"):
        lines += ["## 4. Explainability", "",
                  f"Method: **{explanation.get('method')}**", "",
                  "| Feature | Importance |", "|---|---|"]
        for f in explanation["features"]:
            lines.append(f"| {f['feature']} | {f['importance']} |")
        lines.append("")

    lines += ["---", "", "_Generated automatically by the Enterprise AI Data Analyst platform._"]
    return "\n".join(lines)


def save_markdown(markdown: str, filename: str) -> str:
    path = Path(settings.REPORT_DIR) / f"{filename}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(markdown, encoding="utf-8")
    return str(path)


def save_pdf(markdown: str, filename: str) -> str:
    from fpdf import FPDF

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Helvetica", size=10)
    for raw in markdown.split("\n"):
        line = raw.replace("**", "").replace("`", "")
        if line.startswith("# "):
            pdf.set_font("Helvetica", "B", 16); pdf.multi_cell(0, 8, line[2:]); pdf.ln(2)
        elif line.startswith("## "):
            pdf.set_font("Helvetica", "B", 13); pdf.multi_cell(0, 7, line[3:]); pdf.ln(1)
        elif line.startswith("### "):
            pdf.set_font("Helvetica", "B", 11); pdf.multi_cell(0, 6, line[4:])
        else:
            pdf.set_font("Helvetica", size=9)
            pdf.multi_cell(0, 5, line.encode("latin-1", "replace").decode("latin-1"))
    path = Path(settings.REPORT_DIR) / f"{filename}.pdf"
    path.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(path))
    return str(path)