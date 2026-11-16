# 状态机受控节点验证与视觉链路证据

录像03为隔离人工受控消息→原M8接收类，用于N/M/K状态切换；不代表自然VISUAL_LOCK或飞行闭环。录像02为真实M0/M4/M5实时跟踪，正式接收资料见test/flow/M4-M5。有效M5→M6与M5→M8录像为05、06，见test/visual_tracker/downstream-reference/manual-20261116。

复现03：source /opt/ros/noetic/setup.bash、已有Catkin消息，export DISPLAY=:0后运行 `/usr/bin/python3 -B -u python/manual_receiver_demo.py 3`。该脚本为历史共用工具，保留原内容；只将此处明确指定的状态机演示作为正式证据入口。独立master，不接飞控，OBS由用户操作。结束关闭窗口清理自有进程。

log保留对应的有效原始记录，image只展示本目录正式状态机录像。当前正式视频全集仅01、02、03、05、06，名称/用途/大小/时长/SHA见design_module/M5/模块说明文档/五段视频证据索引-20261116.json。视频和bag不入Git，不把本机路径当共享链接。
