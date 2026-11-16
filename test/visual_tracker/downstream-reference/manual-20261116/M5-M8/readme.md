# M5→M8：正式节点缓存接收、读取与恢复

视频：06_M5-M8_视觉航迹与状态机联调.mp4，原名2026-11-16 17-41-47.mp4。103.9167秒、60fps、6235帧全部可读，SHA `ac4f21fa1eff523004fd1e4c447399a4185bbf5c2c2cde5db529260c032ef7c3`。原视频另行群聊交付，不放Git。

同视频05的真实源bag（偏移100/120/150秒各15秒），播放原相机和/detections；**当前原M5生成/visual/tracks，正式M8原文件以__main__运行**，不是仅实例化接收测试包装类。未改M8阈值0.8/0.02、N/M/K=3/3/5，不发布人工航迹/雷达。无雷达时状态进入SEARCH/RTH，未自然锁定，不作为失败或锁定通过。

|阶段|M5航迹/非空|M8回调非空/空|外部观察收到的判定非空/空|
|---|---:|---:|---:|
|存在|38/11|11/27|10/27|
|离场|41/0|0/41|1/40|
|重入|38/13|13/25|12/26|

原进程M8-internal-readonly.jsonl有117次step及117次visual回调；外部观察话题只收到233条，少1条，不据此声称节点漏判。stage1/stage3录包各37条检测，而监视器各38；三bag总115检测，不能写成完整保存117条。完整源bag、原回放命令及原进程日志仍保留，支持本轮限定接口结论，不能当严格无消息丢失验收。

离场首次step仍读取旧ID5，1794822154.7300863；空航迹回调更新在1794822154.7328303，差2.744毫秒，随后40拍空。该值是两个观测事件间隔，不是端到端延迟保证；检测节拍与航迹回调异步，不声称严格同帧。进入/重入仍有空航迹和ID重建。

## 内部证据如何得到

python/m5_m8_readonly_audit.py通过Python profile返回事件只读观察原on_visual_tracks更新后的缓存、原step的visual_tracks实际实参和状态结果，runpy执行未修改的正式M8原文件__main__。不是外部订阅推断缓存，也没有替换回调/算法。观察器发布/audit/m8_internal并写原始日志；此发布仅审计，不回送M8输入。profile有开销，不用作实时性能证明。source-identities.json与audit-method.json记录原源码SHA和边界。

M8只在/detections回调推进判断，/visual/tracks回调仅缓存。视频03是人工受控N/M/K，旧264次审计66非空/198空属于另一批历史类审计，均不混入这次正式节点计数。

## 已执行流程与复现（不自动测试）

Ubuntu20.04/ROS Noetic及已有编译消息、Qt窗口环境。脚本保留原运行版本，固定节点路径formal-20261116和原始源bag；跨阶段保留节点与状态、ROS墙钟，阶段间选择不同源偏移，不宣称连续仿真时间。需要原运行只读观察器在/tmp/m5_m8_readonly_audit.py；若该位置已存在必须比较字节，不可覆盖不同文件。

```bash
cd /home/demo/ai4-m4-m5-formal-20261116
source /opt/ros/noetic/setup.bash
source catkin_ws/devel/setup.bash
export DISPLAY=:0 XAUTHORITY=/home/demo/.Xauthority
AUDIT=test/visual_tracker/downstream-reference/manual-20261116/M5-M8/python/m5_m8_readonly_audit.py
# 仅在不存在时复制；存在则要求完全相同，否则停止并联系维护者。
if [ -e /tmp/m5_m8_readonly_audit.py ]; then
  cmp "$AUDIT" /tmp/m5_m8_readonly_audit.py || exit 1
else
  cp -n "$AUDIT" /tmp/m5_m8_readonly_audit.py
fi
/usr/bin/python3 -B test/visual_tracker/downstream-reference/manual-20261116/M5-M8/python/manual_m5_m8_stepwise.py
```

脚本创建隔离master、正式M5与带只读观察的正式M8，等待ready。用户准备OBS后点击开始，只阶段1；每阶段结束暂停，用户确认“继续”才进入下一阶段；最后提示停OBS，不自动通过。停止按钮/SESSION中的stop.request只清理自有进程。原始会话`/home/demo/m5-m8-manual-20261116-iv3atpid`已结束，不能重新触发它当新测试。

结论：M5→正式M8接收、空缓存更新和重入读取有原始证据。M8正式生产部署签认、自然VISUAL_LOCK、T4及完整飞行由M8/控制负责人完成，不能据本视频宣布通过。
