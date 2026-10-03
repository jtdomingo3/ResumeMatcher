"""
Job Match & ATS Compliance Evaluation Page.
Executes explainable 5-dimensional hybrid scoring between a resume and job posting.
"""

from nicegui import ui
from frontend.app.components.layout import app_layout
from frontend.app.components.score_gauge import render_score_gauge
from frontend.app.components.skills_chips import render_skills_chips
from frontend.app.components.ats_card import render_ats_card
from frontend.app.api_client import api_client


async def match_page():
    with app_layout(current_page="Job Match"):
        with ui.column().classes("gap-1 mb-2"):
            ui.label("Job Match & ATS Parser Audit").classes("brand-font text-3xl font-extrabold text-white")
            ui.label("Evaluate resume compatibility against target job descriptions with explainable 5-dimensional scoring and ATS compliance audits.").classes("text-sm text-slate-400")

        # Load available resumes
        try:
            resumes = await api_client.list_resumes()
        except Exception:
            resumes = []

        resume_options = {r["id"]: f"{r.get('full_name') or r.get('filename')} ({r.get('total_experience_years', 0):.1f} yrs exp)" for r in resumes}

        with ui.card().classes("glass-card p-6 w-full"):
            ui.label("Step 1: Select Candidate Resume").classes("brand-font text-lg font-bold text-white mb-2")
            if not resume_options:
                with ui.row().classes("items-center gap-2 p-3 bg-amber-500/10 rounded-xl border border-amber-500/30 text-xs text-amber-300"):
                    ui.icon("warning", size="18px")
                    ui.label("No resumes uploaded yet.")
                    with ui.link(target="/resumes").classes("font-bold text-indigo-400 underline"):
                        ui.label("Go to Resume Studio to upload one.")
                selected_resume = None
            else:
                selected_resume = ui.select(
                    options=resume_options,
                    value=list(resume_options.keys())[0] if resume_options else None,
                    label="Candidate Resume",
                ).props("outlined dark dense").classes("w-full max-w-md")

        # Step 2: Target Job Description Input
        with ui.card().classes("glass-card p-6 w-full"):
            ui.label("Step 2: Provide Target Job Description").classes("brand-font text-lg font-bold text-white mb-3")

            with ui.tabs().classes("w-full text-indigo-300") as tabs:
                tab_paste = ui.tab("Paste Text", icon="edit_note")
                tab_url = ui.tab("Import from URL", icon="link")

            with ui.tab_panels(tabs, value=tab_paste).classes("w-full bg-transparent p-0 pt-4"):
                with ui.tab_panel(tab_paste).classes("p-0 gap-3 flex flex-col"):
                    job_title_input = ui.input("Job Title (Optional)", placeholder="e.g. Senior Python Backend Engineer").props("outlined dark dense").classes("w-full max-w-md")
                    job_text_area = ui.textarea(
                        "Job Description Text",
                        placeholder="Paste the full job posting text here including responsibilities and qualifications...",
                    ).props("outlined dark rows=6").classes("w-full")

                with ui.tab_panel(tab_url).classes("p-0 gap-3 flex flex-col"):
                    job_url_input = ui.input(
                        "Job Posting URL",
                        placeholder="https://company.com/careers/senior-python-engineer",
                    ).props("outlined dark").classes("w-full")
                    ui.label("Web fetcher utilizes an automated SSRF security sandbox to safely extract content.").classes("text-xs text-slate-500")

            ui.separator().classes("my-4 bg-slate-800")

            with ui.row().classes("w-full justify-between items-center"):
                use_llm_switch = ui.switch("Include AI Holistic Review (OpenRouter Free)").props("color=indigo").classes("text-sm text-slate-300")
                use_llm_switch.value = True

                match_btn = ui.button("Analyze & Compute Match Score", icon="auto_awesome").classes("glow-btn px-6 py-2.5 text-sm")

        # Results Display Container
        results_container = ui.column().classes("w-full gap-6")

        async def run_match():
            if not selected_resume or not selected_resume.value:
                ui.notify("Please select or upload a candidate resume first.", type="warning")
                return

            rid = selected_resume.value
            raw_text = job_text_area.value.strip() if job_text_area.value else None
            url = job_url_input.value.strip() if (job_url_input.value and tabs.value == tab_url) else None

            if not raw_text and not url:
                ui.notify("Please paste a job description or provide a job posting URL.", type="warning")
                return

            match_btn.props("loading")
            ui.notify("Ingesting job description and calculating compatibility...", type="info")

            try:
                # 1. Create job
                job_res = await api_client.create_job(
                    title=job_title_input.value or None,
                    raw_text=raw_text,
                    url=url,
                )
                jid = job_res["id"]

                # 2. Run match
                result = await api_client.match(resume_id=rid, job_id=jid, use_llm=use_llm_switch.value)
                ui.notify("Match analysis completed successfully!", type="positive")

                # 3. Render results
                render_results(result)
            except Exception as e:
                ui.notify(f"Match evaluation failed: {str(e)}", type="negative")
            finally:
                match_btn.props(remove="loading")

        match_btn.on_click(run_match)

        def render_results(res: dict):
            results_container.clear()
            with results_container:
                # Score Gauge and Breakdown
                render_score_gauge(
                    overall_score=res.get("overall_score", 0),
                    match_tier=res.get("match_tier", "Match"),
                    breakdown=res.get("breakdown", {}),
                )

                # Skills Analysis Chips
                render_skills_chips(res.get("skills_analysis", {}))

                # ATS Report
                render_ats_card(res.get("ats_report", {}))

                # Gap Analysis & Action Plan
                gaps = res.get("gap_analysis", {})
                crit_gaps = gaps.get("critical_skill_gaps", [])
                fixes = gaps.get("priority_fixes", [])

                with ui.card().classes("glass-card p-6 w-full"):
                    ui.label("Prioritized Action Plan & Gap Remediation").classes("brand-font text-lg font-bold text-white mb-3")
                    if fixes:
                        with ui.column().classes("w-full gap-2"):
                            for idx, fix in enumerate(fixes, start=1):
                                with ui.row().classes("items-start gap-2 p-3 bg-slate-900/60 rounded-xl border border-slate-800 text-xs text-slate-300"):
                                    ui.label(f"{idx}.").classes("text-indigo-400 font-bold")
                                    ui.label(fix)
                    else:
                        ui.label("No immediate gap fixes required.").classes("text-xs text-emerald-400")
