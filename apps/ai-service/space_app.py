"""Optional Hugging Face Gradio Space entry (not used on Vercel).

Vercel must see FastAPI only in app/main.py. Keep this file off the
supported Vercel entrypoint names (app.py, main.py, index.py).
"""

from __future__ import annotations

import os

import gradio as gr
import uvicorn

from app.main import app as fastapi_app

with gr.Blocks(title="Academic Research Copilot API") as demo:
    gr.Markdown(
        """
        # Academic Research Copilot API
        This free Space hosts the FastAPI backend. Use the Vercel web app for chat,
        documents, tools, and Prompt Lab.
        - Health: `/health`
        - API: `/api/v1`
        """
    )

app = gr.mount_gradio_app(fastapi_app, demo, path="/")


def _launch(*args: object, **kwargs: object) -> None:
    _ = args
    host = str(kwargs.get("server_name") or os.environ.get("HOST") or "0.0.0.0")
    port = int(kwargs.get("server_port") or os.environ.get("PORT") or 7860)
    uvicorn.run(app, host=host, port=port)


demo.launch = _launch  # type: ignore[method-assign]

if __name__ == "__main__":
    _launch(server_name="0.0.0.0", server_port=int(os.environ.get("PORT", "7860")))
