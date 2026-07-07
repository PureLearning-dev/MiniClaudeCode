"""
agent — main agent loop with nag reminder and task auto-dispatch.

Wires up the "task" tool (from subagent.py) into the parent's tool
registry, then runs the core while loop: call model → handle tool_use
→ repeat until stop_reason is not tool_use.
"""
from config import MODEL, client, SYSTEM
from tools import TOOLS, TOOL_HANDLERS, CURRENT_TODOS
from hooks import trigger_hooks
from subagent import spawn_subagent

# ── Wire the "task" tool into the parent registry ──────────
TOOLS.append({
    "name": "task",
    "description": (
        "Launch a subagent to handle a complex subtask. "
        "Returns only the final conclusion."
    ),
    "input_schema": {
        "type": "object",
        "properties": {"description": {"type": "string"}},
        "required": ["description"],
    },
})
TOOL_HANDLERS["task"] = spawn_subagent

# ── Nag counter (module-level so it survives across turns) ─
rounds_since_todo = 0


def agent_loop(messages: list):
    """Core agent loop: call model, dispatch tools, repeat."""
    global rounds_since_todo

    while True:
        # s05: nag reminder after 3 rounds without a todo_update
        if rounds_since_todo >= 3 and messages:
            messages.append({
                "role": "user",
                "content": "<reminder>Update your todos.</reminder>",
            })
            rounds_since_todo = 0

        response = client.messages.create(
            model=MODEL,
            system=SYSTEM,
            messages=messages,
            tools=TOOLS,
            max_tokens=8000,
        )
        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason != "tool_use":
            force = trigger_hooks("Stop", messages)
            if force:
                messages.append({"role": "user", "content": force})
                continue
            return

        rounds_since_todo += 1
        results = []
        for block in response.content:
            if block.type != "tool_use":
                continue

            blocked = trigger_hooks("PreToolUse", block)
            if blocked:
                results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": str(blocked),
                })
                continue

            handler = TOOL_HANDLERS.get(block.name)
            output = handler(**block.input) if handler else f"Unknown: {block.name}"
            trigger_hooks("PostToolUse", block, output)

            # Reset nag counter on todo_write
            if block.name == "todo_write":
                rounds_since_todo = 0

            results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": output,
            })

        messages.append({"role": "user", "content": results})
