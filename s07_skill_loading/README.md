> [参考文档](https://learn.shareai.run/zh/s07/)

# Skill Loading

当在实现一个目标时需要各种知识，如果将这些知识全部放入到大模型的上下文中，在执行某一步时，这些知识中的大部分都不会用到，从而导致浪费 token 和更容易出现幻觉。

为了解决这个痛点，我们需要使用 skill，skill 将知识进行抽取，放入一个单独的文件中，当大模型判断需要这个知识时，才进行真正意义上的读取。

那么这里就需要在 MiniClaudeCode 启动时将有的 SKILL 和其描述注入到 SYSTEM_PROMPT 中，并实现一个 load_skill 工具，用于读取具体的 SKILL。

这样，一开始大模型就会知道有什么 SKILL，并且知道每个 SKILL 的元数据，当需要调用对应知识时，就使用 load_skill(name) 通过传入 SKILL 的 name 获取对应的内容。