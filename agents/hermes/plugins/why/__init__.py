"""why plugin — /why provenance view.

register(ctx) wires:
  - post_tool_call hook -> capture connector calls into a per-answer ledger
  - pre_llm_call hook   -> reset the ledger when a NEW user question arrives
  - /why command        -> render the ledger client-side (no LLM, not in transcript)
"""
from . import ledger


def register(ctx):
    ctx.register_hook("post_tool_call", ledger.on_tool_call)
    ctx.register_hook("pre_llm_call", ledger.on_user_turn)
    ctx.register_command(
        "why",
        handler=ledger.render_why,
        description="Show how the last answer was derived (data -> gate -> model -> result).",
    )
