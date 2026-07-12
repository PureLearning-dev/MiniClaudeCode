"""
hooks 让执行流程中的扩展变得更加容易

User types query
       │
       ▼
  ┌──────────────────┐
  │ UserPromptSubmit │ ── trigger_hooks() before LLM
  └────────┬─────────┘
           ▼
  ┌────────────┐     ┌─────────────────────────────┐
  │  messages  │────▶│  LLM (stop_reason=tool_use?)│
  └────────────┘     │   No ──▶ Stop hooks ──▶ exit │
                     │   Yes ──▶ tool_use block ──┐ │
                     └────────────────────────────┘ │
                                                    ▼
                                          ┌──────────────────┐
                                          │ trigger_hooks()   │
                                          │  PreToolUse:      │
                                          │   permission_hook │
                                          │   log_hook        │
                                          └───────┬──────────┘
                                                  │ (not blocked)
                                          ┌───────▼──────────┐
                                          │ TOOL_HANDLERS[x]  │
                                          └───────┬──────────┘
                                                  │
                                          ┌───────▼──────────┐
                                          │ trigger_hooks()   │
                                          │  PostToolUse:     │
                                          │   large_output    │
                                          └───────┬──────────┘
                                                  │
                                          results ──▶ back to messages
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import s03_permission.code as permission_code
from s04_hooks import utils
from s04_hooks import hooks

# 将所有 hook 注册到 HOOKS 字典中
utils.register_hook("UserPromptSubmit", hooks.context_inject_hook)
utils.register_hook("PreToolUse", hooks.permission_hook)
utils.register_hook("PreToolUse", hooks.log_hook)
utils.register_hook("PostToolUse", hooks.large_output_hook)
utils.register_hook("Stop", hooks.summary_hook)

# 在 agent_loop 中使用 hooks
def agent_loop(messages: list):
    while True:
        response = permission_code.tool_use_code.agent_loop_code.client.messages.create(
            model=permission_code.tool_use_code.agent_loop_code.MODEL,
            system=permission_code.tool_use_code.agent_loop_code.SYSTEM,
            messages=messages,
            tools=permission_code.tool_use_code.TOOLS,
            max_tokens=permission_code.tool_use_code.agent_loop_code.MAX_TOKEN,
        )
        messages.append({"role": "assistant", "content": response.content})
        if response.stop_reason != "tool_use":
            force = utils.trigger_hooks("Stop", messages)
            if force:
                messages.append({"role": "user", "content": force})
                continue
            return
        results = []
        for block in response.content:
            if block.type != "tool_use":
                continue
            # 在工具执行前执行 PreToolUse Hook
            blocked = utils.trigger_hooks("PreToolUse", block)
            # 如果 blocked 不为 None，则说明权限校验没通过
            if blocked:
                results.append({"type": "tool_result", "tool_use_id": block.id, "content": str(blocked)})
                continue
            handler = permission_code.tool_use_code.TOOL_HANDLERS.get(block.name)
            output = handler(**block.input) if handler else f"Unknown: {block.name}"

            # 在工具执行后执行 PostToolUse Hook
            utils.trigger_hooks("PostToolUse", block, output)
            results.append({"type": "tool_result", "tool_use_id": block.id, "content": output})
        messages.append({"role": "user", "content": results})

if __name__ == "__main__":
    print("s04: Hooks — 扩展逻辑交给 hooks，主循环保持干净")
    print("输入问题，回车发送。输入 q 退出。\n")
    history = []
    while True:
        try:
            query = input("\033[36ms04 >> \033[0m")
        except (EOFError, KeyboardInterrupt):
            break
        if query.strip().lower() in ("q", "exit", ""):
            break

        # 在用户提示词传递给大模型前执行 UserPromptSubmit Hook
        utils.trigger_hooks("UserPromptSubmit", query)
        history.append({"role": "user", "content": query})
        agent_loop(history)
        for block in history[-1]["content"]:
            if getattr(block, "type", None) == "text":
                print(block.text)
        print()