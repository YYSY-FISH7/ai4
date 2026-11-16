# M5→M6：历史真实输入回放下的节点级接收与恢复

视频：05_M5-M6_PID接收与丢失恢复.mp4，原名2026-11-16 17-09-21.mp4。100.6833秒、60fps、6041帧全部可读，SHA-256 `df2e0697443990d35da73dcbcfe8b1a1b26610256719163765645b3866c807fa`。原件另行群聊交付，未剪辑/转码。

数据源：`/home/demo/m4-ort1-exit-reentry.NeAllp/live.bag`，SHA `139009ec869407a1871a4b2b0fa8f1f7420b6bd68b054d06d301320e0af912ea`。只播放真实相机/检测，原M5现在运行并输出/visual/tracks，由原M6节点消费，未播放旧航迹或注入人工航迹。独立master；仅运行时指定M5尺寸及M6 image_width/height=320/240，未改M6源码或正式配置，无飞控/仲裁。

|阶段|M5航迹/非空|监视器PID总数/非零|bag PID总数/非零|
|---|---:|---:|---:|
|存在|38/11|1110/110|926/110|
|离场|41/0|1103/0|935/0|
|重入|38/13|1081/131|918/131|

1103与935是不同采集窗口，均全零；不当成精确15秒FPS。恢复有IDs6–10，存在IDs1–5，不能宣称身份稳定。`log/events.jsonl`、`final-stats.json`与`final-bag-audit.json`分别提供观察/录包证据；image/contact-sheet.jpg显示三阶段和结束。三个bag均已完整读出，原件路径/校验见上级bag-index.json。原M5/M6日志未见Traceback/ERROR/FATAL，不据此声称所有旧会话零告警。

## 已执行流程与复现（本次归档不自动执行）

复用Ubuntu20.04/ROS Noetic、既有编译消息和mavros_msgs，不需要YOLO或新Gazebo。原运行脚本在python/manual_m5_m6_auto.py，固定读取以上源bag与`/home/demo/ai4-m4-m5-formal-20261116`正式节点。其他机器先准备同版本源码/消息和真实数据；这些绝对路径是原VM定位，不是公开下载链接。

```bash
cd /home/demo/ai4-m4-m5-formal-20261116
source /opt/ros/noetic/setup.bash
source catkin_ws/devel/setup.bash
export DISPLAY=:0 XAUTHORITY=/home/demo/.Xauthority
/usr/bin/python3 -B test/visual_tracker/downstream-reference/manual-20261116/M5-M6/python/manual_m5_m6_auto.py
```

脚本创建本项独立ROS master和唯一证据目录，启动原M5、原M6及监视窗口；不是额外连接其他人的master。用户先准备OBS，再点击窗口开始；10秒倒计时后自动播放源bag偏移100/120/150秒各15秒，阶段间3秒，M5/M6不重启；终点显示可停止录制，等待用户确认。用窗口“停止本项测试”或在打印出的SESSION目录创建stop.request，只清理自有进程、正常封包。没有自动判断人工通过。

结论：历史真实检测回放下，M5→M6节点级接收、离场归零与重入恢复有证据。不是新Gazebo、同次实时YOLO链或物理飞行闭环。正式M6接收方确认及默认640×480→实际320×240适配仍由M6负责人完成。
