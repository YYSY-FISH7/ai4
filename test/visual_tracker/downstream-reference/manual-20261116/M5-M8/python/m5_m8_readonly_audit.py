"""Read-only frame observer. Executes unchanged official M8 as __main__.
No replacement class, callback wrapper, parameter change or injected input.
"""
import sys,threading,json,time,runpy,hashlib
from pathlib import Path
source=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]);publisher=None;busy=threading.local()
def observe(frame,event,arg):
 global publisher
 if event!='return' or getattr(busy,'active',False):return
 if frame.f_code.co_filename!=str(source):return
 name=frame.f_code.co_name
 if name not in ('on_visual_tracks','step'):return
 node=frame.f_locals.get('self')
 if node is None and name!='step':return
 busy.active=True
 try:
  tracks=frame.f_locals['visual_tracks'] if name=='step' else node._visual_tracks
  r={'wall':time.time(),'event':name+'_return','cache_count':len(tracks),'cache_ids':[int(t.id) for t in tracks],'state':arg[0] if name=='step' else node.state,'counters':dict(frame.f_locals['counters'] if name=='step' else node.counters),'detection_count':len(frame.f_locals['detections'] if name=='step' else node._detections)}
  with (out/'M8-internal-readonly.jsonl').open('a') as f:f.write(json.dumps(r)+'\n')
  import rospy
  from std_msgs.msg import String
  if publisher is None:publisher=rospy.Publisher('/audit/m8_internal',String,queue_size=100,latch=True)
  publisher.publish(String(data=json.dumps(r)))
 finally:busy.active=False
(out/'audit-method.json').write_text(json.dumps({'method':'Python profile return-event observation; unchanged formal main executed by runpy','source':str(source),'sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'limits':'step_return records actual visual_tracks function argument used in decision; on_visual_tracks_return records cache after callback; concurrent callbacks not causally paired by observer topic arrival; no natural VISUAL_LOCK or flight claim'},indent=2))
threading.setprofile(observe);sys.setprofile(observe)
sys.argv=[str(source)]
runpy.run_path(str(source),run_name='__main__')
