# Ubuntu定位与前后对应

维护入口：/home/demo/M4-M5维护资料。M4_视觉检测/、M5_视觉跟踪/、跨模块联调/、历史版本与归档索引/均已实际建立。旧→新对应是“旧目录不动→分类兼容链接/清单”，不是移动源码。34项真实工作区branch/HEAD/status见test/flow/M4-M5/log/vm-workspaces-20261116.json。

独立维护代码：/home/demo/ai4-m4-m5-delivery-20261116，以最新f540ae4为基线，待本PR最终SHA记录后与其对照。M4 code/detector.py；M5 code/visual_tracker.py。启动M4用M0-M4组合入口或独立ORT1包装；启动M5用roslaunch uav_tracking visual_tracker.launch，联调用test/flow/M4-M5/run.sh。须source原ROS和Catkin及当前M0连接，不另起master。

catkin_ws/devel是到旧integration已编译结果的兼容软链，独立Git对象也复用旧repo，因此不能删除旧integration。原ai4桌面、acceptance-c421、旧正式版本、失败恢复实验都不改名、不清理；latest/priority/recovery不因名字被当成当前算法。模型仍在原m4-yolo11s-validation目录。

本轮85单测与原M5 E2E通过，关键代码软链与devel可用；没有启动新Gazebo或完整飞控，因此不是全新环境部署验收。

交付归档后正式只读入口为/home/demo/ai4-m4-m5-formal-20261116（本PR最终提交），上述delivery-20261116保留为本轮回归工作区。维护索引中的当前入口将指向formal；均依赖旧integration的已编译消息与隔离模型环境。
