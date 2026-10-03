"""
Visual Score Gauge and Dimension Breakdown Component.
"""

from nicegui import ui
from typing import Dict, Any


def render_score_gauge(overall_score: int, match_tier: str, breakdown: Dict[str, Any]):
    """
    Renders radial circular progress display and 5-dimensional breakdown bars.
    """
    # Color logic
    if overall_score >= 80:
        badge_color = "bg-emerald-500/20 text-emerald-400 border-emerald-500/40"
        circle_color = "#10b981"
    elif overall_score >= 65:
        badge_color = "bg-indigo-500/20 text-indigo-400 border-indigo-500/40"
        circle_color = "#6366f1"
    elif overall_score >= 50:
        badge_color = "bg-amber-500/20 text-amber-400 border-amber-500/40"
        circle_color = "#f59e0b"
    else:
        badge_color = "bg-rose-500/20 text-rose-400 border-rose-500/40"
        circle_color = "#f43f5e"

    with ui.card().classes("glass-card p-6 w-full"):
        with ui.row().classes("w-full items-center justify-between"):
            with ui.column().classes("gap-1"):
                ui.label("Overall Match Score").classes("text-sm uppercase tracking-wider text-slate-400 font-semibold")
                with ui.row().classes("items-baseline gap-2"):
                    ui.label(f"{overall_score}").classes("brand-font text-5xl font-extrabold text-white")
                    ui.label("/ 100").classes("text-slate-500 font-semibold text-lg")
                ui.label(match_tier).classes(f"text-xs px-2.5 py-1 rounded-full border font-semibold {badge_color}")

            # Radial Circular Gauge with ECharts
            gauge_options = {
                "series": [
                    {
                        "type": "gauge",
                        "startAngle": 180,
                        "endAngle": 0,
                        "min": 0,
                        "max": 100,
                        "radius": "100%",
                        "progress": {"show": True, "roundCap": True, "width": 14, "itemStyle": {"color": circle_color}},
                        "pointer": {"show": False},
                        "axisLine": {"roundCap": True, "lineStyle": {"width": 14, "color": [[1, "#1e293b"]]}},
                        "axisTick": {"show": False},
                        "splitLine": {"show": False},
                        "axisLabel": {"show": False},
                        "detail": {"show": False},
                        "data": [{"value": overall_score}],
                    }
                ]
            }
            ui.echart(gauge_options).classes("w-44 h-28")

        # 5-Dimensional Breakdown
        ui.separator().classes("my-4 bg-slate-800")
        ui.label("Scoring Breakdown").classes("text-xs uppercase tracking-wider text-slate-400 font-semibold mb-2")

        dimensions = [
            ("Required & Preferred Skills (40%)", breakdown.get("skills_score", 0), "code"),
            ("Semantic Relevance (20%)", breakdown.get("semantic_score", 0), "psychology"),
            ("Experience Alignment (15%)", breakdown.get("experience_score", 0), "work_history"),
            ("Education & Degree Fit (10%)", breakdown.get("education_score", 0), "school"),
            ("AI Rubric Holistic Review (15%)", breakdown.get("llm_rubric_score", 0), "auto_awesome"),
        ]

        with ui.column().classes("w-full gap-3"):
            for label, score, icon in dimensions:
                score_val = round(score, 1)
                with ui.column().classes("w-full gap-1"):
                    with ui.row().classes("w-full justify-between items-center text-xs font-medium text-slate-300"):
                        with ui.row().classes("items-center gap-1.5"):
                            ui.icon(icon, size="16px").classes("text-indigo-400")
                            ui.label(label)
                        ui.label(f"{score_val}%").classes("mono-font font-bold text-white")
                    ui.linear_progress(value=score_val / 100, show_value=False).classes("h-2 rounded-full").props(
                        f'color="{"emerald" if score_val >= 80 else "indigo" if score_val >= 60 else "amber"}" track-color="slate-800"'
                    )
