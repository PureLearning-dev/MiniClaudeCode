# 定义 HOOKS
HOOKS = {
    "UserPromptSubmit": [],
    "PreToolUse": [],
    "PostToolUse": [],
    "Stop": []
}

def register_hook(event: str, callback):
    """注册一个回调函数到指定事件上。

    Args:
        event: 事件名称，对应 HOOKS 字典中的键。
        callback: 事件触发时要执行的回调函数。
    """
    HOOKS[event].append(callback)


def trigger_hooks(event: str, *args):
    """
    触发指定事件的所有已注册回调。

    按注册顺序依次调用，若某个回调返回非 None 值则短路返回该结果，
    不再执行后续回调；全部返回 None 时最终返回 None。

    Args:
        event: 事件名称。
        *args: 传递给每个回调函数的位置参数。

    Returns:
        第一个非 None 的回调返回值，若无则返回 None。
    """
    for callback in HOOKS[event]:
        result = callback(*args)
        if result is not None:  # 返回值 ≠ None → hook 说"停"
            return result
    return None
