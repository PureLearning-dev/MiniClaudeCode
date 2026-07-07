"""
permission 验证在本地执行的大模型输出的操作

+-------+    +--------+    +--------+    +--------+    +------+
| Tool  | -> | Gate 1 | -> | Gate 2 | -> | Gate 3 | -> | Exec |
| call  |    | deny?  |    | match? |    | allow? |    |      |
+-------+    +--------+    +--------+    +--------+    +------+
   |            |             |             |
   v            v             v             v
(normal)     (blocked)    (ask user)   (user says no?)
"""
import s02_tool_use.code as tool_use_code


# GATE1: 直接拒绝的命令集合，这里使用硬编码是为了理解逻辑，但是真实场景中，相同的命令功能可以有许多变体
# 在 cc 源码中使用 多文件 来源进行确认命令是否直接拒绝
DENY_LIST = ["rm -rf /", "sudo", "shutdown", "reboot", "mkfs", "dd if=", "> /dev/sda"]
DESTRUCTIVE = ["rm ", "> /etc/", "chmod 777"]

def check_deny_list(command: str) -> str | None:
    """
        检查 command 是否命中拒绝名单。

        遍历 DENY_LIST，以子串匹配方式判断 command 中是否包含任一被禁
        模式。命中时立即返回对应的阻止信息；全部未命中则返回 None。

        Args:
            command: 待检查的命令字符串。

        Returns:
            命中拒绝名单时返回 "Blocked: '<pattern>' is on the deny list"，
            否则返回 None。
    """
    # 遍历 DENY_LIST
    for pattern in DENY_LIST:
        # 判断需要执行的 command 中是否存在 DENY_LIST 中的命令
        if pattern in command:
            return f"Blocked: '{pattern}' is on the deny list"

    return None

# GATE2: 规则匹配，匹配到的需要询问用户
PERMISSION_RULES = [
    {
        "tools": ["write_file", "edit_file"],
        "check": lambda args: not (tool_use_code.WORKDIR / args.get("path", "")).resolve().is_relative_to(tool_use_code.WORKDIR),
        "message": "Writing outside workspace"
    },
    {
        "tools": ["bash"],
        "check": lambda args: any(kw in args.get("command", "") for kw in DESTRUCTIVE),
        "message": "Potentially destructive command"
    },
]

def check_rules(tool_name: str, args: dict) -> str | None:
    """
        检查 tool_name 与 args 是否命中权限规则。

        遍历 PERMISSION_RULES，若 tool_name 命中某条规则所管辖的工具列表
        且该规则的 check 函数对 args 返回 True，则返回对应的 message；
        全部规则均未命中时返回 None。

        Args:
            tool_name: 工具名称。
            args:     传递给工具的参数字典，直接传入 check 函数进行校验。

        Returns:
            命中规则时返回 rule["message"] 的字符串，否则返回 None。
    """
    for rule in PERMISSION_RULES:
        # 判断工具是否命中和工具对应参数是否满足条件
        if tool_name in rule["tools"] and rule["check"](args):
            return rule["message"]
    return None

# Gate 3: 用户审核
def ask_user(tool_name: str, args: dict, reason: str) -> str:
    """
        向用户询问是否允许执行某个工具调用。

        以警告样式打印原因和工具信息，等待用户输入 y/yes 或 N，
        默认返回 "deny"。

        Args:
            tool_name: 工具名称。
            args:     工具的参数字典。
            reason:   拦截原因，用于提示用户。

        Returns:
            用户确认时返回 "allow"，否则返回 "deny"。
    """
    print(f"\n\033[33m⚠  {reason}\033[0m")
    print(f"   Tool: {tool_name}({args})")
    # strip() 去掉首尾多余的字符
    choice = input("   Allow? [y/N] ").strip().lower()
    return "allow" if choice in ("y", "yes") else "deny"

# 管线：将 GATE 1 到 GATE 3 到限制串联起来
def check_permission(block) -> bool:
    """
        对代码块进行权限校验，返回是否允许执行。

       依次执行两级检查：
           1. 黑名单检查：若 block 为 bash 命令且命中 DENY_LIST，直接拒绝。
           2. 规则检查：匹配 PERMISSION_RULES，命中时弹询问用户确认。

       Args:
           block: 待校验的代码块对象，需包含 name 和 input 属性。

       Returns:
           校验通过返回 True，被拒绝或用户否定返回 False。
    """
    # 如果 block 是一个调用 bash 到回复，则进入 GATE 1
    if block.name == "bash":
        # 获取 command 参数对应的值
        reason = check_deny_list(block.input.get("command", ""))
        # 判断是否在 DENY_LIST，在则返回 False
        if reason:
            print(f"\n\033[31m⛔ {reason}\033[0m")
            return False

    # 进行规则匹配
    reason = check_rules(block.name, block.input)

    # 判断是否有用户审核的命令，有则进行询问
    if reason:
        decision = ask_user(block.name, block.input, reason)
        if decision == "deny":
            return False
    return True


# 在 s02 的基础上添加一个权限校验模块
def agent_loop(messages: list):
    while True:
        # 通过 messages 得到大模型的回复
        res = tool_use_code.agent.client.messages.create(
            model=tool_use_code.agent.MODEL,
            system=tool_use_code.agent.SYSTEM,
            tools=tool_use_code.agent.TOOLS,
            messages=messages,
            max_tokens=tool_use_code.agent.MAX_TOKEN
        )

        # 将大模型的回复添加到 messages 中
        messages.append(
            {
                "role": "assistant",
                "content": res.content
            }
        )

        # stop_reason 表示模型为什么停止生成，也就是本次回复的终止原因。
        # 这里确定此次回复中一定存在工具调用
        if res.stop_reason != "tool_use":
            return

        results = []
        # 权限校验后执行 res 中的工具调用
        # content 里面存放着模型本轮回复的每一项内容。它是一个 list，每个元素代表一个 content block。
        for block in res.content:
            # 这里确定这个 block 是否为一个工具的调用 block
            if block.type != "tool_use":
                continue

            print(f"\033[36m> {block.name}\033[0m")

            # 权限校验模块
            if not check_permission(block):
                # 被拒绝或者直接不能执行
                results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": "Permission denied."
                    }
                )
                continue

            # 执行工具调用
            # block.name 是工具的名称
            handler = tool_use_code.TOOL_HANDLERS.get(block.name)

            output = handler(**block.input) if handler else f"Unknown: {block.name}"

            print(output[:200])

            results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": output
                }
            )

        messages.append(
            {
                "role": "user",
                "content": results
            }
        )

if __name__ == "__main__":
    print("s03: Permission")
    print("输入问题，回车发送。输入 q 退出。\n")
    history = []
    while True:
        try:
            query = input("\033[36ms03 >> \033[0m")
        except (EOFError, KeyboardInterrupt):
            break
        if query.strip().lower() in ("q", "exit", ""):
            break
        history.append({"role": "user", "content": query})
        agent_loop(history)
        for block in history[-1]["content"]:
            if getattr(block, "type", None) == "text":
                print(block.text)
        print()

