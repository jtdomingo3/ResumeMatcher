"""
ATS Compliance and Formatting Audit Card Component.
"""

from nicegui import ui
from typing import Dict, Any


def render_ats_card(ats_report: Dict[str, Any]):
    """
    Renders the ATS scorecard, formatting pass/fail checks, and section headings audit.
    """
    score = ats_report.get("score", 0)
    verdict = ats_report.get("verdict", "PASS")
    issues = ats_report.get("format_issues", [])
    found = ats_report.get("found_headings", [])
    missing = ats_report.get("missing_headings", [])
    has_contact = ats_report.get("has_contact_info", True)
    words = ats_report.get("word_count", 0)

    verdict_colors = {
        "PASS": "text-emerald-400 bg-emerald-500/10 border-emerald-500/30",
        "CAUTION": "text-amber-400 bg-amber-500/10 border-amber-500/30",
        "REVISE": "text-rose-400 bg-rose-500/10 border-rose-500/30",
    }
    badge_style = verdict_colors.get(verdict, verdict_colors["CAUTION"])

    with ui.card().classes("glass-card p-6 w-full"):
        with ui.row().classes("w-full justify-between items-center mb-4"):
            with ui.row().classes("items-center gap-2"):
                ui.icon("fact_check", size="22px").classes("text-indigo-400")
                ui.label("ATS Compliance & Parser Audit").classes("brand-font text-lg font-bold text-white")
            with ui.row().classes("items-center gap-3"):
                ui.label(f"Score: {score}/100").classes("mono-font text-sm font-bold text-white")
                ui.label(verdict).classes(f"text-xs px-3 py-1 rounded-full font-bold border {badge_style}")

        # Metrics grid
        with ui.row().classes("w-full grid grid-cols-2 sm:grid-cols-4 gap-4 mb-4"):
            with ui.card().classes("bg-slate-900/60 p-3 rounded-xl border border-slate-800"):
                ui.label("Contact Info").classes("text-xs text-slate-400 font-medium")
                ui.label("Present" if has_contact else "Missing").classes(f"text-sm font-bold {'text-emerald-400' if has_contact else 'text-rose-400'}")

            with ui.card().classes("bg-slate-900/60 p-3 rounded-xl border border-slate-800"):
                ui.label("Word Count").classes("text-xs text-slate-400 font-medium")
                ui.label(f"{words} words").classes("text-sm font-bold text-white mono-font")

            with ui.card().classes("bg-slate-900/60 p-3 rounded-xl border border-slate-800"):
                ui.label("Headings Found").classes("text-xs text-slate-400 font-medium")
                ui.label(f"{len(found)} / {len(found) + len(missing)}").classes("text-sm font-bold text-indigo-300 mono-font")

            with ui.card().classes("bg-slate-900/60 p-3 rounded-xl border border-slate-800"):
                ui.label("Format Risks").classes("text-xs text-slate-400 font-medium")
                ui.label(f"{len(issues)} detected").classes(f"text-sm font-bold {'text-amber-400' if issues else 'text-emerald-400'}")

        # Format checklist issues if any
        if issues:
            with ui.column().classes("w-full gap-1 p-3 bg-amber-500/10 rounded-xl border border-amber-500/20 mb-3"):
                ui.label("ATS Warning Flags").classes("text-xs font-bold text-amber-400 uppercase tracking-wider")
                for issue in issues:
                    with ui.row().classes("items-center gap-1.5 text-xs text-amber-200"):
                        ui.icon("warning_amber", size="14px")
                        ui.label(issue)

        # Standard Sections Checklist
        with ui.row().classes("w-full flex-wrap gap-2 text-xs"):
            for h in found:
                with ui.element("span").classes("px-2.5 py-1 rounded bg-slate-800 text-slate-300 flex items-center gap-1"):
                    ui.icon("check", size="14px").classes("text-emerald-400")
                    ui.label(h.capitalize())
            for h in missing:
                with ui.element("span").classes("px-2.5 py-1 rounded bg-slate-800/50 text-slate-500 flex items-center gap-1"):
                    ui.icon("close", size="14px").classes("text-rose-400")
                    ui.label(f"Missing {h.capitalize()}")
