# Clarification of redistribution license for fine-tuned YOLO11s weights and ONNX exports

Hello sapoepsilon,

Thank you for publishing yolov11s-drone-detector. We are preparing a reproducible university ROS Noetic perception demo and would like to distribute an ONNX export in a public GitHub Release. We have not published this new resource bundle while the license is being clarified.

The model card at revision 58897d6d6fadda9dfec979fd5dd7ad9040e73365 states Apache-2.0. The original best.pt SHA-256 is 337390e1018eaf815474c02e172a224425095466d4a5cd2dbd11301b0aa01b78. Our Ultralytics 8.4.173 ONNX export retains an AGPL-3.0 metadata notice (ONNX SHA-256: 320ec090ff91a333116d120479f2ad2a9f97a1893e5826e99cf2ad7fd2ca1bd7). We understand that exporter metadata alone does not determine the applicable legal license. Ultralytics also publishes licensing guidance for trained/fine-tuned models.

Could you please clarify:

1. Is the Apache-2.0 statement intended to cover the fine-tuned model weights themselves, rather than only repository code or documentation?
2. Does your permission cover redistribution of an ONNX conversion without further training or changes to the learned weights?
3. What upstream/base-model permissions support that distribution, and are there additional Ultralytics requirements we should clarify directly with them? We are not asking you to waive third-party rights.
4. What license texts, copyright notices, attribution, source materials, or other conditions must accompany the original weights and ONNX derivative? Are there dataset-related redistribution restrictions relevant to the exported weights?
5. Could you provide the intended license text or add a clarification to the model repository so recipients can verify it?

We will preserve both the original model-card statement and export metadata pending clarification, and will not label the entire deployment bundle Apache-2.0. A public discussion reply would help us document the permission accurately.

Thank you.
