> [参考文档](https://learn.shareai.run/zh/s11/)

# Error Recovery

Agent 在运行中，调用其他 api、token 不足、临时故障等情况都可能导致错误，如果 Agent 没有出现错误的应对措施，会很容易导致 Agent 运行中断，从而任务得不到理想的结果。

真实使用中，不可能一出现错误就导致中断，所以我们需要有重试机制，使用 try except 将核心 loop 进行包裹，判断具体是什么错误，去执行对应的逻辑。

在这里的实现，使用 with_try() 处理瞬态错误，api 异常使用 try except 进行包裹，token 超出由 stop_reason 判断，然后进行处理。
