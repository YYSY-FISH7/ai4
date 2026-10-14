"""模块 2 ROS 节点时间处理测试；不启动 ROS master。"""
import importlib.util
from pathlib import Path

import pytest

rospy = pytest.importorskip("rospy")
pytest.importorskip("uav_tracking.msg")

from geometry_msgs.msg import PointStamped  # noqa: E402
from uav_tracking.msg import CentroidArray  # noqa: E402


_NODE_PATH = Path(__file__).resolve().parents[2] / "catkin_ws/src/uav_tracking/scripts/tracker_node.py"
_SPEC = importlib.util.spec_from_file_location("tracker_node_under_test", str(_NODE_PATH))
tracker_node = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(tracker_node)


class _Publisher:
    def __init__(self):
        self.messages = []

    def publish(self, msg):
        self.messages.append(msg)


class _TrackerSpy:
    def __init__(self):
        self.calls = []
        self.active_tracks = []
        self.association_threshold = 2.0
        self.max_missed_frames = 5

    def step(self, measurements, dt, timestamp=None):
        self.calls.append((measurements, dt, timestamp))
        return self.active_tracks


def _centroids(stamp=None):
    msg = CentroidArray()
    if stamp is not None:
        point = PointStamped()
        point.header.stamp = rospy.Time.from_sec(stamp)
        point.point.x, point.point.y, point.point.z = (1.0, 2.0, 3.0)
        msg.centroids.append(point)
    return msg


def _make_node(monkeypatch, clock):
    publisher = _Publisher()
    spy = _TrackerSpy()
    monkeypatch.setattr(rospy.Time, "now", lambda: rospy.Time.from_sec(clock[0]))
    monkeypatch.setattr(rospy, "get_param", lambda name, default: default)
    monkeypatch.setattr(rospy, "Publisher", lambda *args, **kwargs: publisher)
    monkeypatch.setattr(rospy, "Subscriber", lambda *args, **kwargs: None)
    monkeypatch.setattr(rospy, "loginfo", lambda *args, **kwargs: None)
    monkeypatch.setattr(tracker_node, "KalmanTracker", lambda **kwargs: spy)
    return tracker_node.TrackerNode(), spy, publisher


def test_continuous_valid_inputs_use_receive_time_but_pass_measurement_stamp(monkeypatch):
    clock = [100.0]
    instance, spy, _ = _make_node(monkeypatch, clock)

    instance.on_centroids(_centroids(10.0))
    clock[0] = 100.1
    instance.on_centroids(_centroids(999.0))

    assert [call[1] for call in spy.calls] == pytest.approx([1.0 / 30.0, 0.1])
    assert [call[2] for call in spy.calls] == pytest.approx([10.0, 999.0])


@pytest.mark.parametrize("input_hz", [10.0, 30.0])
def test_empty_frames_and_recovery_do_not_double_count_dt(monkeypatch, input_hz):
    period = 1.0 / input_hz
    clock = [20.0]
    instance, spy, _ = _make_node(monkeypatch, clock)
    instance.on_centroids(_centroids(200.0))

    for index in range(1, 4):
        clock[0] = 20.0 + index * period
        instance.on_centroids(_centroids())
    clock[0] = 20.0 + 4 * period
    instance.on_centroids(_centroids(300.0))

    subsequent_dts = [call[1] for call in spy.calls[1:]]
    assert subsequent_dts == pytest.approx([period] * 4)
    assert sum(subsequent_dts) == pytest.approx(4 * period)
    assert spy.calls[-1][2] == pytest.approx(300.0)
    assert all(call[2] is None for call in spy.calls[1:4])


def test_complete_silence_recovery_uses_full_receive_time_gap(monkeypatch):
    clock = [50.0]
    instance, spy, _ = _make_node(monkeypatch, clock)
    instance.on_centroids(_centroids(500.0))

    clock[0] = 53.25
    instance.on_centroids(_centroids(503.25))

    assert len(spy.calls) == 2
    assert spy.calls[-1][1] == pytest.approx(3.25)


def test_repeated_ros_time_does_not_predict_default_dt(monkeypatch):
    clock = [70.0]
    instance, spy, publisher = _make_node(monkeypatch, clock)
    instance.on_centroids(_centroids(700.0))

    instance.on_centroids(_centroids(701.0))
    assert len(spy.calls) == 1
    assert len(publisher.messages) == 2

    clock[0] = 70.2
    instance.on_centroids(_centroids(702.0))
    assert [call[1] for call in spy.calls] == pytest.approx([1.0 / 30.0, 0.2])


def test_ros_time_rollback_rebases_without_nonpositive_or_default_dt(monkeypatch):
    clock = [90.0]
    instance, spy, publisher = _make_node(monkeypatch, clock)
    instance.on_centroids(_centroids(900.0))

    clock[0] = 80.0
    instance.on_centroids(_centroids(901.0))
    assert len(spy.calls) == 1
    assert len(publisher.messages) == 2

    clock[0] = 80.1
    instance.on_centroids(_centroids(902.0))
    assert [call[1] for call in spy.calls] == pytest.approx([1.0 / 30.0, 0.1])
    assert all(call[1] > 0.0 for call in spy.calls)
