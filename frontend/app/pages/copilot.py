"""
Career Copilot Page: Real-time Streaming Chat with RAG and DuckDuckGo Web Context Injection.
"""

from nicegui import ui
from frontend.app.components.layout import app_layout
from frontend.app.api_client import api_client


async def copilot_page():
    with app_layout(current_page="Career Copilot"):
        with ui.column().classes("gap-1 mb-2"):
            ui.label("Career Copilot & Advisory Chat").classes("brand-font text-3xl font-extrabold text-white")
            ui.label("Streaming AI mentor grounded in your local RAG knowledge base and live DuckDuckGo web search.").classes("text-sm text-slate-400")

        # Load resumes and jobs for optional attachment
        try:
            resumes = await api_client.list_resumes()
            jobs = await api_client.list_jobs()
        except Exception:
            resumes = []
            jobs = []

        resume_options = {r["id"]: f"Resume: {r.get('full_name') or r.get('filename')}" for r in resumes}
        job_options = {j["id"]: f"Job: {j['title']}" for j in jobs}

        # Chat Control Bar (Toggles & Attachments)
        with ui.card().classes("glass-card p-4 w-full"):
            with ui.row().classes("w-full items-center justify-between flex-wrap gap-4"):
                with ui.row().classes("items-center gap-4"):
                    rag_toggle = ui.switch("RAG Knowledge Base").props("color=indigo").classes("text-xs font-semibold text-slate-300")
                    rag_toggle.value = True

                    web_toggle = ui.switch("DuckDuckGo Web Search").props("color=sky").classes("text-xs font-semibold text-slate-300")
                    web_toggle.value = False

                with ui.row().classes("items-center gap-3"):
                    att_res = ui.select(options={"none": "No Resume Attached", **resume_options}, value="none").props("outlined dark dense").classes("text-xs w-48")
                    att_job = ui.select(options={"none": "No Job Attached", **job_options}, value="none").props("outlined dark dense").classes("text-xs w-48")

        # Chat Conversation Window
        chat_scroll = ui.scroll_area().classes("w-full h-[520px] p-6 glass-card rounded-2xl border border-slate-800")
        with chat_scroll:
            chat_container = ui.column().classes("w-full gap-4")

            # Welcome message from Copilot
            with chat_container:
                with ui.row().classes("items-start gap-3 w-full"):
                    ui.icon("psychology", size="26px").classes("text-indigo-400 mt-1")
                    with ui.card().classes("bg-slate-900/80 p-4 rounded-2xl rounded-tl-sm border border-slate-800 max-w-2xl text-sm leading-relaxed text-slate-200"):
                        ui.label("Hello! I am your Career Copilot. I can advise on resume structuring, gap analysis, career pivots, and technical interviews. Ask me anything or attach a resume above to begin!")

        # Chat Input Box
        with ui.card().classes("glass-card p-3 w-full flex items-center gap-3"):
            user_input = ui.input(
                placeholder="Ask your Copilot (e.g. 'How should I explain a career pivot from QA to Backend Engineer?')...",
            ).props("outlined dark rounded").classes("flex-1 text-sm")

            send_btn = ui.button(icon="send").classes("glow-btn p-3 rounded-full")

        async def send_message():
            prompt = user_input.value.strip() if user_input.value else ""
            if not prompt:
                return

            user_input.value = ""

            # Render user message
            with chat_container:
                with ui.row().classes("items-start gap-3 w-full justify-end"):
                    with ui.card().classes("bg-indigo-600/30 p-4 rounded-2xl rounded-tr-sm border border-indigo-500/40 max-w-2xl text-sm leading-relaxed text-white"):
                        ui.label(prompt)
                    ui.icon("person", size="24px").classes("text-indigo-300 mt-1")

            chat_scroll.scroll_to(percent=1.0)

            # Prepare Assistant Message Bubble with streaming placeholder
            with chat_container:
                with ui.row().classes("items-start gap-3 w-full"):
                    ui.icon("psychology", size="26px").classes("text-indigo-400 mt-1")
                    with ui.card().classes("bg-slate-900/80 p-4 rounded-2xl rounded-tl-sm border border-slate-800 max-w-2xl text-sm leading-relaxed text-slate-200"):
                        response_markdown = ui.markdown("...")

            chat_scroll.scroll_to(percent=1.0)

            # Stream tokens
            tokens = []
            try:
                rid = None if att_res.value == "none" else att_res.value
                jid = None if att_job.value == "none" else att_job.value

                async for token in api_client.stream_chat(
                    message=prompt,
                    enable_rag=rag_toggle.value,
                    enable_web=web_toggle.value,
                    resume_id=rid,
                    job_id=jid,
                ):
                    tokens.append(token)
                    response_markdown.set_content("".join(tokens))
                    chat_scroll.scroll_to(percent=1.0)
            except Exception as e:
                response_markdown.set_content(f"*(Error communicating with assistant: {str(e)})*")

        send_btn.on_click(send_message)
        user_input.on("keydown.enter", send_message)
