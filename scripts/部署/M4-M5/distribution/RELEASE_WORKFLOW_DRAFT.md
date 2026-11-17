# M4/M5部署资源Release（发布候选稿，尚无新Release）

计划发布到个人Fork YYSY-FISH7/ai4，tag m4-m5-runtime-20261117；ZIP只放Release附件，不进develop，不修改已合并PR22；源码/技术资料通过本次独立PR供审核，二进制发行仍暂停。源码侧仅保存脚本、本文、许可证、版本及校验清单，建议独立release分支/tag。

## 下载入口与完整性
以下是发布后填写的入口模板，不代表附件已经存在：
```
RELEASE_BASE="<创建完成后核实的Release附件下载前缀>"
curl -fL "$RELEASE_BASE/m4-m5-runtime-ubuntu20.04-py38.zip" -o m4-m5-runtime-ubuntu20.04-py38.zip
curl -fL "$RELEASE_BASE/m4-m5-runtime-ubuntu20.04-py38.zip.sha256" -o m4-m5-runtime-ubuntu20.04-py38.zip.sha256
sha256sum -c m4-m5-runtime-ubuntu20.04-py38.zip.sha256
# 仅在目标目录不存在时解压；不得覆盖已有资源目录。
test ! -e "$HOME/m4-resource-kit" || exit 1
unzip -n m4-m5-runtime-ubuntu20.04-py38.zip -d "$HOME"
cd "$HOME/m4-resource-kit"
sha256sum -c SHA256SUMS.txt
```
补齐许可/说明后的ZIP大小和SHA会改变，发布必须重新计算，不能继续用旧d3901b1e…摘要。原ONNX仍为37746458字节、SHA320ec090ff91a333116d120479f2ad2a9f97a1893e5826e99cf2ad7fd2ca1bd7。

## 平台及安装边界
Ubuntu20.04 x86_64、Python3.8、ROS Noetic及已编译uav_tracking消息。不是其他OS/架构通用包。基础torch等依赖需网络下载；本包仅ONNX补充wheel离线可用，不是全离线环境。
先核实是否存在可复用的基础库与ONNX库；使用M4_BASE_DEPS、M4_ORT_DEPS指定队友实际路径。不得复制本机历史路径。确认确实缺库且新解压目录内runtime既不存在也不是失效链接，才运行：
```
bash install-isolated.sh --install-new-runtime
```
只在资源包的新runtime.pending.*安装，成功才发布runtime；不覆盖已有runtime、系统Python、ROS或其他工程。原脚本独立目标已审查；全新队友VM安装尚未执行，不宣传为跨机安装已验收。

## 预检和实时启动
```
KIT="$HOME/m4-resource-kit"
cd <队友实际ai4工程根目录>
bash "$KIT/preflight.sh" "$PWD"
bash "$KIT/start.sh" "$PWD" "<当次M0实际生成的connection.bash>"
```
加载顺序：ROS Noetic→实际Catkin setup→隔离依赖→当次M0连接。预检只导入/加载ONNX，不启动节点。启动调用现有入口，显式可信模型、640/.50、ORT intra/inter=1；检查相机及重复节点，不启动ROS Master/Gazebo/PX4，不停止他人节点。
同master的检查终端可用rostopic info/echo/hz检查/camera/image_raw、/detections、/visual/tracks以及/detector/debug_image。空检测/空轨迹需与画面相符；异常/过期抑制不能伪装空目标。Ctrl+C只停止本次自有M4/M5。

## 报错
模型不存在或SHA不一致则停止重传；库路径缺失先核实，不直接装全局包；缺消息setup由ROS工程负责人处理，不自动apt/编译；master或相机缺失用当次connection；已有同名节点联系所有者，不自动杀进程。

## 发布完成判据
创建Release后必须上传完整新ZIP及外部.sha256；核实服务端附件大小/digest，独立重新下载完整附件，核对下载SHA和ZIP CRC、模型SHA、文件清单，不以空Release或仅README成功算完成。新Release链接、tag、上传/下载时间与结果留档。此候选稿未执行任何发布动作。

## 仓库工具与资源附件的关系

本PR只交付小型脚本/清单/许可。资源附件可独立解压，用仓库check-resources.py核验其model与wheelhouse；通过M4_MODEL指定模型，缺库时由仓库install-isolated.sh --install-new-runtime --wheelhouse /实际目录进行隔离安装。不要把源码PR已经提交误解为模型ZIP已经公开。最终ZIP如再次重组，应重新生成整体SHA，模型SHA不变。
