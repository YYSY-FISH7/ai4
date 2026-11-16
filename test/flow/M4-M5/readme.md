# M4→M5 正式接收方归档

M5由本组维护，是本链路接收方。本目录正式归档原2026-11-14真实实时Gazebo证据（02视频，非新测试），保留Git移动历史和原日志。图像image、日志log/live-20261114、可视化/目标阶段脚本python。本方验收到/visual/tracks发布与展示为止，不要求M6/M8算法处理结果。

一键离线核验：bash run.sh <真实bag> <输出json>，不启动master，无需停止其他节点。真实现场复现：沿用已有M0和M4，roslaunch uav_tracking visual_tracker.launch（先确认无同名节点）；读取实时/visual/tracks即可。python/manual_track_view.py <证据目录>只读展示；python/manual_track_sequence.py <同证据目录>预置10秒倒计时并等待start.request，内部录bag，暂停/移走/恢复target_uav，异常finally恢复，须在独占且已source本次connection的测试场景操作。结束后Ctrl+C只停对应程序/节点，不killall。

离线回放不能证明新Gazebo运行；身份正确率需要真值，本次只验证字段、面积、空输入、重入能力及记录ID变化，不宣称稳定身份。
