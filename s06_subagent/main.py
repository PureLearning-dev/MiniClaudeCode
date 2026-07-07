#!/usr/bin/env python3
"""
main — REPL entry point for the s06 modular agent.

Run:  cd s06_modular && python main.py
Needs: pip install anthropic python-dotenv + ANTHROPIC_API_KEY in .env
"""
try:
    import readline
    readline.parse_and_bind("set bind-tty-special-chars off")
except ImportError:
    pass

from agent import agent_loop
from hooks import trigger_hooks


def main():
    print("s06: Subagent — spawn sub-agents with fresh context, summary only")
    print("Type a question, press Enter. Type q to quit.\n")

    history = []
    while True:
        try:
            query = input("\033[36ms06 >> \033[0m")
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


if __name__ == "__main__":
    main()
