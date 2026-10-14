"""模块 2 纯算法单元测试。"""

import numpy as np
import pytest

import tracker
from datatypes import Track, TrackState


def test_track_state_is_available_with_required_fields():
    state = TrackState(1, np.zeros(6), np.eye(6), 1, 0.0)
    assert state.id == 1
    assert state.state.shape == (6,)
    assert state.cov.shape == (6, 6)


def test_track_state_converts_to_pure_track_before_ros_packaging():
    state = TrackState(4, np.array([1.0, 2.0, 3.0, 0.1, 0.2, 0.3]), np.eye(6), 7, 12.5)
    track = tracker.track_state_to_track(state)
    assert isinstance(track, Track)
    assert track.id == 4
    assert track.position == (1.0, 2.0, 3.0)
    assert track.velocity == (0.1, 0.2, 0.3)
    assert len(track.covariance) == 36
    assert track.age == 7


def test_new_measurement_creates_track_with_zero_velocity():
    kalman = tracker.KalmanTracker()
    tracks = kalman.step([np.array([1.0, 2.0, 3.0])], dt=1.0, timestamp=10.0)
    assert len(tracks) == 1
    assert tracks[0].id == 0
    assert np.allclose(tracks[0].state, [1.0, 2.0, 3.0, 0.0, 0.0, 0.0])
    assert tracks[0].age == 1
    assert tracks[0].last_update == 10.0


def test_predict_uses_constant_velocity_model():
    kalman = tracker.KalmanTracker()
    kalman.step([np.array([0.0, 0.0, 0.0])], dt=1.0)
    kalman.tracks[0].state[3:] = [1.0, -2.0, 0.5]
    kalman.predict(2.0)
    assert np.allclose(kalman.tracks[0].state[:3], [2.0, -4.0, 1.0])
    assert np.allclose(kalman.tracks[0].state[3:], [1.0, -2.0, 0.5])
    assert kalman.tracks[0].age == 2


def test_associate_is_nearest_neighbor_and_one_to_one():
    kalman = tracker.KalmanTracker(association_threshold=3.0)
    kalman.step([np.array([0.0, 0.0, 0.0]), np.array([10.0, 0.0, 0.0])], 1.0)
    result = kalman.associate(
        [np.array([9.0, 0.0, 0.0]), np.array([0.5, 0.0, 0.0])]
    )
    assert result == {0: 1, 1: 0}


def test_out_of_gate_measurement_creates_new_track():
    kalman = tracker.KalmanTracker(association_threshold=1.0)
    kalman.step([np.array([0.0, 0.0, 0.0])], 1.0)
    tracks = kalman.step([np.array([5.0, 0.0, 0.0])], 1.0)
    assert len(tracks) == 2
    assert [track.id for track in tracks] == [0, 1]


def test_unmatched_track_is_kept_then_deleted_after_timeout():
    kalman = tracker.KalmanTracker(max_missed_frames=2)
    kalman.step([np.array([0.0, 0.0, 0.0])], 1.0)
    kalman.step([], 1.0)
    assert len(kalman.tracks) == 1
    assert kalman.tracks[0].age == 2
    kalman.step([], 1.0)
    assert len(kalman.tracks) == 1
    kalman.step([], 1.0)
    assert kalman.tracks == []


def test_update_reduces_position_error():
    kalman = tracker.KalmanTracker(measurement_noise=0.1)
    kalman.step([np.array([0.0, 0.0, 0.0])], 1.0)
    kalman.tracks[0].state[:3] = [1.0, 1.0, 1.0]
    before = np.linalg.norm(kalman.tracks[0].state[:3])
    kalman.associate([np.array([0.0, 0.0, 0.0])])
    kalman.update(np.array([0.0, 0.0, 0.0]))
    assert np.linalg.norm(kalman.tracks[0].state[:3]) < before


@pytest.mark.parametrize("dt", [0.0, -1.0, "bad"])
def test_invalid_dt_raises_in_dev(dt):
    kalman = tracker.KalmanTracker()
    with pytest.raises(ValueError):
        kalman.predict(dt)


def test_empty_tracker_association_returns_empty():
    assert tracker.KalmanTracker().associate([]) == {}
