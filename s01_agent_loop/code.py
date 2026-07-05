"""
实现一个最简单的 Agent Loop！

+----------+      +-------+      +---------+
|   User   | ---> |  LLM  | ---> |  Tool   |
|  prompt  |      |       |      | execute |
+----------+      +---+---+      +----+----+
                      ^               |
                      |   tool_result |
                      +---------------+
                      (loop continues)

使用方式：
1. uv add anthropic python-dotenv
2. DEEPSEEK_API_KEY=...
3. uv run python s01_agent_loop/code.py
"""

import os, subprocess

from anthropic import Anthropic
from dotenv import load_dotenv

try:
    # input() 提示符里正常输入中文和使用编辑快捷键
    # 可以让用户在终端输入时更加快捷方便
    import readline
    # macOS 的 libedit 在处理中文输入时有退格问题，这四行修复它
    readline.parse_and_bind('set bind-tty-special-chars off')
    readline.parse_and_bind('set input-meta on')
    readline.parse_and_bind('set output-meta on')
    readline.parse_and_bind('set convert-meta off')
except ImportError:
    pass

MAX_TOKEN = 8000

# load_dotenv 做的事是把 .env 文件里的 KEY=VALUE 逐行加载到 os.environ 中。默认情况下它不会覆盖已有的值——如果系统已经设了 OPENAI_API_KEY，.env 里的同名键就被忽略。
load_dotenv(override=True)

# 当本地配置了第三方服务，则需要删除官方的认证 TOKEN
if os.getenv("ANTHROPIC_BASE_URL"):
    os.environ.pop("ANTHROPIC_AUTH_TOKEN", None)

# 创建 Anthropic 客户端
client = Anthropic(base_url=os.getenv("ANTHROPIC_BASE_URL"))

# 大模型系统 Prompt
SYSTEM = f"You are a coding agent at {os.getcwd()}. Use bash to solve tasks. Act, don't explain."

# 得到模型名称
MODEL = os.getenv("MODEL_ID")
if not MODEL:
    raise ValueError("MODEL_ID 未设置，请确认是否配置第三方模型，如果需要，请在 .env 中进行配置")

# 定义工具——只存在 bash ，因为我们需要实现的是一个最简单的 Agent
# 满足 Anthropic 规范
TOOLS = [
    {
        "name": "bash",
        "description": "Run a shell command.",
        "input_schema": {
            "type": "object",
            "properties": {"command": {"type": "string"}},
            "required": ["command"],
        },
    }
]

# -- 工具执行 -- 相当于实现 TOOLS 中定义的工具
def run_bash(command: str) -> str:
    dangerous = ["rm -rf /", "sudo", "shutdown", "reboot", "> /dev/"]

    # 一旦危险命名出现在 command 中，直接退出
    if any(x in command for x in dangerous):
        return "Error: Dangerous command blocked"

    # 执行 shell 命令并返回得到的结果
    try:
        # subprocess.run(command, ...) 启动一个子进程，在 shell 里执行 command。执行期间你的 Python 程序是阻塞的——等命令跑完才继续往下走。返回值 r 是一个 CompletedProcess 对象，里面装着执行结果的所有信息。
        r = subprocess.run(command, shell=True, cwd=os.getcwd(), capture_output=True, text=True, timeout=120)
        out = (r.stdout + r.stderr).strip()
        return out[:50000] if out else "(no output)"
    except subprocess.TimeoutExpired:
        return "Error: Timeout (120s)"
    except (FileNotFoundError, OSError) as e:
        return f"Error: {e}"

# -- Agent 核心运行模式 --

def agent_loop(messages: list) -> None:
    while True:
        # 发送数据给大模型并得到大模型返回到结果
        res = client.messages.create(model = MODEL, system = SYSTEM, messages = messages, tools = TOOLS, max_tokens = MAX_TOKEN,)

        # 判断是否需要执行工具，不需要的话，直接 return
        if res.stop_reason != 'tool_use':
            return

        # 添加大模型的信息到记录里
        messages.append({"role": "assistant", "content": res.content})

        # 执行大模型需要调用的所有工具
        results = []
        # res.content 中的内容是一块一块的，每一块中有 type 属性，决定其是否需要工具调用
        for block in res.content:
            if block.type == 'tool_use':
                # 大模型通过 tools 中的工具定义的参数进行返回参数值，将约定的参数名作为 key
                # 可以在 block.input 中通过 key 进行访问
                print(f"\033[33m$ {block.input['command']}\033[0m")
                output = run_bash(block.input["command"])
                print(output[:200])
                results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": output,
                })

        # 将工具得到的结果传入到记录中
        messages.append({"role": "user", "content": results})

# 当这个文件直接被运行时改判断为 True，例如： python xxx.py 或者 uv run python xxx.py 等
if __name__ == '__main__':
    print('-- [s01] Agent Loop --')
    print("输入问题，回车发送。输入 q 退出。\n")

    history = []

    while True:
        try:
            query = input("\033[36ms01 >> \033[0m")
        except (EOFError, KeyboardInterrupt):
            break

        if query.strip().lower() in ("q", "exit", ""):
            break

        history.append({"role": "user", "content": query})

        agent_loop(history)

        # 处理大模型回复的最后一条内容
        response_content = history[-1]["content"]

        # 只处理大模型返回的内容，换句话说，大模型返回的一定是 list，而用户的输入是 str
        if isinstance(response_content, list):
            for block in response_content:
                if getattr(block, "type", None) == "text":
                    print(block.text)

        print()
