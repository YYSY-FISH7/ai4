# ONNX 导出链路与可移植脚本

正常部署直接使用已验收 ONNX，不需要下载或执行第三方 .pt。本目录用于交付转换方法，不是要求队友重新导出。

`HISTORICAL_EXPORT_EVIDENCE.json`记录当时成功脚本、限制加载辅助脚本、原始日志的SHA及实测版本/参数。原始文件完整保留在维护归档中；不将其临时绝对路径当作部署要求。原成功脚本采用固定SHA、pickle操作码和全局类白名单的自定义受限加载器，torch.load的weights_only=False与受限Unpickler组合；不能描述为weights_only=True，也不能描述为不受限的普通torch.load。

`export_verified_drone.py`是本轮从该流程提取的可移植适配脚本：保留固定PT SHA和原白名单、导出参数；用安装包内yolo11s.yaml创建容器，再替换为核验的微调网络，避免依赖历史yolov8n.pt容器文件。容器不是训练基础权重。脚本没有重新训练，也没有执行导出，本轮仅语法/静态审查；其新导出结果需要另行数值与元数据比对，不能沿用原视频宣布通过。旧导出的时间元数据也意味着不能保证重新导出字节SHA相同。

仅经来源和授权确认后，在独立、无凭据、非特权导出环境中使用：
```bash
# 加载本资源包隔离依赖；不向系统Python安装。
export PYTHONPATH="$KIT/runtime/lib/m4_onnx:$KIT/runtime/lib/m4${PYTHONPATH:+:$PYTHONPATH}"
export YOLO_AUTOINSTALL=false PYTHONDONTWRITEBYTECODE=1
/usr/bin/python3 "$KIT/export/export_verified_drone.py"   --weights "/实际路径/best.pt" --output-dir "/全新路径/onnx-export"   --acknowledge-third-party-pickle
```
脚本拒绝未知PT SHA和已有输出目录。受限加载不是通用安全认证；未获确认不要运行。当前正式ONNX不受此操作影响，也不修改其AGPL元数据。PT下载固定revision与SHA见model/SOURCE_CHAIN.md。requirements-export.txt仅锁定有历史证据的核心版本，不伪称完整导出环境锁。部署运行依赖另见DEPENDENCIES.md。
