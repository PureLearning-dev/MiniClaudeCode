> [参考文档](https://learn.shareai.run/zh/s13/)

# Background Tasks

想象你在家做家务。洗衣机转了 45 分钟，你不会站在洗衣机前面盯着它转——你会趁这段时间煮饭、烧水、扫地。这是并行：几件事同时推进。等洗衣机响铃了，你过去把衣服拿出来，和已经煮好的饭一起收工。

Agent 也一样。npm install 跑 10 分钟，Agent 在这 10 分钟里完全能去读配置文件、写 README、检查代码风格——但这些活必须等 Agent 主循环空出来才能做。如果 subprocess.run 同步阻塞，主循环就僵在安装命令上，Agent 什么都干不了。这是串行的代价：一个慢任务卡住，后面所有快任务全排队。

回到前面几章，所有任务的执行都是串行的。如果任务都很快，串行倒也没什么问题——读文件毫秒级，git status 一秒内返回，Agent 几乎感觉不到等待。但一旦任务里混进了 npm install、pytest、docker build 这种分钟级的慢操作，串行就成了瓶颈。解决方式就是把长时间执行的任务丢到另一个线程，主线程继续跑，慢任务完成了再把结果返回。

工作原理分四步：

- 第一步，判断哪些任务该后台跑。 优先听模型的——bash 工具的 input_schema 里有一个 run_in_background: boolean 参数，模型显式标记"这个慢，后台跑"。模型没说的话，代码用关键词启发式兜底——命令里包含 install、build、test、deploy 等字眼，大概率是慢操作，也扔后台。
- 第二步，启动后台线程。 决定丢后台后，把命令包装成 worker 函数，塞进 daemon 线程执行。主线程立刻恢复。同时在全局字典里登记这个任务：唯一 ID、状态（running）、对应哪个 tool_use。然后给 Agent 返回占位回复："后台任务 bg_0001 已启动"。daemon=True 保证 Agent 进程退出时这些线程跟着退出，不留僵尸。
- 第三步，Agent 继续跑循环。 Agent 收到占位回复后知道 npm install 还在跑，但它不等着，下一轮继续决策——读配置、写文件、回应用户。这和同步模式形成鲜明对比：同步模式 Agent 只能盯着洗衣机转，后台模式下洗衣机在转，Agent 在厨房煮饭。
- 第四步，完成后回注通知。 后台线程跑完了，状态改成 completed。主循环下一个回合调用 collect_background_results() 检查有没有已完成的后台任务，有的话格式化成 <task_notification> XML 注入对话，和当前轮的工具结果合并成一条 user 消息。Agent 在同一条消息里同时看到"安装完成了"和"刚才读的配置内容"，无缝衔接。

一个完整的两轮交互：

第一轮 Agent 说"我先装依赖"→ 模型返回 bash "npm install" 且 run_in_background: true → 代码扔到后台线程，返回 "[Background task bg_0001 started]" → 模型收到后说"好的，安装跑后台，我先去看看配置文件"。

第二轮 Agent 说"读 package.json"→ read_file 同步返回文件内容。同时 collect_background_results() 发现 bg_0001 跑完了 → 把 <task_notification> 和读文件结果一起塞进同一条 user 消息 → Agent 同时收到配置文件内容和安装成功的通知。

Agent 没干等。npm install 跑后台的时候，它去读了配置文件。串行要 12 分钟的事，后台模式 10 分钟搞定——那 10 分钟安装和读文件是重叠的。

