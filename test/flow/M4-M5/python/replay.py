import sys,json,math
from pathlib import Path
import rosbag
ROOT=Path(__file__).resolve().parents[4];sys.path.insert(0,str(ROOT/'code'))
from visual_tracker import setup
from datatypes import DetectedTarget
tracker=setup(frame_size=(320,240));rows=[];empty=0
with rosbag.Bag(sys.argv[1]) as b:
 for topic,m,t in b.read_messages(topics=['/detections']):
  ds=[DetectedTarget(class_id=x.class_id,confidence=x.confidence,bbox=tuple(x.bbox)) for x in m.targets]
  ts=tracker.track(ds,None)
  assert ds or not ts
  for x in ts:
   assert isinstance(x.id,int) and len(x.bbox)==4 and all(math.isfinite(z) for z in x.bbox)
   assert abs(x.area_ratio-x.bbox[2]*x.bbox[3]/76800)<1e-6
  rows.append({'targets':len(ds),'tracks':[x.id for x in ts]})
result={'source':sys.argv[1],'provenance':'historical real Gazebo detection replay; tracker recomputed, not fresh Gazebo','frame_size':[320,240],'detections':len(rows),'empty_detections':sum(not x['targets'] for x in rows),'empty_tracks':sum(not x['tracks'] for x in rows),'ids':sorted({i for x in rows for i in x['tracks']}),'passed':bool(rows),'identity_accuracy':'not established by this replay'}
Path(sys.argv[2]).write_text(json.dumps(result,indent=2));print(json.dumps(result))
