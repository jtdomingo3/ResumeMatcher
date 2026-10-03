"""
Career Analyzer Page: 3-Path Trajectory, 90-Day Roadmap, and AI Writer Tools.
"""

from nicegui import ui
from frontend.app.components.layout import app_layout
from frontend.app.api_client import api_client


async def career_page():
    with app_layout(current_page="Career Analyzer"):
        with ui.column().classes("gap-1 mb-2"):
            ui.label("Career Advancement & Strategy Suite").classes("brand-font text-3xl font-extrabold text-white")
            ui.label("3-Path Trajectory Modeling (Vertical, Lateral, Pivot), 90-Day Career Roadmaps, and AI Resume Writers.").classes("text-sm text-slate-400")

        # Load resumes
        try:
            resumes = await api_client.list_resumes()
        except Exception:
            resumes = []

        resume_options = {r["id"]: f"{r.get('full_name') or r.get('filename')} ({r.get('total_experience_years', 0):.1f} yrs exp)" for r in resumes}

        with ui.tabs().classes("w-full text-indigo-300 border-b border-slate-800") as main_tabs:
            tab_roadmap = ui.tab("Trajectory & 90-Day Roadmap", icon="alt_route")
            tab_writer = ui.tab("STAR Bullet Rewriter", icon="auto_fix_high")
            tab_cover = ui.tab("Cover Letter Generator", icon="history_edu")
            tab_interview = ui.tab("Interview Prep", icon="record_voice_over")

        with ui.tab_panels(main_tabs, value=tab_roadmap).classes("w-full bg-transparent p-0 pt-6"):
            # --- TAB 1: ROADMAP & CAREER PATHS ---
            with ui.tab_panel(tab_roadmap).classes("p-0 gap-6 flex flex-col"):
                with ui.card().classes("glass-card p-6 w-full"):
                    ui.label("Generate Career Trajectory Model").classes("brand-font text-lg font-bold text-white mb-3")
                    with ui.row().classes("w-full items-center gap-4"):
                        sel_res = ui.select(
                            options=resume_options,
                            value=list(resume_options.keys())[0] if resume_options else None,
                            label="Candidate Profile",
                        ).props("outlined dark dense").classes("w-full max-w-sm")

                        target_role_input = ui.input(
                            "Specialization Goal (Optional)",
                            placeholder="e.g. AI Systems Architect, Cloud Lead",
                        ).props("outlined dark dense").classes("w-full max-w-md")

                        analyze_btn = ui.button("Analyze Trajectories", icon="trending_up").classes("glow-btn px-6 py-2 text-sm")

                roadmap_container = ui.column().classes("w-full gap-6")

                async def run_career_analysis():
                    if not sel_res.value:
                        ui.notify("Please select a candidate resume first.", type="warning")
                        return
                    analyze_btn.props("loading")
                    ui.notify("Synthesizing RAG career frameworks and live market data...", type="info")
                    try:
                        report = await api_client.analyze_career(resume_id=sel_res.value, target_career=target_role_input.value or None)
                        ui.notify("Career report generated successfully!", type="positive")
                        render_roadmap_results(report)
                    except Exception as e:
                        ui.notify(f"Analysis failed: {str(e)}", type="negative")
                    finally:
                        analyze_btn.props(remove="loading")

                analyze_btn.on_click(run_career_analysis)

                def render_roadmap_results(rep: dict):
                    roadmap_container.clear()
                    with roadmap_container:
                        # 1. Career Paths Grid (Vertical, Lateral, Pivot)
                        ui.label("Strategic Career Pathways").classes("brand-font text-xl font-bold text-white mb-2")
                        paths = rep.get("career_paths", [])
                        with ui.row().classes("w-full grid grid-cols-1 md:grid-cols-3 gap-5 mb-4"):
                            for p in paths:
                                ptype = p.get("path_type", "Path")
                                fit = p.get("fit_score", 80)
                                border_color = "border-indigo-500/50" if ptype == "Vertical" else "border-sky-500/50" if ptype == "Lateral" else "border-emerald-500/50"
                                badge_bg = "bg-indigo-500/20 text-indigo-300" if ptype == "Vertical" else "bg-sky-500/20 text-sky-300" if ptype == "Lateral" else "bg-emerald-500/20 text-emerald-300"

                                with ui.card().classes(f"glass-card p-5 flex flex-col justify-between {border_color}"):
                                    with ui.column().classes("gap-2"):
                                        with ui.row().classes("w-full justify-between items-center"):
                                            ui.label(ptype).classes(f"text-xs px-2.5 py-0.5 rounded-full font-bold {badge_bg}")
                                            ui.label(f"{fit}% Fit").classes("text-xs font-bold text-white mono-font")
                                        ui.label(p.get("title", "Role")).classes("brand-font text-lg font-bold text-white leading-tight")
                                        ui.label(p.get("rationale", "")).classes("text-xs text-slate-400 leading-relaxed")

                                        ui.separator().classes("my-2 bg-slate-800")
                                        ui.label("Required Competencies:").classes("text-xs font-semibold text-slate-300")
                                        with ui.row().classes("flex-wrap gap-1"):
                                            for sk in p.get("required_skills", []):
                                                with ui.element("span").classes("px-2 py-0.5 rounded bg-slate-800 text-xs text-indigo-300 font-medium"):
                                                    ui.label(sk)

                                    with ui.row().classes("w-full items-center justify-between text-xs text-slate-500 mt-4"):
                                        ui.label("Expected Timeline:")
                                        ui.label(p.get("timeline_months", "6-12 months")).classes("text-slate-300 font-semibold")

                        # 2. 90-Day Roadmap Timeline
                        ui.label("90-Day Career Acceleration Roadmap").classes("brand-font text-xl font-bold text-white mb-2")
                        milestones = rep.get("roadmap_90_days", [])
                        with ui.column().classes("w-full gap-4 mb-4"):
                            for m in milestones:
                                with ui.card().classes("glass-card p-5 w-full border-l-4 border-l-indigo-500"):
                                    with ui.row().classes("items-center justify-between mb-2"):
                                        with ui.row().classes("items-center gap-2"):
                                            ui.icon("flag", size="20px").classes("text-indigo-400")
                                            ui.label(m.get("phase", "Phase")).classes("font-extrabold text-sm text-indigo-400 uppercase tracking-wider")
                                        ui.label(m.get("focus_area", "")).classes("font-bold text-sm text-white")

                                    with ui.column().classes("gap-1.5 pl-6"):
                                        for goal in m.get("goals", []):
                                            with ui.row().classes("items-start gap-2 text-xs text-slate-300"):
                                                ui.label("▸").classes("text-indigo-400 font-bold")
                                                ui.label(goal)

                                    resources = m.get("recommended_resources", [])
                                    if resources:
                                        with ui.row().classes("items-center gap-2 mt-3 pt-3 border-t border-slate-800 text-xs text-slate-400 pl-6"):
                                            ui.icon("menu_book", size="14px").classes("text-slate-400")
                                            ui.label("Recommended Curated Study: " + " • ".join(resources))

                        # 3. Market Calibration
                        insights = rep.get("market_insights", {})
                        if insights:
                            with ui.card().classes("glass-card p-6 w-full border border-sky-500/30"):
                                with ui.row().classes("items-center gap-2 mb-2"):
                                    ui.icon("query_stats", size="22px").classes("text-sky-400")
                                    ui.label("Live Market Benchmark & Trends").classes("brand-font text-lg font-bold text-white")
                                with ui.row().classes("w-full grid grid-cols-1 sm:grid-cols-2 gap-4 mb-3"):
                                    with ui.column().classes("gap-1"):
                                        ui.label("Estimated Compensation Range:").classes("text-xs text-slate-400")
                                        ui.label(insights.get("estimated_salary_range", "Industry Competitive")).classes("text-sm font-bold text-emerald-400 mono-font")
                                    with ui.column().classes("gap-1"):
                                        ui.label("Market Demand Indicator:").classes("text-xs text-slate-400")
                                        ui.label(insights.get("demand_trend", "High Demand")).classes("text-sm font-bold text-sky-400")
                                ui.label(insights.get("market_summary", "")).classes("text-xs text-slate-300 leading-relaxed")

            # --- TAB 2: STAR BULLET REWRITER ---
            with ui.tab_panel(tab_writer).classes("p-0 gap-4 flex flex-col"):
                with ui.card().classes("glass-card p-6 w-full"):
                    ui.label("Google STAR-XYZ Resume Bullet Rewriter").classes("brand-font text-lg font-bold text-white mb-1")
                    ui.label("Transform weak experience lines into compelling, metric-driven achievements using action verbs and quantified impact.").classes("text-xs text-slate-400 mb-4")

                    raw_bullet_input = ui.textarea(
                        "Original Bullet Point",
                        placeholder="e.g. worked on backend apis and fixed database queries",
                    ).props("outlined dark rows=3").classes("w-full mb-3")

                    with ui.row().classes("w-full gap-4 mb-4"):
                        role_in = ui.input("Target Role", placeholder="e.g. Senior Backend Engineer").props("outlined dark dense").classes("flex-1")
                        skill_in = ui.input("Key Tech/Skill", placeholder="e.g. Python / FastAPI / PostgreSQL").props("outlined dark dense").classes("flex-1")

                    rewrite_btn = ui.button("Rewrite into STAR Format", icon="auto_fix_high").classes("glow-btn px-6 py-2 text-sm")

                rewrite_output_container = ui.column().classes("w-full gap-4")

                async def handle_rewrite():
                    if not raw_bullet_input.value or not raw_bullet_input.value.strip():
                        ui.notify("Please enter a bullet point to rewrite.", type="warning")
                        return
                    rewrite_btn.props("loading")
                    try:
                        res = await api_client.rewrite_bullet(
                            bullet_text=raw_bullet_input.value.strip(),
                            target_role=role_in.value or None,
                            target_skill=skill_in.value or None,
                        )
                        rewrite_output_container.clear()
                        with rewrite_output_container:
                            with ui.card().classes("glass-card p-6 w-full border border-indigo-500/50"):
                                ui.label("Optimized STAR-XYZ Achievement").classes("text-xs font-bold text-indigo-400 uppercase tracking-wider mb-2")
                                ui.label(f'"{res["rewritten_star"]}"').classes("text-base font-semibold text-white leading-relaxed mb-4")

                                with ui.row().classes("w-full grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs"):
                                    with ui.card().classes("bg-slate-900/60 p-3 rounded-xl border border-slate-800"):
                                        ui.label("Action Verb").classes("text-slate-400")
                                        ui.label(res.get("action_verb_used", "Engineered")).classes("font-bold text-emerald-400")
                                    with ui.card().classes("bg-slate-900/60 p-3 rounded-xl border border-slate-800"):
                                        ui.label("Quantified Metric").classes("text-slate-400")
                                        ui.label(res.get("metrics_quantified", "Quantified")).classes("font-bold text-sky-400")
                                    with ui.card().classes("bg-slate-900/60 p-3 rounded-xl border border-slate-800"):
                                        ui.label("Structure").classes("text-slate-400")
                                        ui.label("STAR Framework").classes("font-bold text-indigo-300")
                    except Exception as e:
                        ui.notify(f"Rewrite failed: {str(e)}", type="negative")
                    finally:
                        rewrite_btn.props(remove="loading")

                rewrite_btn.on_click(handle_rewrite)

            # --- TAB 3: COVER LETTER ---
            with ui.tab_panel(tab_cover).classes("p-0 gap-4 flex flex-col"):
                with ui.card().classes("glass-card p-6 w-full"):
                    ui.label("Tailored Application Cover Letter Generator").classes("brand-font text-lg font-bold text-white mb-3")

                    with ui.row().classes("w-full gap-4 mb-3"):
                        cl_res_sel = ui.select(options=resume_options, value=list(resume_options.keys())[0] if resume_options else None, label="Resume").props("outlined dark dense").classes("flex-1")
                        cl_comp_input = ui.input("Target Company Name", placeholder="e.g. Acme Corp").props("outlined dark dense").classes("flex-1")

                    cl_jd_input = ui.textarea("Target Job Description", placeholder="Paste the job description here...").props("outlined dark rows=4").classes("w-full mb-3")

                    cl_btn = ui.button("Generate Tailored Cover Letter", icon="history_edu").classes("glow-btn px-6 py-2 text-sm")

                cl_output_container = ui.column().classes("w-full gap-4")

                async def handle_cover_letter():
                    if not cl_res_sel.value or not cl_jd_input.value:
                        ui.notify("Please select a resume and paste job description.", type="warning")
                        return
                    cl_btn.props("loading")
                    try:
                        res = await api_client.generate_cover_letter(
                            resume_id=cl_res_sel.value,
                            job_description=cl_jd_input.value,
                            company_name=cl_comp_input.value or None,
                        )
                        cl_output_container.clear()
                        with cl_output_container:
                            with ui.card().classes("glass-card p-6 w-full"):
                                ui.markdown(res.get("cover_letter_markdown", "")).classes("text-slate-200 leading-relaxed text-sm")
                    except Exception as e:
                        ui.notify(f"Cover letter generation failed: {e}", type="negative")
                    finally:
                        cl_btn.props(remove="loading")

                cl_btn.on_click(handle_cover_letter)

            # --- TAB 4: INTERVIEW PREP ---
            with ui.tab_panel(tab_interview).classes("p-0 gap-4 flex flex-col"):
                with ui.card().classes("glass-card p-6 w-full"):
                    ui.label("Role-Targeted Interview Preparation").classes("brand-font text-lg font-bold text-white mb-2")
                    ui.label("Generates behavioral and technical questions focused specifically on your experience and target role requirements.").classes("text-xs text-slate-400 mb-4")

                    try:
                        jobs_list = await api_client.list_jobs()
                    except Exception:
                        jobs_list = []
                    job_options = {j["id"]: j["title"] for j in jobs_list}

                    with ui.row().classes("w-full gap-4 mb-4"):
                        ip_res_sel = ui.select(options=resume_options, value=list(resume_options.keys())[0] if resume_options else None, label="Resume").props("outlined dark dense").classes("flex-1")
                        ip_job_sel = ui.select(options=job_options, value=list(job_options.keys())[0] if job_options else None, label="Target Job").props("outlined dark dense").classes("flex-1")

                    prep_btn = ui.button("Generate Interview Questions", icon="record_voice_over").classes("glow-btn px-6 py-2 text-sm")

                prep_output_container = ui.column().classes("w-full gap-4")

                async def handle_prep():
                    if not ip_res_sel.value or not ip_job_sel.value:
                        ui.notify("Please select both a resume and target job.", type="warning")
                        return
                    prep_btn.props("loading")
                    try:
                        questions = await api_client.generate_interview_prep(resume_id=ip_res_sel.value, job_id=ip_job_sel.value)
                        prep_output_container.clear()
                        with prep_output_container:
                            for q in questions:
                                with ui.card().classes("glass-card p-5 w-full mb-3"):
                                    with ui.row().classes("items-center justify-between mb-2"):
                                        ui.label(q.get("category", "Question")).classes("text-xs px-2.5 py-0.5 rounded-full font-bold bg-indigo-500/20 text-indigo-300")
                                    ui.label(q.get("question", "")).classes("font-bold text-sm text-white mb-2")
                                    with ui.column().classes("gap-1 bg-slate-900/60 p-3 rounded-xl border border-slate-800 text-xs"):
                                        ui.label("What Interviewer Evaluates:").classes("text-slate-400 font-semibold")
                                        ui.label(q.get("what_interviewer_looks_for", "")).classes("text-slate-300 mb-2")
                                        ui.label("Suggested STAR Answer Outline:").classes("text-indigo-400 font-semibold")
                                        ui.label(q.get("star_answer_outline", "")).classes("text-slate-300")
                    except Exception as e:
                        ui.notify(f"Interview prep generation failed: {e}", type="negative")
                    finally:
                        prep_btn.props(remove="loading")

                prep_btn.on_click(handle_prep)
