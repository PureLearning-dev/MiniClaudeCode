> [参考文档](https://learn.shareai.run/zh/s14/)

# Cron Scheduler

闹钟不需要你盯着它才会响。你设好早上 7:00，到点它自己响——你在睡觉、在洗澡、在做饭，它都照响不误。Agent 也一样。"每天早上 9 点跑测试"、"每 30 分钟检查 CI 状态"，这些周期性任务不该每次都需要人来手动触发。s13 让 Agent 能后台执行慢操作，但所有的起点仍然是用户说一句、Agent 动一下。如果用户忘了说，Agent 就永远不动。

回到前面几章，从 s01 到 s13，Agent 的运行模式一直是"被动响应"：用户在终端输入一句话，Agent 开始思考、执行、返回结果，然后等待下一句。如果所有任务都是即时触发的，被动模式倒也没什么问题——你问天气、Agent 查了告诉你，整个过程是自然的对话节奏。但一旦工作里混进了"每天早上汇总未读邮件"、"每小时检查服务健康状态"这种周期性的需求，被动模式就不够用了。解决方式就是给 Agent 装一个闹钟——一个独立的调度线程，按 cron 表达式触发任务，不需要人等，也不等人催。

工作原理分四层：

- 第一层，调度线程（Scheduler）。 一个独立的 daemon 线程，每秒轮询一次当前时间。它遍历所有已注册的定时任务，用 cron_matches 判断"现在是不是该触发了"。该触发就把任务塞进 cron_queue。这是一条完全独立于 agent_loop 的时间线——即使 Agent 正在执行别的任务、甚至 Agent Loop 根本没在跑，调度线程也在后台忠实地滴答。
- 第二层，队列（Queue）。 调度线程只负责生产——把到时间的任务扔进 cron_queue。队列本身只是一个 Python 列表，配合 cron_lock 保证线程安全。调度线程不负责交付，它只负责说"这个任务到点了"。怎么交付、什么时候交付，是下一层的事。
- 第三层，队列处理器（Queue Processor）。 另一个独立线程，每 0.2 秒检查一次队列。队列非空且 Agent 空闲（通过 agent_lock 判断），就拉起一轮 agent_loop。如果 Agent 在忙——正在执行用户触发的任务——队列处理器就等着，不打断。agent_lock.acquire(blocking=False) 是关键：拿不到锁就下次再说，不阻塞、不强插。这保证了定时任务不会打断正在进行的用户交互。
- 第四层，消费者（agent_loop）。 agent_loop 不关心时间、不关心调度。它只做一件事：从 cron_queue 里把已触发的任务取出来，注入到 messages 里。格式是 "[Scheduled] {prompt}"——Agent 看到这条消息就像看到用户输入一样，正常思考、执行、返回。对 Agent 来说，定时触发和手动输入没有区别，只是消息来源不同。

四层之间的关系： 生产者（调度线程）、交付者（queue processor）和消费者（agent_loop）通过 cron_queue、cron_lock 和 agent_lock 三个组件解耦。调度线程不知道 Agent 在干什么，queue processor 不知道现在几点钟，agent_loop 不知道任务是谁触发的。每一层只关心自己的职责，互不侵入。

CronJob 数据结构：

每个定时任务是一个 CronJob 对象，包含五个字段。id 是唯一标识符，用于查找和删除。cron 是五段式 cron 表达式，精确描述触发时间。prompt 是触发时注入给 Agent 的消息。recurring 标记是周期性还是仅一次。durable 标记是否写入磁盘跨重启保留。

Cron 表达式：Unix 用了 50 年的时间描述语言。 五段式：分钟、小时、日、月、星期。0 9 * * * 是每天早上九点，*/5 * * * * 是每五分钟，0 9 * * 1-5 是工作日早上九点。支持通配符 *、步长 */N、范围 N-M，以及逗号分隔的多个值。

cron_matches 匹配逻辑： 分钟、小时、月必须全部匹配。日（DOM）和星期（DOW）的关系遵循 Unix cron 标准——两者同时被约束时，任一匹配即触发（OR 语义）。两个都没约束（都是 *），直接匹配。只有一个被约束，以被约束的为准。这个细节防止了"设了每月 15 号但也设了每周一"这种场景下的匹配冲突。

独立调度线程的关键设计： 用 "YYYY-MM-DD HH:MM" 格式的分钟标记防重复触发——同一分钟内多次轮询不会重复入队，但又不像简单布尔标记那样会在第二天跳过。每个 job 独立 try/except，一个坏 job 不会拖垮整个调度线程。一次性任务触发后自动删除，不再占用调度资源。

Durable vs Session-only： Durable 的任务定义写入 .scheduled_tasks.json，Agent 重启后自动恢复。Session-only 的只在内存里，Agent 关闭就消失。但要注意一个前提：cron 调度器必须在 Agent 进程内跑。进程关了，调度也停。Durable 只保证任务定义不丢，下次启动时调度器会补触发。如果需要"进程不跑也能到点执行"，得用系统的 crontab 或 systemd timer——那超出了 Agent 内部调度的范畴。

一个完整的生命周期：

启动时，load_durable_jobs() 从 .scheduled_tasks.json 恢复持久化任务，调度线程和队列处理器线程同时启动。注册一个任务只需要一行 schedule_cron(cron="*/2 * * * *", prompt="run date")，CronJob 写入内存字典和磁盘文件。每两分钟，调度线程检测到匹配，任务进入 cron_queue。队列处理器发现队列非空且 Agent 空闲，拉起 agent_loop。Agent 收到 "[Scheduled] run date"，就像收到用户消息一样，执行 date 命令。关闭进程，调度线程随 daemon 退出。.scheduled_tasks.json 还在磁盘上。下次启动，任务恢复。