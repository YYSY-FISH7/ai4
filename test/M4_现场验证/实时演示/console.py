#!/usr/bin/env python3
"""An isolated, observable M4 demo; no installation and no global process cleanup."""
import argparse
import collections
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import threading
import time
import xmlrpc.client
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
RUNTIME = Path('/tmp') / ('m4-console-' + str(os.getuid()))
MANIFEST = RUNTIME / 'session.json'

def process_start(pid):
    try:
        return Path('/proc/%d/stat' % pid).read_text().split(') ', 1)[1].split()[19]
    except (OSError, IndexError):
        return None

def session():
    try:
        data = json.loads(MANIFEST.read_text())
        return data if process_start(data['pid']) == data['start'] else None
    except (OSError, ValueError, KeyError):
        return None

class TimeoutTransport(xmlrpc.client.Transport):
    def make_connection(self, host):
        connection = super().make_connection(host)
        connection.timeout = 3
        return connection

def master_proxy(uri):
    return xmlrpc.client.ServerProxy(uri, transport=TimeoutTransport())

def ready(uri):
    try:
        return master_proxy(uri).getPid('/m4_console_probe')[0] == 1
    except (OSError, xmlrpc.client.Error):
        return False

def free_port(port):
    with socket.socket() as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(('0.0.0.0', port))

def environment(master):
    setup = ROOT / 'catkin_ws/devel/setup.bash'
    if not setup.is_file():
        raise RuntimeError('缺少 catkin_ws/devel/setup.bash，请先编译工程')
    raw = subprocess.check_output(['bash', '-c',
        'source /opt/ros/noetic/setup.bash && source "$1" && env -0', 'bash', str(setup)])
    env = dict(x.decode().split('=', 1) for x in raw.split(b'\0') if b'=' in x)
    env.update(ROS_MASTER_URI=master, PYTHONUNBUFFERED='1', PYTHONDONTWRITEBYTECODE='1')
    env.pop('ROS_NAMESPACE', None)
    return env

def main():
    parser = argparse.ArgumentParser(description='M4 视觉感知台')
    parser.add_argument('command', nargs='?', default='start', choices=['start','stop','status','verify','_run'])
    parser.add_argument('--mode', choices=['demo','sim'], default='demo')
    parser.add_argument('--video', default=str(HERE / 'assets/bus_moving.mp4'))
    parser.add_argument('--model', default=str(HERE / 'assets/yolov8n.pt'))
    parser.add_argument('--topic', default='/uav/front_camera/image_raw')
    parser.add_argument('--master')
    parser.add_argument('--port', type=int, default=8092)
    parser.add_argument('--no-browser', action='store_true')
    args = parser.parse_args()
    if not 1 <= args.port <= 65535: parser.error('port 必须在 1..65535')
    RUNTIME.mkdir(mode=0o700, exist_ok=True)
    current = session()
    if args.command == 'verify':
        if not current: raise RuntimeError('控制台未运行，请先启动')
        import urllib.request
        def read():
            return json.load(urllib.request.urlopen(current['url']+'status',timeout=5))
        first=read();time.sleep(2);second=read()
        failures=[]
        for name in ['camera','detector','tracker']:
            if second['counts'].get(name,0)<=first['counts'].get(name,0):
                failures.append(name+' 消息没有持续更新')
        if second['frames']<=first['frames']: failures.append('检测图像没有更新')
        if any(code is not None for code in second['processes'].values()): failures.append('有进程异常退出')
        groups=master_proxy(current['master']).getSystemState('/m4_console_verify')
        if groups[0]!=1: failures.append('无法读取实际 ROS 图谱')
        else:
            pubs=dict(groups[2][0])
            for topic in ['/detections','/visual/tracks','/detector/debug_image']:
                if not pubs.get(topic): failures.append(topic+' 没有实际发布者')
        if failures: raise RuntimeError('；'.join(failures))
        print('自检通过：实际 ROS 发布者存在，图像、检测、跟踪消息持续更新。')
        print('当前模式：'+second['source']+'；这不代表无人机仿真验收通过。')
        return 0
    if args.command == 'status':
        print(json.dumps(current,ensure_ascii=False,indent=2) if current else '控制台未运行')
        return 0
    if args.command == 'stop':
        if current:
            os.kill(current['pid'],signal.SIGTERM)
            for _ in range(150):
                if not session():
                    print('已停止本次启动的进程；其他环境保留。'); return 0
                time.sleep(.1)
            raise RuntimeError('停止超时，请检查 '+str(RUNTIME/'session.log'))
        print('控制台未运行，无需停止。'); return 0
    if args.command == 'start':
        if current:
            if current['mode'] != args.mode:
                raise RuntimeError('当前模式为 '+current['mode']+'；请先 stop 再切换模式')
            url=current['url']
        else:
            free_port(args.port)
            cmd=[sys.executable,str(HERE/'console.py'),'_run','--mode',args.mode,
                 '--video',args.video,'--model',args.model,'--topic',args.topic,'--port',str(args.port)]
            if args.master: cmd+=['--master',args.master]
            with open(RUNTIME/'session.log','w') as log:
                launch_master=args.master or ('http://127.0.0.1:11321' if args.mode=='demo' else os.environ.get('ROS_MASTER_URI','http://127.0.0.1:11311'))
                proc=subprocess.Popen(cmd,env=environment(launch_master),stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
            print('正在启动，模型首次预热可能需要约一分钟…',flush=True)
            for _ in range(150):
                current=session()
                if current: break
                if proc.poll() is not None:
                    raise RuntimeError((RUNTIME/'session.log').read_text()[-4000:])
                time.sleep(.2)
            else:
                os.kill(proc.pid,signal.SIGTERM)
                raise RuntimeError('启动超时，请检查 '+str(RUNTIME/'session.log'))
            url=current['url']
        print('浏览器打开：'+url)
        if not args.no_browser:
            subprocess.Popen(['xdg-open',url],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        return 0
    return run(args)

def run(args):
    import fcntl
    lock=open(RUNTIME/'session.lock','w')
    try: fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BlockingIOError: raise RuntimeError('控制台已在运行或启动中')
    master=args.master or ('http://127.0.0.1:11321' if args.mode=='demo' else
                            os.environ.get('ROS_MASTER_URI','http://127.0.0.1:11311'))
    env=environment(master)
    model=Path(args.model).resolve()
    if not model.is_file(): raise RuntimeError('找不到模型，请用 --model 指定：'+str(model))
    if args.mode=='demo' and not Path(args.video).is_file():
        raise RuntimeError('找不到视频，请用 --video 指定：'+args.video)
    children=[]; logs=[]; shutdown=threading.Event(); srv=None
    signal.signal(signal.SIGTERM,lambda *_:shutdown.set())
    signal.signal(signal.SIGINT,lambda *_:shutdown.set())
    def spawn(name,cmd):
        log=open(RUNTIME/(name+'.log'),'w');logs.append(log)
        proc=subprocess.Popen(cmd,env=env,cwd=str(ROOT),stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        children.append((name,proc))
    try:
        if args.mode=='demo':
            parsed=urlparse(master)
            if parsed.hostname not in ('127.0.0.1','localhost'):
                raise RuntimeError('本地演示只允许独立的本机 ROS master')
            port=parsed.port or 11321; free_port(port)
            spawn('master',['roscore','-p',str(port)])
            for _ in range(100):
                if ready(master): break
                if shutdown.wait(.1): return 0
            else: raise RuntimeError('独立 ROS master 启动失败')
        elif not ready(master): raise RuntimeError('仿真 ROS master 未启动：'+master)
        os.environ.update(env)
        for part in env.get('PYTHONPATH','').split(os.pathsep):
            if part and part not in sys.path: sys.path.append(part)
        import rospy
        import rosgraph
        import cv2
        from cv_bridge import CvBridge
        from sensor_msgs.msg import Image
        from std_msgs.msg import String
        from uav_tracking.msg import Detections,VisualTrackArray
        rospy.init_node('m4_console',anonymous=True,disable_signals=True)
        if args.mode=='sim':
            groups=rosgraph.Master(rospy.get_name()).getSystemState()
            active={node for group in groups for _,names in group for node in names}
            if '/detector' in active or '/visual_tracker' in active:
                raise RuntimeError('已有视觉节点，拒绝替换；请先由原启动者停止它们')
            try: rospy.wait_for_message(args.topic,Image,timeout=10)
            except rospy.ROSException:
                raise RuntimeError('未收到真实仿真图像：'+args.topic+'；没有使用替代图片')
        topic='/camera/image_raw' if args.mode=='demo' else args.topic
        data=dict(mode=args.mode,source='本地视频演示' if args.mode=='demo' else '队友仿真输入',
                  topic=topic,model=model.name,master=master,state='尚未收到',ids=[],areas=[],
                  targets=0,confidence=0,shape=None,frames=0,counts={})
        mutex=threading.Lock();latest={'jpeg':None};last={}
        samples={key:collections.deque(maxlen=60) for key in ['camera','detector','tracker']}
        bridge=CvBridge()
        def mark(key):
            now=time.monotonic();samples[key].append(now);last[key]=now
            data['counts'][key]=data['counts'].get(key,0)+1
        def camera(msg):
            with mutex: mark('camera')
        def debug(msg):
            try:
                image=bridge.imgmsg_to_cv2(msg,'bgr8')
                ok,jpeg=cv2.imencode('.jpg',image,[cv2.IMWRITE_JPEG_QUALITY,85])
                if ok:
                    with mutex:
                        latest['jpeg']=jpeg.tobytes();data['shape']=[msg.width,msg.height]
                        data['frames']+=1;last['image']=time.monotonic()
            except Exception as exc: rospy.logwarn_throttle(5,'控制台图像转换失败：%s',exc)
        def detection(msg):
            with mutex:
                mark('detector');data['targets']=len(msg.targets)
                data['confidence']=max([t.confidence for t in msg.targets] or [0])
        def tracks(msg):
            with mutex:
                mark('tracker');data['ids']=[t.id for t in msg.tracks]
                data['areas']=[round(t.area_ratio,4) for t in msg.tracks]
        def state(msg):
            with mutex: data['state']=msg.data;last['state']=time.monotonic()
        rospy.Subscriber(topic,Image,camera,queue_size=1,buff_size=2**24)
        rospy.Subscriber('/detector/debug_image',Image,debug,queue_size=1,buff_size=2**24)
        rospy.Subscriber('/detections',Detections,detection,queue_size=10)
        rospy.Subscriber('/visual/tracks',VisualTrackArray,tracks,queue_size=10)
        rospy.Subscriber('/state',String,state,queue_size=10)
        def status():
            with mutex:
                out=dict(data);now=time.monotonic()
                out['ages']={k:round(now-v,1) for k,v in last.items()}
                out['rates']={k:round((len(v)-1)/(v[-1]-v[0]),1) if len(v)>1 and now-v[-1]<3 else 0
                              for k,v in samples.items()}
            out['processes']={name:proc.poll() for name,proc in children};out['logs']={}
            for name,_ in children:
                try:
                    with open(RUNTIME/(name+'.log'),'rb') as file:
                        file.seek(0,2);file.seek(max(0,file.tell()-3000))
                        out['logs'][name]=file.read().decode('utf-8','replace')
                except OSError: pass
            return out
        page=(HERE/'console.html').read_bytes()
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*_): pass
            def do_GET(self):
                path=urlparse(self.path).path;code=200
                if path=='/status': body=json.dumps(status(),ensure_ascii=False).encode();kind='application/json; charset=utf-8'
                elif path=='/frame.jpg':
                    with mutex: body=latest['jpeg']
                    kind='image/jpeg'
                    if body is None: body=b'Waiting for inference';kind='text/plain';code=503
                elif path=='/': body=page;kind='text/html; charset=utf-8'
                else: body=b'Not found';kind='text/plain';code=404
                self.send_response(code);self.send_header('Content-Type',kind)
                self.send_header('Content-Length',str(len(body)));self.send_header('Cache-Control','no-store');self.end_headers()
                try: self.wfile.write(body)
                except (BrokenPipeError,ConnectionResetError): pass
        srv=ThreadingHTTPServer(('0.0.0.0',args.port),Handler);srv.daemon_threads=True
        threading.Thread(target=srv.serve_forever,daemon=True).start()
        if args.mode=='demo':
            spawn('camera',['rosrun','uav_tracking','camera_node.py','_source:=video',
                            '_video_path:='+str(Path(args.video).resolve()),'_fps:=10','_loop:=true'])
        spawn('detector',['rosrun','uav_tracking','detector_node.py','_model_path:='+str(model),
                          '_image_topic:='+topic,'_imgsz:=320','_conf_thres:=0.1'])
        spawn('tracker',['rosrun','uav_tracking','visual_tracker_node.py','_image_topic:='+topic])
        if args.mode=='demo': spawn('state',['rosrun','uav_tracking','state_machine_node.py'])
        MANIFEST.write_text(json.dumps(dict(pid=os.getpid(),start=process_start(os.getpid()),
            mode=args.mode,url='http://127.0.0.1:%d/'%args.port,master=master)))
        print('控制台已启动',flush=True)
        while not shutdown.wait(.25):
            if any(proc.poll() is not None for _,proc in children):
                print('子进程退出，页面保留供查看错误日志。',flush=True);shutdown.wait();break
    finally:
        if srv: srv.shutdown();srv.server_close()
        for _,proc in reversed(children):
            if proc.poll() is None: os.killpg(proc.pid,signal.SIGTERM)
        for _,proc in reversed(children):
            try: proc.wait(timeout=5)
            except subprocess.TimeoutExpired: os.killpg(proc.pid,signal.SIGKILL);proc.wait()
        for file in logs: file.close()
        current=session()
        if current and current['pid']==os.getpid(): MANIFEST.unlink()
        lock.close()
    return 0

if __name__=='__main__':
    try: sys.exit(main())
    except Exception as exc: print('启动失败：'+str(exc),file=sys.stderr,flush=True);sys.exit(1)
