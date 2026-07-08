> [参考文档](https://learn.shareai.run/zh/s06/)

# Subagent

Agent 系统如果将所有工具的调用和操作都放在主线程中进行执行的话，会让上下文中的信息变得非常复杂，大模型会因此变笨。

我们可以设计一个 subagent 概念，让这个 subagent 去执行主线程需要执行的任务，当 subagent 完成后，返回这个执行的结果，这个 subagent 的上下文是与主线程隔离的。

为了保证 subagent 不陷入大量的循环，可以在设置一个循环的上限值。

实现一个工具给主线程，让其可以创建一个 subagent 去执行需要执行的任务。