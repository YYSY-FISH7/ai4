# 2026-11-16 M5发送侧人工OBS验收归档

这两项均为**历史真实Gazebo检测数据回放→当前原M5重新计算航迹→原接收节点**，不是新Gazebo实时测试、人工航迹或完整飞行验收。本次只归档既有证据，没有重跑。

- [M5→M6 PID接收、归零与恢复](M5-M6/readme.md)：视频05。
- [M5→M8视觉缓存接收、读取与恢复](M5-M8/readme.md)：视频06。
- [五段正式视频名称/原名/大小/时长/SHA索引](../../../../design_module/M5/模块说明文档/五段视频证据索引-20261116.json)。原视频由用户另行发群，不在Git；相同SHA即可核对原件，不把本机绝对路径当分享链接。
- bag-index.json记录六个原bag的VM路径、SHA和全部消息读出统计，bag原件在Windows维护归档及原VM会话，不放Git。
- event-recount.json是原始事件独立重计数；code-hash-audit.json区分VM文件哈希、Windows CRLF与c421 Git blob。source-script-hashes.json记录实际运行辅助脚本SHA，提交脚本与VM原/tmp文件逐字节一致。
- acceptance-record.json记录用户已确认最终核验报告并授权归档。原始日志中的human_verdict=null及旧PR状态保留其原时点，不能据此覆盖最新确认，也不能反向改旧日志伪造签认。

本目录只提供M5发送侧资料，不替代接收方test/flow/M5-M6或M5-M8的正式验收签认。M6默认尺寸、M8自然锁定/T4、T1及完整飞行仍待对应负责人。实际M5→M6录像以05为准，旧人工输入节点记录不计入正式录像。

## 证据边界

原始events、player/record/node日志、phase和parameters保持原内容。表格中的观察器计数/录包计数窗口不同；M8原进程审计与外部审计话题也分开，不能混写成无消息损失或严格同帧。profile观察会引入开销，不是性能基准。

source-manifest.json记录当前归档文件及SHA；旧第二周manifest仅适用于原快照和其换行方式，不把有意纠正文档当原始实验数据。

原始终端player日志含回车进度行与尾随空格，不为美化而修改；本目录.gitattributes对归档文件保留原始换行字节以匹配来源SHA，仅对两组原始log关闭空白格式检查；脚本与说明仍执行常规格式检查并识别原CRLF行尾，不改变功能验收标准。
