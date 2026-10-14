"""模块 3 ROS 节点适配测试；不启动 ROS master 或完整飞控链。"""

import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest

rospy = pytest.importorskip("rospy")
pytest.importorskip("mavros_msgs.msg")
pytest.importorskip("uav_tracking.msg")

from geometry_msgs.msg import PoseStamped  # noqa: E402
from mavros_msgs.msg import PositionTarget  # noqa: E402
from uav_tracking.msg import Track as TrackMsg, TrackArray  # noqa: E402

from datatypes import Pose, PositionCommand, Track, Waypoint  # noqa: E402


_NODE_PATH = Path(__file__).resolve().parents[2] / "catkin_ws/src/uav_tracking/scripts/navigator_node.py"
_SPEC = importlib.util.spec_from_file_location("navigator_node_under_test", str(_NODE_PATH))
navigator_node = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(navigator_node)


def _message_track(track_id=4, age=9):
    msg = TrackMsg()
    msg.id = track_id
    msg.position = [1.0, 2.0, 3.0]
    msg.velocity = [0.1, 0.2, 0.3]
    msg.covariance = [float(i) for i in range(36)]
    msg.age = age
    return msg


def test_tracks_from_msg_converts_track_array():
    msg = TrackArray()
    msg.tracks.append(_message_track())
    tracks = navigator_node.tracks_from_msg(msg)
    assert tracks == [
        Track(4, (1.0, 2.0, 3.0), (0.1, 0.2, 0.3), tuple(float(i) for i in range(36)), 9)
    ]


def test_empty_track_array_converts_to_empty_list():
    assert navigator_node.tracks_from_msg(TrackArray()) == []


def test_pose_from_msg_converts_position_only():
    msg = PoseStamped()
    msg.pose.position.x = 4.0
    msg.pose.position.y = -2.0
    msg.pose.position.z = 1.5
    assert navigator_node.pose_from_msg(msg) == Pose(
        position=(4.0, -2.0, 1.5), orientation=(0.0, 0.0, 0.0, 0.0)
    )


def test_pure_command_is_adapted_to_position_target():
    command = PositionCommand(1, 3576, position=(4.0, -2.0, 1.5), yaw=0.25)
    msg = navigator_node.position_command_to_position_target(command)
    assert msg.coordinate_frame == 1
    assert msg.type_mask == 3576
    assert (msg.position.x, msg.position.y, msg.position.z) == (4.0, -2.0, 1.5)
    assert msg.yaw == pytest.approx(0.25)


def test_position_target_uses_local_frame_and_position_only_mask():
    msg = navigator_node.waypoint_to_position_target(
        Waypoint(position=(1.0, 2.0, 3.0), yaw=0.0)
    )
    assert msg.coordinate_frame == PositionTarget.FRAME_LOCAL_NED
    assert msg.type_mask == navigator_node.POSITION_ONLY_TYPE_MASK
    assert msg.position.x == pytest.approx(1.0)
    assert msg.position.y == pytest.approx(2.0)
    assert msg.position.z == pytest.approx(3.0)
    assert msg.type_mask & PositionTarget.IGNORE_VX
    assert msg.type_mask & PositionTarget.IGNORE_YAW_RATE


def test_topics_are_intermediate_radar_only_and_rate_is_50hz():
    assert navigator_node.TOPIC_TRACKS == "/radar/tracks"
    assert navigator_node.TOPIC_POSE == "/mavros/local_position/pose"
    assert navigator_node.TOPIC_OUTPUT == "/ctrl/radar"
    assert navigator_node.TOPIC_OUTPUT != "/mavros/setpoint_raw/local"
    from config import NAVIGATOR_RATE_HZ

    assert NAVIGATOR_RATE_HZ == 50.0


@pytest.mark.parametrize("send_empty", [False, True], ids=["upstream_silent", "empty_array"])
def test_valid_target_then_loss_enters_hover(monkeypatch, send_empty):
    # Exercise the real node callbacks with ROS messages, but no master or real timer.
    clock = [10.0]
    published = []
    monkeypatch.setattr(rospy.Time, "now", lambda: rospy.Time.from_sec(clock[0]))
    monkeypatch.setattr(rospy, "get_param", lambda name, default: default)
    monkeypatch.setattr(rospy, "Publisher", lambda *a, **kw: SimpleNamespace(publish=published.append))
    monkeypatch.setattr(rospy, "Subscriber", lambda *a, **kw: None)
    monkeypatch.setattr(rospy, "Timer", lambda *a, **kw: None)
    monkeypatch.setattr(rospy, "loginfo", lambda *a, **kw: None)
    instance = navigator_node.NavigatorNode()
    pose = PoseStamped()
    pose.pose.position.x, pose.pose.position.y, pose.pose.position.z = (4.0, -2.0, 1.5)
    instance.on_pose(pose)
    msg = TrackArray()
    msg.tracks.append(_message_track())
    instance.on_tracks(msg)
    instance.on_timer(None)
    target = published[-1]
    assert (target.position.x, target.position.y, target.position.z) == (1.0, 2.0, 3.0)

    clock[0] = 10.0 + instance.hold_timeout / 2.0
    if send_empty:
        instance.on_tracks(TrackArray())
    instance.on_timer(None)
    assert instance._last_valid_time.to_sec() == 10.0
    assert published[-1] == target

    for elapsed in (instance.hold_timeout + 0.01, instance.hold_timeout + 1.0):
        clock[0] = 10.0 + elapsed
        if send_empty:
            instance.on_tracks(TrackArray())
        instance.on_timer(None)
        hover = published[-1]
        assert (hover.position.x, hover.position.y, hover.position.z) == (4.0, -2.0, 1.5)
        assert hover.coordinate_frame == PositionTarget.FRAME_LOCAL_NED
        assert hover.type_mask == navigator_node.POSITION_ONLY_TYPE_MASK
        assert instance._last_valid_time.to_sec() == 10.0
    assert bool(instance._tracks) is not send_empty
