> [参考文档](https://learn.shareai.run/zh/s01/)

# Agent Loop

一个最简单的 Agent 只需要一个循环和 Bash 则可，循环判断是否仍然满足终止的条件，Bash 用于执行需要的命令。

这样做的原因是为了去掉人的“中间件”身份，让 Bash 和 LLM 之间可以自动化地执行。

LOOP 核心：一个 while True 循环，模型调用工具 -> 执行 -> 喂回 -> 再问。直到不再调用工具为止，这个循环是后续各种机制的基础。


