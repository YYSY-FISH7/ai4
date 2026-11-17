"""Unpublished portable adapter of the historical verified export recipe.
Not executed/re-exported in this preparation task. See README.md.
"""
import argparse,hashlib,importlib,json,pickletools,sys,zipfile,os
from pathlib import Path
PT_SHA='337390e1018eaf815474c02e172a224425095466d4a5cd2dbd11301b0aa01b78'
allowed={
 'torch.nn.modules.activation':'SiLU','torch.nn.modules.batchnorm':'BatchNorm2d','torch.nn.modules.container':'ModuleList Sequential','torch.nn.modules.conv':'Conv2d','torch.nn.modules.linear':'Identity','torch.nn.modules.loss':'BCEWithLogitsLoss','torch.nn.modules.pooling':'MaxPool2d','torch.nn.modules.upsampling':'Upsample',
 'ultralytics.nn.modules.block':'Attention Bottleneck C2PSA C3k C3k2 DFL PSABlock SPPF C2f','ultralytics.nn.modules.conv':'Concat Conv DWConv','ultralytics.nn.modules.head':'Detect','ultralytics.nn.tasks':'DetectionModel','ultralytics.utils':'IterableSimpleNamespace','ultralytics.utils.loss':'BboxLoss DFLoss v8DetectionLoss','ultralytics.utils.tal':'TaskAlignedAssigner','numpy':'dtype','numpy.core.multiarray':'scalar'}
extra={m+' '+n for m,s in allowed.items() for n in s.split()}
standard=set('__builtin__ set|_codecs encode|collections OrderedDict|torch FloatStorage|torch HalfStorage|torch LongStorage|torch Size|torch device|torch._utils _rebuild_parameter|torch._utils _rebuild_tensor_v2'.split('|'))
def checked(f):
 f=Path(f)
 assert hashlib.sha256(f.read_bytes()).hexdigest()==PT_SHA
 with zipfile.ZipFile(f) as z:
  names=z.namelist()
  assert all(not n.startswith('/') and '..' not in n.split('/') and '/code/' not in n and not n.endswith('constants.pkl') for n in names)
  data=[n for n in names if n.endswith('/data.pkl')];assert len(data)==1
  ops=list(pickletools.genops(z.read(data[0])))
  assert not {o.name for o,_,_ in ops}&{'EXT1','EXT2','EXT4','STACK_GLOBAL','INST','OBJ'}
  gs={v.replace('numpy._core.','numpy.core.') for o,v,_ in ops if o.name=='GLOBAL'}
  assert gs<=standard|extra,gs-(standard|extra)
 import pickle,types,builtins
 class Restricted(pickle.Unpickler):
  def find_class(self,module,name):
   module={'__builtin__':'builtins','numpy._core.multiarray':'numpy.core.multiarray'}.get(module,module)
   pair=module+' '+name
   if pair=='builtins set': return builtins.set
   if pair not in gs or pair not in standard|extra: raise pickle.UnpicklingError(pair)
   return getattr(importlib.import_module(module),name)
 safe_pickle=types.SimpleNamespace(__name__='pickle',Unpickler=Restricted,load=pickle.load)
 ck=torch.load(f,map_location='cpu',pickle_module=safe_pickle,weights_only=False)
 m=(ck.get('ema') or ck['model']).float().eval()
 # Portable adapter: YAML creates a container; it is NOT a base checkpoint.
 y=YOLO('yolo11s.yaml',task='detect')
 y.model=m
 return y,ck.get('train_args',{}).get('imgsz')

def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--weights',required=True,type=Path)
 p.add_argument('--output-dir',required=True,type=Path)
 p.add_argument('--acknowledge-third-party-pickle',action='store_true')
 a=p.parse_args()
 if not __debug__:p.error('Optimized Python disables safety assertions; do not use -O')
 if not a.acknowledge_third_party_pickle:p.error('Requires prior source/license approval and an isolated export environment')
 if not a.weights.is_file() or hashlib.sha256(a.weights.read_bytes()).hexdigest()!=PT_SHA:p.error('Unexpected source checkpoint SHA-256')
 if a.output_dir.exists() or a.output_dir.is_symlink():p.error('Output must be a NEW directory; never overwrite the validated ONNX')
 if sys.version_info[:2]!=(3,8):p.error('Historical environment used Python 3.8')
 os.environ['YOLO_AUTOINSTALL']='false'
 global torch,YOLO
 import torch,onnx,ultralytics
 from ultralytics import YOLO
 for name,got,want in [('torch',torch.__version__,'2.4.1+cpu'),('onnx',onnx.__version__,'1.16.2'),('ultralytics',ultralytics.__version__,'8.4.173')]:
  if got!=want:p.error('%s expected %s, got %s'%(name,want,got))
 a.output_dir.mkdir(parents=True,exist_ok=False)
 torch.set_num_threads(2) # Historical export setting; runtime detection remains ORT 1/1.
 y,_=checked(a.weights)
 y.model.task='detect'
 y.model.pt_path=str(a.output_dir.resolve()/'yolo11s-drone.pt')
 f=Path(y.export(format='onnx',imgsz=640,opset=17,simplify=False,dynamic=True,device='cpu',nms=False))
 if f.resolve()!=(a.output_dir/'yolo11s-drone.onnx').resolve():raise RuntimeError('Unexpected export destination')
 graph=onnx.load(str(f),load_external_data=False)
 onnx.checker.check_model(graph)
 if any(t.data_location==onnx.TensorProto.EXTERNAL for t in graph.graph.initializer):raise RuntimeError('Unexpected external tensors')
 if any(n.domain not in ('','ai.onnx') for n in graph.graph.node):raise RuntimeError('Unexpected ONNX domain')
 metadata={m.key:m.value for m in graph.metadata_props}
 if 'AGPL' not in metadata.get('license',''):raise RuntimeError('Expected original upstream license metadata; do not strip or rewrite it')
 record={'source_sha256':PT_SHA,'onnx_sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'metadata':metadata,'status':'new_export_requires_comparison_not_original_acceptance'}
 (a.output_dir/'export-result.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps(record,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
