# 模型来源、转换与许可边界

原模型：https://huggingface.co/sapoepsilon/yolov11s-drone-detector 。已核验内容对应revision `58897d6d6fadda9dfec979fd5dd7ad9040e73365`；历史下载命令是否显式固定revision未记录。

原微调best.pt：19160211字节，SHA `337390e1018eaf815474c02e172a224425095466d4a5cd2dbd11301b0aa01b78`。原ONNX：37746458字节，SHA `320ec090ff91a333116d120479f2ad2a9f97a1893e5826e99cf2ad7fd2ca1bd7`。类别0=drone。原模型经用户确认作为个人Fork Release附件提供，七wheel仍可从内部ZIP交接；本目录不提交二进制。模型固定下载：https://github.com/YYSY-FISH7/ai4/releases/download/m4-yolo11s-onnx-20261117/yolo11s-drone.onnx 。

基础权重：模型作者称为Ultralytics yolo11s.pt；其准确下载版本、SHA和完整训练过程待作者确认，不能用COCO yolov8n.pt冒充训练基础。

历史成功转换记录：Python3.8.10、Ultralytics8.4.173、PyTorch2.4.1+cpu、ONNX1.16.2；format=onnx、imgsz640、opset17、dynamic=True、simplify=False、nms=False、device=cpu；导出torch线程2，正式运行ORT线程1/1。历史四图PT/ONNX核对两张正样本约0.729/0.659、两张空目标一致，不代表全面精度验证。

[可移植导出适配器](export/export_verified_drone.py)沿用固定PT SHA与历史限制加载白名单，以安装包内YAML容器替代旧COCO容器初始化；本轮仅语法/help检查，未重新导出。只在经确认、隔离非特权导出环境使用，不能把新导出结果视为旧验收模型。正常部署直接使用原ONNX，无需PT或重新导出。源校验失败、未知全局类、已有输出目录均拒绝，不是通用安全加载器。

HF[原模型卡](https://huggingface.co/sapoepsilon/yolov11s-drone-detector/blob/58897d6d6fadda9dfec979fd5dd7ad9040e73365/README.md)声明Apache-2.0；ONNX自身保留AGPL-3.0元数据；[Ultralytics官方政策](https://www.ultralytics.com/license)及[固定版本许可证](https://github.com/ultralytics/ultralytics/blob/v8.4.173/LICENSE)均须保留。没有据此裁定冲突已解决，不删除或修改模型元数据，不给团队源码指定许可证。

完整原始模型卡、ONNX导出元数据、83份第三方版权/许可文本和来源清单已随内部ZIP的m4-resource-kit/model及distribution/licenses/交付，此处引用，不重复复制。七wheel的原始许可证也在各wheel内，FlatBuffers缺失文本由内部包官方版本原LICENSE补充；pip内嵌组件分别保留。完整分发适用仍需权利人/组长确认，不因内部交接自动豁免第三方义务。
