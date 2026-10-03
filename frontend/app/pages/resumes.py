"""
Resume Studio Page: Upload, Parse, Segment, and Inspect Candidate Profiles.
"""

from nicegui import ui, events
from frontend.app.components.layout import app_layout
from frontend.app.api_client import api_client


async def resumes_page():
    with app_layout(current_page="Resume Studio"):
        # Header
        with ui.column().classes("gap-1 mb-2"):
            ui.label("Resume Studio & Profile Ingestion").classes("brand-font text-3xl font-extrabold text-white")
            ui.label("Upload your resume in PDF, DOCX, or TXT format. Extracted skills, experience, and education will be automatically structured.").classes("text-sm text-slate-400")

        # Top Section: Upload Card + Privacy Toggle
        with ui.card().classes("glass-card p-6 w-full"):
            with ui.row().classes("w-full justify-between items-center mb-4"):
                with ui.column().classes("gap-0"):
                    ui.label("Upload Candidate Resume").classes("brand-font text-lg font-bold text-white")
                    ui.label("Supports PDF (with multi-column fallback), DOCX, and TXT (Max 5MB)").classes("text-xs text-slate-400")

                # PII Masking Switch
                pii_switch = ui.switch("Mask Personal Contact Info (PII)").props("color=indigo").classes("text-sm text-slate-300")
                pii_switch.value = True

            upload_result_container = ui.column().classes("w-full gap-4")

            async def handle_upload(e: events.UploadEventArguments):
                ui.notify(f"Processing '{e.name}'...", type="info")
                try:
                    content = e.content.read()
                    res = await api_client.upload_resume(filename=e.name, content_bytes=content, mask_pii=pii_switch.value)
                    ui.notify("Resume parsed and ingested successfully!", type="positive")
                    render_parsed_profile(res)
                except Exception as exc:
                    ui.notify(f"Upload failed: {str(exc)}", type="negative")

            ui.upload(on_upload=handle_upload, max_file_size=5_000_000, auto_upload=True).props(
                'accept=".pdf,.docx,.txt,.md" label="Drag and drop your resume file here"'
            ).classes("w-full bg-slate-900/50 border-dashed border-2 border-slate-700 rounded-xl p-4")

        # Container for viewing parsed profile details
        profile_display = ui.column().classes("w-full gap-6")

        def render_parsed_profile(res_data: dict):
            profile_display.clear()
            prof = res_data.get("profile", {})
            with profile_display:
                with ui.card().classes("glass-card p-6 w-full border border-indigo-500/40"):
                    with ui.row().classes("w-full justify-between items-start mb-4"):
                        with ui.column().classes("gap-1"):
                            ui.label(prof.get("full_name") or res_data.get("filename", "Candidate")).classes("brand-font text-2xl font-bold text-white")
                            with ui.row().classes("items-center gap-4 text-xs text-slate-400"):
                                if prof.get("email"):
                                    with ui.row().classes("items-center gap-1"):
                                        ui.icon("mail", size="14px")
                                        ui.label(prof["email"])
                                if prof.get("phone"):
                                    with ui.row().classes("items-center gap-1"):
                                        ui.icon("phone", size="14px")
                                        ui.label(prof["phone"])
                        with ui.element("div").classes("bg-indigo-500/20 text-indigo-300 border border-indigo-500/40 px-3 py-1.5 rounded-xl font-bold text-xs"):
                            ui.label(f"{prof.get('total_experience_years', 0):.1f} Years Total Experience")

                    ui.separator().classes("my-3 bg-slate-800")

                    # Extracted Skills Chips
                    skills = prof.get("skills", [])
                    ui.label(f"Extracted Technical Competencies ({len(skills)})").classes("text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2")
                    if skills:
                        with ui.row().classes("flex-wrap gap-2 mb-4"):
                            for s in skills:
                                with ui.element("div").classes("chip-matched"):
                                    ui.label(s.get("name") if isinstance(s, dict) else s)
                    else:
                        ui.label("No skills detected in document.").classes("text-xs text-slate-500 italic mb-4")

                    # Experience Bullets
                    experience = prof.get("experience", [])
                    if experience:
                        ui.label("Work Experience History").classes("text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2")
                        for exp in experience:
                            title = exp.get("title", "Role") if isinstance(exp, dict) else "Role"
                            bullets = exp.get("bullets", []) if isinstance(exp, dict) else []
                            with ui.card().classes("bg-slate-900/60 p-4 rounded-xl border border-slate-800 mb-2 w-full"):
                                ui.label(title).classes("font-bold text-sm text-indigo-300")
                                for b in bullets[:4]:
                                    with ui.row().classes("items-start gap-2 text-xs text-slate-300 mt-1"):
                                        ui.label("•").classes("text-indigo-400 font-bold")
                                        ui.label(b)

        # Existing Resumes Library
        with ui.card().classes("glass-card p-6 w-full"):
            ui.label("Your Ingested Resume Library").classes("brand-font text-lg font-bold text-white mb-4")

            try:
                resumes_list = await api_client.list_resumes()
            except Exception:
                resumes_list = []

            if resumes_list:
                table_container = ui.column().classes("w-full")

                def refresh_table(resumes):
                    table_container.clear()
                    with table_container:
                        for r in resumes:
                            with ui.card().classes("bg-slate-900/60 p-4 rounded-xl border border-slate-800 flex items-center justify-between w-full mb-2"):
                                with ui.row().classes("items-center gap-3"):
                                    ui.icon("description", size="24px").classes("text-indigo-400")
                                    with ui.column().classes("gap-0"):
                                        ui.label(r.get("filename", "Resume")).classes("font-bold text-sm text-white")
                                        ui.label(f"{r.get('full_name') or 'Candidate'} • {r.get('total_experience_years', 0):.1f} yrs exp • {r.get('skills_count', 0)} skills").classes("text-xs text-slate-400")

                                with ui.row().classes("items-center gap-2"):
                                    async def view_resume(rid=r["id"]):
                                        try:
                                            full = await api_client.get_resume(rid)
                                            render_parsed_profile(full)
                                            ui.notify("Loaded resume profile details", type="info")
                                        except Exception as e:
                                            ui.notify(f"Could not load resume: {e}", type="negative")

                                    async def delete_res(rid=r["id"]):
                                        ok = await api_client.delete_resume(rid)
                                        if ok:
                                            ui.notify("Resume deleted", type="positive")
                                            new_list = await api_client.list_resumes()
                                            refresh_table(new_list)

                                    ui.button("Inspect", icon="visibility", on_click=view_resume).props("flat text-indigo-300 text-xs")
                                    ui.button("Delete", icon="delete", on_click=delete_res).props("flat text-rose-400 text-xs")

                refresh_table(resumes_list)
            else:
                ui.label("No resumes saved in library. Upload your first resume above!").classes("text-xs text-slate-500 italic")
