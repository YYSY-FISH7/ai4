"""Regression checks for the M4 review findings; no ROS master required."""
import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest
import detector
from datatypes import DetectedTarget
from visual_tracker import BotSortTracker, DEFAULT_TRACK_LOW_THRESH

def det(score=.9, cls=0):
    return DetectedTarget(bbox=(10.,10.,60.,60.), confidence=score, class_id=cls)

def test_detector_keeps_low_score_measurements_needed_by_tracker():
    assert detector.DEFAULT_CONF_THRES <= DEFAULT_TRACK_LOW_THRESH
    tracker=BotSortTracker()
    first=tracker.track([det()])[0]
    second=tracker.track([det(.3)])[0]
    assert first.id==second.id

def test_class_change_does_not_reuse_another_object_id():
    tracker=BotSortTracker()
    first=tracker.track([det(cls=0)])[0]
    second=tracker.track([det(cls=7)])[0]
    assert first.id!=second.id

def test_same_class_keeps_id():
    tracker=BotSortTracker()
    assert tracker.track([det(cls=7)])[0].id==tracker.track([det(cls=7)])[0].id

def test_relay_rejects_names_resolving_to_same_topic(monkeypatch):
    pytest.importorskip('rospy')
    scripts=Path(__file__).resolve().parents[2]/'catkin_ws/src/uav_tracking/scripts'
    spec=importlib.util.spec_from_file_location('m4_camera_regression',scripts/'camera_node.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    monkeypatch.setattr(module.rospy,'get_param',lambda *_:'camera/image_raw')
    monkeypatch.setattr(module.rospy,'resolve_name',lambda name:'/'+name.lstrip('/'))
    monkeypatch.setattr(module.rospy,'logwarn',lambda *_:None)
    monkeypatch.setattr(module.rospy,'Subscriber',lambda *_args,**_kw:pytest.fail('self-relay subscribed'))
    node=SimpleNamespace(image_topic='/camera/image_raw')
    with pytest.raises(ValueError,match='same topic'):
        module.CameraNode._init_gazebo_relay(node)
