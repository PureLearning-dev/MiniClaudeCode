> [参考文档](https://learn.shareai.run/zh/s15/)

# Agent Team

在实现大型复杂的需求时，会同时进行多种不同方面的操作，这些上下文内容如果全部放在一个 Agent 中，会导致混乱。

这个时候，我们就需要“队友” Agent，也可以称为下手，让一个 Agent 作为 Leader，管理多个下手 Agent 进行完成任务，这个和之前学习的 subagent 不同。

这里的下手 Agent 是可以存活多轮，并且可以相互通信。这种管理 Agent 的方式和真实世界中的团队管理是一致的。

为了实现这个机制，需要每个 Agent 有自己邮箱，Leader Agent 和 手下Agent 进行信息的交流时，往对应 Agent 的邮箱中写入要发送的数据，读取后进行删除。

启动的每个手下 Agent 都有自己的上下文，可以视为一个完整的 Agent。

在每次循环结束后检查邮箱中的数据，并放入 history 中，这就是 inbox，Leader Agent 中得到手下 Agent 的信息后，就可以由此发布新的任务。