"""
tool use 在 agent loop 的基础上添加更多的工具 + 分发映射

本文件 = s01 的全部代码 + 以下新增:
  + run_read / run_write / run_edit / run_glob 四个工具实现
  + TOOL_HANDLERS 分发映射（替代 s01 中硬编码的 run_bash 调用）
  + safe_path 路径安全校验

核心循环机制代码完全一致
"""

# 加载 s01 中的配置
import s01_agent_loop.code as agent
from pathlib import Path

# 获取当前文件所在的目录
WORKDIR = Path.cwd()

def safe_path(p: str) -> Path:
    """
        将相对路径拼接至 WORKDIR 下，并确保结果未跳出工作目录。

        Args:
            p: 相对于 WORKDIR 的路径字符串

        Returns:
            规范化后的绝对 Path 对象

        Raises:
            ValueError: 路径经规范化后跳出了 WORKDIR（如包含 ``..`` 穿越）
    """
    # 将传入的相对路径拼接到 WORKDIR 下，resolve 展开为规范化的绝对路径
    path = (WORKDIR / p).resolve()

    # 判断 path 是否在 WORKDIR 目录下，若不在，则抛出一个错误
    if not path.is_relative_to(WORKDIR):
        raise ValueError(f"Path escapes workspace: {p}")

    # 若在，则返回合理的路径
    return path

def run_read(path: str, limit: int | None = None) -> str:
    """
       安全读取文件内容，支持限制返回行数。

       Args:
           path: 相对于 WORKDIR 的文件路径
           limit: 最大返回行数，None 或省略则返回全部

       Returns:
           文件内容字符串；超出 limit 时末尾追加行数提示；读取出错时返回错误信息
    """
    try:
        # 得到文件 Path，调用 read_text() 获取文件中的内容，再使用 splitlines() 将内容按照换行符进行分割成字符串数组
        lines = safe_path(path).read_text().splitlines()

        # 如果有读取的限制行数，则进行限制，并重新得到限制后的内容
        if limit and limit < len(lines):
            lines = lines[:limit] + [f"... ({len(lines) - limit} more lines)"]

        return "\n".join(lines)
    except Exception as e:
        return f"Error: {e}"

def run_write(path: str, content: str) -> str:
    """
        将内容安全写入工作目录下的文件，目录不存在时自动创建。

        Args:
            path: 相对于 WORKDIR 的目标文件路径
            content: 要写入的字符串内容

        Returns:
            写入成功的字节数及路径信息；出错时返回错误描述
    """
    try:
        # 转换为安全的 Path 对象
        file_path = safe_path(path)

        # 获取文件目录，同时当不存在目录时进行创建，存在时跳过
        # file_path.name 是目录下的文件名称
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # 写入数据
        file_path.write_text(content)

        # 返回相关信息
        return f"Wrote {len(content)} bytes to {path}"
    except Exception as e:
        return f"Error: {e}"

def run_edit(path: str, old_text: str, new_text: str) -> str:
    """
        安全替换文件中的文本，仅替换首次出现的位置。

        Args:
            path: 相对于 WORKDIR 的目标文件路径
            old_text: 要被替换的原始文本
            new_text: 替换后的新文本

        Returns:
            操作结果描述；原文本不存在时返回错误提示
    """
    try:
        # 得到 Path 对象
        file_path = safe_path(path)

        # 获取文件中的内容
        text = file_path.read_text()

        # 判断 old_text 是否在 text 中存在
        # 若不存在，则报错
        if old_text not in text:
            return f"Error: text not found in {path}"

        # 若存在，则将 new_text 替换 old_text，只替换一次
        file_path.write_text(text.replace(old_text, new_text, 1))

        return f"Edited {path}"
    except Exception as e:
        return f"Error: {e}"

def run_glob(pattern: str) -> str:
    """
        在 WORKDIR 下按模式匹配文件，返回所有命中路径。

        Args:
            pattern: glob 匹配模式，如 ``*.py``、``**/*.js``

        Returns:
            换行分隔的匹配路径列表；无匹配时返回 ``(no matches)``
    """
    import glob as g
    try:
        results = []

        # 得到匹配 pattern 的所有文件
        for match in g.glob(pattern, root_dir=WORKDIR):
            # 防止存在软链接指向外部文件
            if (WORKDIR / match).resolve().is_relative_to(WORKDIR):
                results.append(match)

        # 返回所有满足 pattern 文件的相对路径
        return "\n".join(results) if results else "(no matches)"
    except Exception as e:
        return f"Error: {e}"

# 工具定义
TOOLS = [
  {
    "name": "bash",
    "description": "Run a shell command.",
    "input_schema": {
      "type": "object",
      "properties": {
        "command": {
          "type": "string"
        }
      },
      "required": [
        "command"
      ]
    }
  },
  {
    "name": "read_file",
    "description": "Read file contents.",
    "input_schema": {
      "type": "object",
      "properties": {
        "path": {
          "type": "string"
        },
        "limit": {
          "type": "integer"
        }
      },
      "required": [
        "path"
      ]
    }
  },
  {
    "name": "write_file",
    "description": "Write content to a file.",
    "input_schema": {
      "type": "object",
      "properties": {
        "path": {
          "type": "string"
        },
        "content": {
          "type": "string"
        }
      },
      "required": [
        "path",
        "content"
      ]
    }
  },
  {
    "name": "edit_file",
    "description": "Replace exact text in a file once.",
    "input_schema": {
      "type": "object",
      "properties": {
        "path": {
          "type": "string"
        },
        "old_text": {
          "type": "string"
        },
        "new_text": {
          "type": "string"
        }
      },
      "required": [
        "path",
        "old_text",
        "new_text"
      ]
    }
  },
  {
    "name": "glob",
    "description": "Find files matching a glob pattern.",
    "input_schema": {
      "type": "object",
      "properties": {
        "pattern": {
          "type": "string"
        }
      },
      "required": [
        "pattern"
      ]
    }
  }
]

# 定义 handle，用于工具分发映射
TOOL_HANDLERS = {
    "bash": agent.run_bash,
    "read_file": run_read,
    "write_file": run_write,
    "edit_file": run_edit,
    "glob": run_glob,
}

# 重新实现 agent_loop ，在里面使用工具映射
def agent_loop(messages: list):
    while True:
        response = agent.client.messages.create(
            model=agent.MODEL, system=agent.SYSTEM, messages=messages,
            tools=TOOLS, max_tokens=agent.MAX_TOKEN,
        )
        messages.append(
            {
                "role": "assistant",
                "content": response.content
            }
        )
        if response.stop_reason != "tool_use":
            return
        results = []
        for block in response.content:
            if block.type == "tool_use":
                # block.name 得到的是调用工具的名称
                print(f"\033[33m> {block.name}\033[0m")
                handler = TOOL_HANDLERS.get(block.name)
                output = handler(**block.input) if handler else f"Unknown: {block.name}"
                print(str(output)[:200])
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
    print("s02: Tool Use — 在 s01 基础上加了 4 个工具")
    print("输入问题，回车发送。输入 q 退出。\n")
    history = []
    while True:
        try:
            query = input("\033[36ms02 >> \033[0m")
        except (EOFError, KeyboardInterrupt):
            break
        if query.strip().lower() in ("q", "exit", ""):
            break
        history.append(
            {
                "role": "user",
                "content": query
            }
        )
        agent_loop(history)
        for block in history[-1]["content"]:
            if getattr(block, "type", None) == "text":
                print(block.text)
        print()