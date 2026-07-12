> [参考文档](https://learn.shareai.run/zh/s10/)

# System Prompt

之前实现的代码中的 SYSTEM_PROMPT 都是硬编码，不会根据项目中已有的内容进行动态组装，这样会导致 SYSTEM_PROMPT 中提到的有些内容被浪费，并且修改也很麻烦。

随着 Agent 中的上下文信息、工具、skill 等越来越多，会让 SYSTEM_PROMPT 更重，如果仍然是人工编写，只会增加出错的概率。

SYSTEM_PROMPT 必须根据运行时状态进行组装。

为了更好地组装 SYSTEM_PROMPT，将其分为 4 个部分：

- identity：始终加载，表明 LLM 的身份
- tools：始终加载，为可用的 tools
- workspace：始终加载，表明工作的目录
- memory：按需加载，关于记忆的内容，有 MEMORY.md 才加载

将整个 SYSTEM_PROMPT 拆分后，不仅可以更好地进行维护，而且修改一个部分的内容，不会影响其他 section。

需要维护一个 context，用于判断缓存是否命中，当命中，则直接返回 context，否则重新组装 SYSTEM_PROMPT。