"""Regression tests for invalid numeric data and slow-inference frame handling."""
import threading
from types import SimpleNamespace
import importlib.util
from pathlib import Path
import numpy as np
import pytest
import detector
import visual_tracker
from datatypes import DetectedTarget

@pytest.mark.parametrize('value',[float('nan'),float('inf'),-.1,1.1,True])
def test_detector_rejects_bad_threshold(value):
    with pytest.raises(ValueError): detector.YoloDetector(conf_thres=value)

@pytest.mark.parametrize('kwargs',[{'track_buffer':-1},{'match_thresh':float('nan')},
                                 {'track_low_thresh':.8,'track_high_thresh':.5}])
def test_tracker_rejects_bad_parameters(kwargs):
    with pytest.raises(ValueError): visual_tracker.BotSortTracker(**kwargs)

@pytest.mark.parametrize('bbox',[(0.,0.,float('nan'),10.),(0.,0.,0.,10.),np.array(2.)])
def test_bad_detection_does_not_modify_tracker(bbox):
    tracker=visual_tracker.BotSortTracker()
    with pytest.raises(ValueError):
        tracker.track([SimpleNamespace(bbox=bbox,confidence=.9,class_id=0)])
    assert tracker.track_count == 0

def test_onboard_skips_bad_detection(monkeypatch):
    monkeypatch.setattr(visual_tracker,'ONBOARD',True)
    tracker=visual_tracker.BotSortTracker()
    with pytest.warns(RuntimeWarning):
        out=tracker.track([SimpleNamespace(bbox=(0,0,-1,2),confidence=.9,class_id=0)])
    assert out == [] and tracker.track_count == 0

def test_newest_image_replaces_backlog_during_slow_inference():
    pytest.importorskip('rospy')
    path=Path(__file__).resolve().parents[2]/'catkin_ws/src/uav_tracking/scripts/detector_node.py'
    spec=importlib.util.spec_from_file_location('m4_worker_review',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    node=module.DetectorNode.__new__(module.DetectorNode)
    node._condition=threading.Condition();node._pending_image=None;node._stopping=False
    entered=threading.Event();release=threading.Event();done=threading.Event();seen=[]
    def process(message):
        seen.append(message)
        if message == 1:
            entered.set();assert release.wait(3)
        else: done.set()
    node._process_image=process
    worker=threading.Thread(target=node._run_worker,daemon=True);worker.start()
    try:
        node.on_image(1);assert entered.wait(3)
        node.on_image(2);node.on_image(3)
        release.set();assert done.wait(3)
        assert seen == [1,3]
    finally:
        release.set();node.shutdown();worker.join(3)
    assert not worker.is_alive()
