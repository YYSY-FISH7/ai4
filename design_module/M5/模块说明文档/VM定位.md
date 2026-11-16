# Ubuntu定位与前后对应

维护入口：/home/demo/M4-M5维护资料。M4_视觉检测/、M5_视觉跟踪/、跨模块联调/、历史版本与归档索引/均已实际建立。旧→新对应是“旧目录不动→分类兼容链接/清单”，不是移动源码。34项真实工作区branch/HEAD/status见test/flow/M4-M5/log/vm-workspaces-20261116.json。

独立维护代码：/home/demo/ai4-m4-m5-delivery-20261116，以最新f540ae4为基线，待本PR最终SHA记录后与其对照。M4 code/detector.py；M5 code/visual_tracker.py。启动M4用M0-M4组合入口或独立ORT1包装；启动M5用roslaunch uav_tracking visual_tracker.launch，联调用test/flow/M4-M5/run.sh。须source原ROS和Catkin及当前M0连接，不另起master。

catkin_ws/devel是到旧integration已编译结果的兼容软链，独立Git对象也复用旧repo，因此不能删除旧integration。原ai4桌面、acceptance-c421、旧正式版本、失败恢复实验都不改名、不清理；latest/priority/recovery不因名字被当成当前算法。模型仍在原m4-yolo11s-validation目录。

本轮85单测与原M5 E2E通过，关键代码软链与devel可用；没有启动新Gazebo或完整飞控，因此不是全新环境部署验收。

交付归档后正式只读入口为/home/demo/ai4-m4-m5-formal-20261116（本PR最终提交），上述delivery-20261116保留为本轮回归工作区。维护索引中的当前入口将指向formal；均依赖旧integration的已编译消息与隔离模型环境。

## 2026-11-16最终只读核查补充（最终归档）

核验时推荐源码入口formal-20261116，HEAD=98eb7169ef4a6c81ec98587628a1d44de165df84；最终归档后同步到本PR当前HEAD；其未跟踪catkin_ws/devel是既有兼容链接，不是新算法修改。delivery-20261116仍在f540ae4且有未跟踪历史测试资料，没有完整M4-M5/run.sh，不能当正式副本。acceptance-c421无devel，需显式复用integration构建。桌面旧ai4在83e0f46且存在大量历史未提交改动，本轮不清理、不覆盖。

正式副本本地不含YOLO/ORT隔离依赖，M4启动必须使用M4文档补充的PYTHONPATH和--ort-deps；M5不需要YOLO。M5-M6、M5-M8新增人工证据分别在/home/demo/m5-m6-auto-20261116-25uf5ylg和/home/demo/m5-m8-manual-20261116-iv3atpid，属于历史输入回放，非新Gazebo。当前所有11个维护兼容链接可解析；旧/tmp真实数据参考仍有易失风险，Windows原始归档保留，不能以临时目录作为唯一交接位置。

本轮正式交付只调整证据范围：团队基线为PR20合并后的431c049，VM已有运行源码保留PR20最终ded098a，不擅自切换或启动仿真；核心代码与新交付一致。新文档以本次PR为准，旧路径/依赖继续保留。
