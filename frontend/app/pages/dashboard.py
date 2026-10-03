"""
Dashboard Page: KPI Overview, Quick Action Cards, and Recent Matches.
"""

from nicegui import ui
from frontend.app.components.layout import app_layout
from frontend.app.api_client import api_client


async def dashboard_page():
    with app_layout(current_page="Dashboard"):
        # Header banner
        with ui.row().classes("w-full justify-between items-start"):
            with ui.column().classes("gap-1"):
                ui.label("Executive Career Dashboard").classes("brand-font text-3xl font-extrabold text-white")
                ui.label("AI-Powered Resume Optimization, Hybrid Matching, and 90-Day Advancement Roadmaps.").classes("text-sm text-slate-400")

            with ui.link(target="/match").classes("no-underline"):
                ui.button("New Job Match", icon="tune").classes("glow-btn px-5 py-2.5 text-sm")

        # Load dynamic metrics
        try:
            health = await api_client.get_health()
            resumes = await api_client.list_resumes()
            jobs = await api_client.list_jobs()
            matches = await api_client.list_matches()
        except Exception:
            health = {}
            resumes = []
            jobs = []
            matches = []

        # KPI Cards Grid
        with ui.row().classes("w-full grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5"):
            kpis = [
                ("Uploaded Resumes", len(resumes), "description", "text-indigo-400", "bg-indigo-500/10"),
                ("Target Jobs Analyzed", len(jobs), "business_center", "text-sky-400", "bg-sky-500/10"),
                ("Completed Matches", len(matches), "verified", "text-emerald-400", "bg-emerald-500/10"),
                ("Live Free Models", health.get("available_free_models", 0), "bolt", "text-amber-400", "bg-amber-500/10"),
            ]
            for title, value, icon, icon_color, bg_color in kpis:
                with ui.card().classes("glass-card p-5 flex items-center justify-between"):
                    with ui.column().classes("gap-1"):
                        ui.label(title).classes("text-xs font-semibold text-slate-400 uppercase tracking-wider")
                        ui.label(str(value)).classes("brand-font text-3xl font-extrabold text-white mono-font")
                    with ui.element("div").classes(f"p-3 rounded-xl {bg_color}"):
                        ui.icon(icon, size="28px").classes(icon_color)

        # Quick Actions Section
        with ui.column().classes("w-full gap-4"):
            ui.label("Core Application Capabilities").classes("brand-font text-xl font-bold text-white")
            with ui.row().classes("w-full grid grid-cols-1 md:grid-cols-3 gap-5"):
                actions = [
                    (
                        "Resume Studio",
                        "Upload and segment PDF/DOCX resumes with automated skills extraction and PII privacy protection.",
                        "description",
                        "/resumes",
                        "text-indigo-400",
                    ),
                    (
                        "Job Match & ATS Audit",
                        "Calculate explainable 0-100 fit scores with 5-dimensional breakdown and ATS keyword audit.",
                        "tune",
                        "/match",
                        "text-emerald-400",
                    ),
                    (
                        "Career Analyzer & Copilot",
                        "Discover vertical/lateral/pivot career paths, generate 90-day roadmaps, and chat with RAG Copilot.",
                        "psychology",
                        "/career",
                        "text-sky-400",
                    ),
                ]
                for title, desc, icon, route, color in actions:
                    with ui.card().classes("glass-card p-6 flex flex-col justify-between hover:border-indigo-500/50"):
                        with ui.column().classes("gap-3"):
                            ui.icon(icon, size="32px").classes(color)
                            ui.label(title).classes("brand-font text-lg font-bold text-white")
                            ui.label(desc).classes("text-xs text-slate-400 leading-relaxed")
                        with ui.link(target=route).classes("no-underline mt-4"):
                            ui.button("Launch", icon_right="arrow_forward").props("flat").classes(f"p-0 text-xs font-bold {color}")

        # Recent Matches Table
        with ui.card().classes("glass-card p-6 w-full"):
            with ui.row().classes("w-full justify-between items-center mb-4"):
                ui.label("Recent Match Evaluations").classes("brand-font text-xl font-bold text-white")
                with ui.link(target="/match").classes("no-underline"):
                    ui.label("View All Matches →").classes("text-xs font-semibold text-indigo-400 hover:text-indigo-300")

            if matches:
                columns = [
                    {"name": "score", "label": "Score", "field": "overall_score", "sortable": True},
                    {"name": "tier", "label": "Match Tier", "field": "match_tier"},
                    {"name": "date", "label": "Evaluation Date", "field": "created_at"},
                ]
                rows = [
                    {
                        "overall_score": f"{int(m['overall_score'])}%",
                        "match_tier": m.get("match_tier", "Evaluated"),
                        "created_at": (m.get("created_at") or "")[:10],
                    }
                    for m in matches[:6]
                ]
                ui.table(columns=columns, rows=rows, row_key="date").classes("w-full bg-transparent text-slate-200")
            else:
                with ui.column().classes("w-full items-center justify-center py-8 text-slate-500 gap-2"):
                    ui.icon("analytics", size="42px").classes("text-slate-600")
                    ui.label("No matches evaluated yet. Upload a resume and match against your first job!").classes("text-xs")
