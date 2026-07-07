from s02_tool_use.code import TOOLS, TOOL_HANDLERS
import ast, json

# 当前正要执行的 TOOL 集合
CURRENT_TODOS: list[dict] = []

def _normalize_todos(todos):
    """校验并标准化 task list 参数。

    支持三种入参格式：list、JSON 字符串、Python 字面量字符串。
    校验每个 todo 必须是 dict，且包含 content 和 status 字段，
    status 值仅限 'pending'、'in_progress'、'completed'。

    Args:
        todos: 任务列表，可以是 list / JSON 字符串 / Python 表达式字符串。

    Returns:
        (list | None, str | None):
            校验通过时返回 (标准化后的 list, None)；
            校验失败时返回 (None, 错误信息字符串)。
    """
    # 如果是字符串，尝试 JSON 解析，再尝试 ast.literal_eval
    if isinstance(todos, str):
        try:
            # 从 string 中转换字符串为 Python 对象
            todos = json.loads(todos)
        except json.JSONDecodeError:
            try:
                # json 不能转换再使用 ast 进行兜底
                # 将传入 todos 转换为 Python 对象
                todos = ast.literal_eval(todos)
            except (SyntaxError, ValueError):
                return None, "Error: todos must be a list or JSON array string"

    # 必须是 list
    if not isinstance(todos, list):
        return None, "Error: todos must be a list"

    # 逐个校验每个元素
    # enumerate(todos) 这个函数将 todos 中的 item 给上一个索引
    # 将 todos 中 index 和 item 取出来
    for i, t in enumerate(todos):
        # item 必须是 dict
        if not isinstance(t, dict):
            return None, f"Error: todos[{i}] must be an object"
        # item 中必须有 content 和 status 属性
        if "content" not in t or "status" not in t:
            return None, f"Error: todos[{i}] missing 'content' or 'status'"
        # item 中的 status 必须在 ("pending", "in_progress", "completed") 中
        if t["status"] not in ("pending", "in_progress", "completed"):
            return None, f"Error: todos[{i}] has invalid status '{t['status']}'"

    return todos, None

def run_todo_write(todos: list) -> str:
    global CURRENT_TODOS
    todos, error = _normalize_todos(todos)
    if error:
        return error
    CURRENT_TODOS = todos
    lines = ["\n\033[33m## Current Tasks\033[0m"]
    for t in CURRENT_TODOS:
        icon = {"pending": " ", "in_progress": "\033[36m▸\033[0m", "completed": "\033[32m✓\033[0m"}[t["status"]]
        lines.append(f"  [{icon}] {t['content']}")
    print("\n".join(lines))
    return f"Updated {len(CURRENT_TODOS)} tasks"

# 添加 todo_write 工具定义
TOOLS.append(
    {
        "name": "todo_write",
        "description": "Create and manage a task list ...",
        "input_schema": {
            "type": "object",
            "properties": {
                "todos": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "content": {
                                "type": "string"
                            },
                            "status": {
                                "type": "string",
                                "enum": ["pending", "in_progress", "completed"]
                            },
                        },
                    },
                },
            },
        }
    }
)

TOOL_HANDLERS["todo_write"] = run_todo_write