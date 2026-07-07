> [参考文档](https://learn.shareai.run/zh/s04/)

# Hooks

在 s03 中，权限校验是放在 agent_loop 中的，如果需要添加更多的校验，又会修改 agent_loop，导致不好维护。

按照最初的设定，需要保持一个 loop 基础，其余的逻辑在 loop 基础上进行扩展。

这个机制通过 hook 实现，大白话就是在执行流程中插入多个关键的 hook，从而可以在需要的位置方便地拓展更多代码逻辑。

在此部分进行实现四个 hook 覆盖了 agent cycle 的关键节点：输入→执行前→执行后→退出。循环只负责调用 trigger_hooks()，具体逻辑全在 hook 回调里。