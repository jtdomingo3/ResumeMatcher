"""
Interactive Skills Analysis and Evidence Chip Component.
"""

from nicegui import ui
from typing import Dict, List, Any


def render_skills_chips(skills_data: Dict[str, Any]):
    """
    Renders categorized skill chips: Matched Required, Matched Preferred, and Missing.
    Includes contextual evidence snippets.
    """
    matched_req = skills_data.get("matched_required", [])
    missing_req = skills_data.get("missing_required", [])
    matched_pref = skills_data.get("matched_preferred", [])
    missing_pref = skills_data.get("missing_preferred", [])
    evidence = skills_data.get("evidence_by_skill", {})

    with ui.card().classes("glass-card p-6 w-full"):
        ui.label("Skills Compatibility Matrix").classes("brand-font text-lg font-bold text-white mb-4")

        # 1. Matched Required
        with ui.column().classes("w-full gap-2 mb-4"):
            with ui.row().classes("items-center gap-2"):
                ui.icon("check_circle", size="18px").classes("text-emerald-400")
                ui.label(f"Matched Required Skills ({len(matched_req)})").classes("text-sm font-semibold text-emerald-400")

            if matched_req:
                with ui.row().classes("flex-wrap gap-2"):
                    for skill in matched_req:
                        snippet = evidence.get(skill, "Verified in resume text.")
                        with ui.element("div").classes("chip-matched cursor-pointer").tooltip(f"Evidence: {snippet}"):
                            ui.label(skill)
            else:
                ui.label("No required skills matched.").classes("text-xs text-slate-500 italic")

        # 2. Matched Preferred (Bonus)
        if matched_pref:
            with ui.column().classes("w-full gap-2 mb-4"):
                with ui.row().classes("items-center gap-2"):
                    ui.icon("stars", size="18px").classes("text-sky-400")
                    ui.label(f"Bonus / Preferred Skills ({len(matched_pref)})").classes("text-sm font-semibold text-sky-400")

                with ui.row().classes("flex-wrap gap-2"):
                    for skill in matched_pref:
                        snippet = evidence.get(skill, "Bonus skill verified.")
                        with ui.element("div").classes("chip-preferred cursor-pointer").tooltip(f"Evidence: {snippet}"):
                            ui.label(skill)

        # 3. Missing Required (Actionable Gaps)
        with ui.column().classes("w-full gap-2"):
            with ui.row().classes("items-center gap-2"):
                ui.icon("cancel", size="18px").classes("text-rose-400")
                ui.label(f"Critical Missing Skills ({len(missing_req)})").classes("text-sm font-semibold text-rose-400")

            if missing_req:
                with ui.row().classes("flex-wrap gap-2"):
                    for skill in missing_req:
                        with ui.element("div").classes("chip-missing"):
                            ui.label(skill)
            else:
                ui.label("Great job! Zero missing required qualifications.").classes("text-xs text-emerald-400 font-medium")
