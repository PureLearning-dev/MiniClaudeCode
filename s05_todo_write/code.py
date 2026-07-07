import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from s04_hooks import code as hooks
from s05_todo_write import utils
from s04_hooks.utils import trigger_hooks

rounds_since_todo = 0

def agent_loop(messages):
    global rounds_since_todo
    while True:
        # reminder 机制——判断是否连续 3 轮未调用 todo_write 工具
        if rounds_since_todo >= 3 and messages:
            messages.append({"role": "user",
                             "content": "<reminder>Update your todos.</reminder>"})
            rounds_since_todo = 0
        response = hooks.permission_code.tool_use_code.agent_loop_code.client.messages.create(
            model=hooks.permission_code.tool_use_code.agent_loop_code.MODEL,
            system=hooks.permission_code.tool_use_code.agent_loop_code.SYSTEM,
            messages=messages,
            tools=hooks.permission_code.tool_use_code.agent_loop_code.TOOLS,
            max_tokens=hooks.permission_code.tool_use_code.agent_loop_code.MAX_TOKEN,
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
                results.append({"type": "tool_result", "tool_use_id": block.id, "content": str(blocked)})
                continue
            handler = utils.TOOL_HANDLERS.get(block.name)
            output = handler(**block.input) if handler else f"Unknown: {block.name}"
            trigger_hooks("PostToolUse", block, output)
            # 如果调用 todo_write，则重置计数
            if block.name == "todo_write":
                rounds_since_todo = 0
            results.append({"type": "tool_result", "tool_use_id": block.id, "content": output})

        messages.append({"role": "user", "content": results})

history = []

if __name__ == "__main__":
    print("s05: TodoWrite — plan before execute, nag if you forget")
    print("Type a question, press Enter. Type q to quit.\n")
    history = []
    while True:
        try:
            query = input("\033[36ms05 >> \033[0m")
        except (EOFError, KeyboardInterrupt):
            break
        if query.strip().lower() in ("q", "exit", ""):
            break
        trigger_hooks("UserPromptSubmit", query)
        history.append({"role": "user", "content": query})
        agent_loop(history)
        for block in history[-1]["content"]:
            if getattr(block, "type", None) == "text":
                print(block.text)
        print()





