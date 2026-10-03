"""
Main Application Layout and Navigation Header for NiceGUI Frontend.
"""

from contextlib import contextmanager
from nicegui import ui
from backend.app.core.secrets import SecretManager
from frontend.app.theme.tokens import apply_theme


@contextmanager
def app_layout(current_page: str = "Dashboard"):
    """
    Renders top navigation bar, system status badge, and structured content container.
    """
    apply_theme()

    # Header
    with ui.header().classes("glass-header px-8 py-3 flex items-center justify-between sticky top-0 z-50"):
        with ui.row().classes("items-center gap-3"):
            ui.icon("psychology", size="34px").classes("text-indigo-400")
            with ui.column().classes("gap-0"):
                ui.label("ResumeMatcher AI").classes("brand-font text-xl font-bold gradient-text leading-tight")
                ui.label("Career Analyzer & Match Engine").classes("text-xs text-slate-400 font-medium")

        # Navigation Links
        nav_items = [
            ("Dashboard", "/", "dashboard"),
            ("Resume Studio", "/resumes", "description"),
            ("Job Match", "/match", "tune"),
            ("Career Analyzer", "/career", "trending_up"),
            ("Career Copilot", "/copilot", "chat"),
            ("Model Manager", "/models", "memory"),
            ("Settings", "/settings", "settings"),
        ]

        with ui.row().classes("items-center gap-1 bg-slate-900/60 p-1.5 rounded-xl border border-slate-800"):
            for title, route, icon in nav_items:
                is_active = current_page.lower() in title.lower()
                active_classes = "bg-indigo-600/30 text-indigo-300 border border-indigo-500/40" if is_active else "text-slate-400 hover:text-white hover:bg-slate-800/50"
                with ui.link(target=route).classes(f"no-underline px-3.5 py-1.5 rounded-lg text-sm font-medium flex items-center gap-2 transition-all {active_classes}"):
                    ui.icon(icon, size="18px")
                    ui.label(title)

        # Status Badges
        with ui.row().classes("items-center gap-3"):
            masked_key = SecretManager.get_masked_openrouter_key()
            if masked_key:
                with ui.row().classes("status-pill status-online"):
                    ui.html("<span class='status-indicator'></span>")
                    ui.label(f"Key: {masked_key}").classes("mono-font")
            else:
                with ui.link(target="/settings").classes("no-underline"):
                    with ui.row().classes("status-pill bg-amber-500/10 text-amber-400 border border-amber-500/30"):
                        ui.icon("warning", size="14px")
                        ui.label("Set API Key")

    # Main content container
    with ui.column().classes("w-full max-w-7xl mx-auto px-6 py-8 gap-8"):
        yield
