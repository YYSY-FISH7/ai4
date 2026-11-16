"""Real recorded M4 detections -> original running M5 -> original running M6.
Every stage requires a separate user trigger. No synthetic tracks or flight chain.
"""
import os,sys,time,json,socket,tempfile,subprocess,signal,threading,hashlib
from pathlib import Path
ROOT=Path('/home/demo/ai4-m4-m5-formal-20261116');BAG=Path('/home/demo/m4-ort1-exit-reentry.NeAllp/live.bag')
OUT=Path(tempfile.mkdtemp(prefix='m5-m6-auto-20261116-',dir='/home/demo'));print('SESSION='+str(OUT),flush=True)
with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
os.environ.update(ROS_MASTER_URI='http://127.0.0.1:'+str(port),ROS_IP='127.0.0.1',ROS_HOSTNAME='127.0.0.1',ROS_LOG_DIR=str(OUT/'ros'),DISPLAY=':0',PYTHONDONTWRITEBYTECODE='1')
children=[];data={};counts={'detections':0,'tracks':0,'commands':0,'images':0};ui={'phase':'ready','message':'准备完成：历史真实数据回放；等待用户“开始”','deadline':0,'completed':0};events=[];mutex=threading.Lock()
def start(cmd,name):
 with (OUT/(name+'.log')).open('w') as f:p=subprocess.Popen(cmd,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
 children.append(p);return p
def stop(p):
 if p.poll() is None:
  os.killpg(p.pid,signal.SIGINT)
  try:p.wait(timeout=12)
  except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGTERM)
def mark(phase,message,seconds=0):
 ui.update(phase=phase,message=message,deadline=time.time()+seconds);r=dict(wall=time.time(),**ui);events.append(r);t=OUT/'phase.tmp';t.write_text(json.dumps(r));t.replace(OUT/'phase.json');print(json.dumps(r),flush=True)
try:
 assert BAG.exists();start(['roscore','-p',str(port)],'master');time.sleep(3)
 import rospy,rosgraph,yaml
 from PyQt5 import QtWidgets,QtCore,QtGui
 from sensor_msgs.msg import Image
 from uav_tracking.msg import Detections,VisualTrackArray
 from mavros_msgs.msg import PositionTarget
 from cv_bridge import CvBridge
 rospy.init_node('m5_m6_manual_monitor',disable_signals=True);bridge=CvBridge()
 for k,v in yaml.safe_load((ROOT/'catkin_ws/src/uav_tracking/config/visual_tracker.yaml').read_text()).items():rospy.set_param('/visual_tracker/'+k,v)
 rospy.set_param('/visual_tracker/width',320);rospy.set_param('/visual_tracker/height',240)
 start(['/usr/bin/python3','-B',str(ROOT/'catkin_ws/src/uav_tracking/scripts/visual_tracker_node.py')],'original-M5')
 start(['/usr/bin/python3','-B',str(ROOT/'catkin_ws/src/uav_tracking/scripts/pid_controller_node.py'),'_image_width:=320','_image_height:=240'],'original-M6')
 def cb(m,key):
  with mutex:
   counts[key]+=1
   if key=='images':data[key]=bridge.imgmsg_to_cv2(m,'rgb8');return
   r=dict(kind=key,wall=time.time(),phase=ui['phase'])
   if key=='detections':r['targets']=[dict(confidence=t.confidence,bbox=list(t.bbox)) for t in m.targets]
   if key=='tracks':r['tracks']=[dict(id=t.id,bbox=list(t.bbox),area_ratio=t.area_ratio) for t in m.tracks]
   if key=='commands':r.update(vx=m.velocity.x,vy=m.velocity.y,vz=m.velocity.z,yaw_rate=m.yaw_rate,frame=m.coordinate_frame,mask=m.type_mask)
   data[key]=r
   if ui['phase'] not in ['ready','hold1','hold2','hold3']:
    with (OUT/'events.jsonl').open('a') as f:f.write(json.dumps(r)+'\n')
 subs=[rospy.Subscriber(t,c,cb,callback_args=k,queue_size=100,buff_size=2**22) for t,c,k in [('/camera/image_raw',Image,'images'),('/detections',Detections,'detections'),('/visual/tracks',VisualTrackArray,'tracks'),('/ctrl/visual',PositionTarget,'commands')]]
 (OUT/'session.json').write_text(json.dumps(dict(master=os.environ['ROS_MASTER_URI'],source_bag=str(BAG),sha256=hashlib.sha256(BAG.read_bytes()).hexdigest(),source='historical real Gazebo camera/detections; original M5 and M6 run now',PID_test_dimensions=[320,240],flight=False,synthetic_tracks=False,git_changes=False),indent=2))
 subprocess.run(['rosparam','dump',str(OUT/'parameters.yaml')],check=True)
 def wait(sec):
  end=time.monotonic()+sec
  while time.monotonic()<end:
   if (OUT/'stop.request').exists():raise RuntimeError('User stopped')
   time.sleep(.05)
 def sequence():
  try:
   for i,offset in [(1,100),(2,120),(3,150)]:
    if i==1:
     while not (OUT/'start.request').exists():wait(.1)
     mark('countdown','请启动OBS：10秒后自动演示全部三个阶段',10);wait(10)
    else:
     mark('transition','上一阶段完成，3秒后自动进入阶段%d'%i,3);wait(3)
    mark('stage%d'%i,{1:'阶段1：真实目标存在/移动 → 原M5航迹 → 原M6输出',2:'阶段2：历史真实离场空检测 → M5空航迹 → PID归零',3:'阶段3：历史真实重入 → M5重新建轨 → PID恢复'}[i],15)
    record=start(['rosbag','record','--lz4','-O',str(OUT/('stage%d.bag'%i)),'/camera/image_raw','/detections','/visual/tracks','/ctrl/visual'],'record%d'%i);wait(1)
    player=start(['rosbag','play','--start='+str(offset),'--duration=15',str(BAG),'--topics','/camera/image_raw','/camera/camera_info','/detections'],'player%d'%i)
    while player.poll() is None:wait(.1)
    if player.returncode:raise RuntimeError('Playback failed')
    wait(1);stop(record)
    ui['completed']=i
    mark('hold%d'%i,'阶段%d完成；%s'%(i,'即将自动进入下一阶段' if i<3 else '测试完成，可以停止OBS录制；等待你确认本项结果'))
   (OUT/'all-stages-finished.txt').write_text('Waiting for human verdict; not automatically passed')
  except Exception as e:mark('error','已暂停，请停止录制并检查：'+str(e))
 threading.Thread(target=sequence,daemon=True).start()
 app=QtWidgets.QApplication(sys.argv);win=QtWidgets.QWidget();win.resize(1050,720);win.move(30,40);layout=QtWidgets.QVBoxLayout(win)
 layout.addWidget(QtWidgets.QLabel('M5→M6 人工验收 | 历史真实Gazebo输入回放，原M5/M6现在运行 | 非人工航迹、非飞行闭环'))
 head=QtWidgets.QLabel();head.setWordWrap(True);head.setStyleSheet('font-size:23px;font-weight:bold');layout.addWidget(head)
 buttons=QtWidgets.QHBoxLayout();begin=QtWidgets.QPushButton('开始第1阶段（10秒倒计时，准备OBS）');advance=QtWidgets.QPushButton('确认上一阶段，继续');halt=QtWidgets.QPushButton('停止本项测试')
 def trigger_begin():
  if ui['phase']=='ready':(OUT/'start.request').touch();begin.setEnabled(False)
 def trigger_next():
  if ui['phase'] in ['hold1','hold2']:(OUT/('continue-2.request' if ui['phase']=='hold1' else 'continue-3.request')).touch();advance.setEnabled(False)
 begin.clicked.connect(trigger_begin);advance.clicked.connect(trigger_next);halt.clicked.connect(lambda:(OUT/'stop.request').touch())
 for b in [begin,halt]:buttons.addWidget(b)
 layout.addLayout(buttons);progress=QtWidgets.QProgressBar();progress.setRange(0,3);progress.setFormat('已完成阶段 %v / 3');layout.addWidget(progress)
 layout.addWidget(QtWidgets.QLabel('点击一次开始：10秒倒计时 → 目标存在/移动 → 自动离场归零 → 自动重入恢复 → 显示停止录制'))
 image=QtWidgets.QLabel('等待“开始”后才发布真实回放图像；当前不执行测试');image.setMinimumHeight(260);image.setAlignment(QtCore.Qt.AlignCenter);layout.addWidget(image)
 values=QtWidgets.QLabel();values.setStyleSheet('font-size:25px;color:#087522');layout.addWidget(values);text=QtWidgets.QPlainTextEdit();text.setReadOnly(True);layout.addWidget(text)
 layout.addWidget(QtWidgets.QLabel('临时PID 320×240；ROS侧FLU；不修改M6正式配置。一次开始自动演示三阶段；结束后由你确认验收结果。'))
 def refresh():
  if (OUT/'stop.request').exists():app.quit();return
  begin.setEnabled(ui['phase']=='ready');advance.setEnabled(ui['phase'] in ['hold1','hold2']);advance.setText('确认第1阶段，继续第2阶段' if ui['phase']=='hold1' else '确认第2阶段，继续第3阶段' if ui['phase']=='hold2' else '等待当前阶段结束后才能继续')
  progress.setValue(ui.get('completed',0))
  head.setStyleSheet('font-size:23px;font-weight:bold;color:'+('#087522' if ui['phase']=='hold3' else '#202020'))
  remaining=max(0,int(ui['deadline']-time.time()+.99));head.setText(ui['message']+((' %d秒'%remaining) if remaining else ''));win.setWindowTitle('M5→M6 一键人工验收 — '+ui['phase'])
  with mutex:
   if 'images' in data:
    a=data['images'];q=QtGui.QImage(a.data,a.shape[1],a.shape[0],a.strides[0],QtGui.QImage.Format_RGB888).copy();image.setPixmap(QtGui.QPixmap.fromImage(q).scaled(640,280,QtCore.Qt.KeepAspectRatio))
   cmd=data.get('commands',{});values.setText('yaw %.3f | vz %.3f | vx %.3f'%(cmd.get('yaw_rate',0),cmd.get('vz',0),cmd.get('vx',0)))
   text.setPlainText('接收计数 '+json.dumps(counts)+'\nM4原记录/detections: '+json.dumps(data.get('detections',{}))+'\n原M5实时/visual/tracks: '+json.dumps(data.get('tracks',{}))+'\n原M6实时/ctrl/visual: '+json.dumps(cmd))
   (OUT/'viewer-status.json').write_text(json.dumps(dict(phase=ui['phase'],counts=counts,M5=data.get('tracks'),M6=cmd)))
 timer=QtCore.QTimer();timer.timeout.connect(refresh);timer.start(200);(OUT/'armed.ready').write_text('No input data has been replayed; awaiting start.request');mark('ready',ui['message']);win.show();app.exec_()
finally:
 for p in reversed(children):stop(p)
 (OUT/'phases.json').write_text(json.dumps(events,indent=2))
