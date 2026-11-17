# 已验收模型来源与转换记录

## 可核实来源

- 上游仓库：https://huggingface.co/sapoepsilon/yolov11s-drone-detector
- 固定revision：58897d6d6fadda9dfec979fd5dd7ad9040e73365。
- 原卡：https://huggingface.co/sapoepsilon/yolov11s-drone-detector/blob/58897d6d6fadda9dfec979fd5dd7ad9040e73365/README.md 。本包保留其原文和仓库元数据。
- 权重：https://huggingface.co/sapoepsilon/yolov11s-drone-detector/resolve/58897d6d6fadda9dfec979fd5dd7ad9040e73365/best.pt 。上游LFS记录与历史加载器固定SHA一致：19160211字节，337390e1018eaf815474c02e172a224425095466d4a5cd2dbd11301b0aa01b78。Windows历史v11s.pt原件本轮重新计算大小与SHA，完全一致；正常部署不执行/不需要此PT，当前包不捆绑PT。固定revision用于定位同内容，历史下载时是否显式指定这一revision没有原始命令记录，不能据此编造当时的下载方式。
- 验收转换产物：yolo11s-drone.onnx，37746458字节，320ec090ff91a333116d120479f2ad2a9f97a1893e5826e99cf2ad7fd2ca1bd7。
- 类别：0=drone；ONNX原始metadata完整保留在模型内及ONNX_EXPORT_METADATA.json中。

## 训练基础与未知项

模型卡称以Ultralytics yolo11s.pt为基础微调；这是作者声明，不是我们独立复现的训练事实。官方模型说明：https://docs.ultralytics.com/models/yolo11/ 。原训练基础权重具体下载URL/revision/SHA、实际训练环境、完整训练脚本及训练数据权利尚待作者确认，不能用普通COCO yolov8n.pt冒充其训练基础。

## 实际转换证据

历史成功导出：Python3.8.10、Ultralytics8.4.173、PyTorch2.4.1+cpu、ONNX1.16.2；CPU、imgsz640、opset17、dynamic=True、simplify=False、nms=False。导出过程torch线程2与正式检测ORT线程1/1是不同阶段，不冲突。输入示例1×3×640×640，输出1×5×8400；dynamic输出实际符号维度以原模型图为准，不能解释为所有输入固定。

历史日志记录四张旧图的PT/ONNX对照：两张正样本置信度分别约0.729/0.659且两端一致，两张无目标均为空；最终SHA与当前模型一致。详细脚本/日志哈希、参数及本轮适配器差异见../export/HISTORICAL_EXPORT_EVIDENCE.json。此四图核对不等于完整精度验证。

## 许可不作改标

原HF卡Apache-2.0声明、ONNX中的AGPL-3.0元数据、Ultralytics官方政策分别保留，冲突未自行裁定。详LICENSE_STATUS.md及../THIRD_PARTY_NOTICES.md。官方许可：https://www.ultralytics.com/license 。尚待模型作者/相关权利人确认微调权重及ONNX分发条件；团队源码未给定许可证，不得给整个交付包指定Apache或AGPL。
