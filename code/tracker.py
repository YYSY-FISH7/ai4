"""模块 2：航迹关联与六维恒速卡尔曼滤波。

本文件只包含纯算法，不导入 ``rospy`` 或任何 ROS 消息。ROS 话题消息与
``TrackState``/``Track`` 的转换由 ``tracker_node.py`` 负责。

算法流程：

``predict(dt)`` -> ``associate(measurements)`` -> ``update(measurement)``

``step`` 是供节点调用的管理入口，负责执行上述流程、创建新航迹、记录未匹配
帧数并删除超时航迹。状态量为 ``[x, y, z, vx, vy, vz]``，量测为三维位置。
"""
from __future__ import annotations

import warnings
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np

from config import (
    ONBOARD,
    TRACKER_ASSOCIATION_THRESHOLD,
    TRACKER_INITIAL_COVARIANCE,
    TRACKER_MAX_MISSED_FRAMES,
    TRACKER_MEASUREMENT_NOISE,
    TRACKER_PROCESS_NOISE,
)
from datatypes import Track, TrackState

__all__ = ["KalmanTracker", "track_state_to_track"]

_STATE_DIM = 6
_MEASUREMENT_DIM = 3


def track_state_to_track(track_state: TrackState) -> Track:
    """将内部 ``TrackState`` 转为 ROS 无关的纯发布 ``Track``。"""
    if not isinstance(track_state, TrackState):
        raise TypeError("track_state must be TrackState")
    return Track(
        id=int(track_state.id),
        position=tuple(float(value) for value in track_state.state[:3]),
        velocity=tuple(float(value) for value in track_state.state[3:6]),
        covariance=tuple(float(value) for value in track_state.cov.reshape(-1)),
        age=int(track_state.age),
    )


def _reject(message: str) -> bool:
    """按项目运行阶段处理非法算法参数。"""
    if ONBOARD:
        warnings.warn(
            "[tracker] %s；上机阶段按安全默认值处理" % message,
            RuntimeWarning,
            stacklevel=2,
        )
        return True
    raise ValueError("[tracker] " + message)


def _is_number(value: object) -> bool:
    return isinstance(value, (int, float, np.integer, np.floating)) and not isinstance(
        value, (bool, np.bool_)
    )


def _as_vector(value: object, name: str, size: int) -> Optional[np.ndarray]:
    """将量测/状态向量校验并转换为独立的 float 数组。"""
    try:
        array = np.asarray(value, dtype=float)
    except (TypeError, ValueError):
        if _reject("%s 必须可转换为数值向量，实际为 %r" % (name, value)):
            return None
        return None
    if array.shape != (size,) or not np.all(np.isfinite(array)):
        if _reject("%s 必须为形状 (%d,) 的有限数值向量，实际形状为 %r" % (name, size, array.shape)):
            return None
    return array.copy()


def _as_matrix(value: object, name: str, shape: Tuple[int, int]) -> np.ndarray:
    """将标量或矩阵配置转换为指定形状的 float 矩阵。"""
    if _is_number(value):
        scalar = float(value)
        if scalar < 0 or not np.isfinite(scalar):
            if _reject("%s 必须为非负有限数值，实际为 %r" % (name, value)):
                return np.eye(shape[0], dtype=float)
        return np.eye(shape[0], dtype=float) * scalar
    try:
        matrix = np.asarray(value, dtype=float)
    except (TypeError, ValueError):
        if _reject("%s 必须为标量或矩阵，实际为 %r" % (name, value)):
            return np.eye(shape[0], dtype=float)
        return np.eye(shape[0], dtype=float)
    if matrix.shape != shape or not np.all(np.isfinite(matrix)):
        if _reject("%s 必须为形状 %r 的有限矩阵，实际形状为 %r" % (name, shape, matrix.shape)):
            return np.eye(shape[0], dtype=float)
    return matrix.copy()


class KalmanTracker:
    """多目标三维恒速卡尔曼跟踪器。

    参数默认从 ``code.config`` 集中读取。``association_threshold`` 是位置欧氏
    距离门限；``max_missed_frames`` 是连续未关联帧数上限；噪声参数既可传标量
    （乘单位阵），也可传相应维度矩阵。

    ``associate`` 返回 ``{track_id: measurement_index}``，只包含门限内成功匹配。
    未匹配量测和航迹由 ``step`` 处理。
    """

    def __init__(
        self,
        association_threshold: float = TRACKER_ASSOCIATION_THRESHOLD,
        max_missed_frames: int = TRACKER_MAX_MISSED_FRAMES,
        process_noise: object = TRACKER_PROCESS_NOISE,
        measurement_noise: object = TRACKER_MEASUREMENT_NOISE,
        initial_covariance: object = TRACKER_INITIAL_COVARIANCE,
    ) -> None:
        if not _is_number(association_threshold) or association_threshold <= 0:
            if _reject("association_threshold 必须为正数，实际为 %r" % (association_threshold,)):
                association_threshold = TRACKER_ASSOCIATION_THRESHOLD
        if (
            not isinstance(max_missed_frames, (int, np.integer))
            or isinstance(max_missed_frames, (bool, np.bool_))
            or max_missed_frames < 0
        ):
            if _reject("max_missed_frames 必须为非负整数，实际为 %r" % (max_missed_frames,)):
                max_missed_frames = TRACKER_MAX_MISSED_FRAMES

        self.association_threshold = float(association_threshold)
        self.max_missed_frames = int(max_missed_frames)
        self.process_noise = process_noise
        self.measurement_noise = _as_matrix(
            measurement_noise, "measurement_noise", (_MEASUREMENT_DIM, _MEASUREMENT_DIM)
        )
        self.initial_covariance = _as_matrix(
            initial_covariance, "initial_covariance", (_STATE_DIM, _STATE_DIM)
        )
        self.tracks: List[TrackState] = []
        self._missed_frames: Dict[int, int] = {}
        self._next_id = 0
        self._associated_track_id: Optional[int] = None

    @property
    def active_tracks(self) -> List[TrackState]:
        """返回当前航迹列表的浅拷贝，避免调用方改动容器。"""
        return list(self.tracks)

    def _transition_matrix(self, dt: float) -> np.ndarray:
        matrix = np.eye(_STATE_DIM, dtype=float)
        matrix[:3, 3:] = np.eye(3, dtype=float) * dt
        return matrix

    def _process_covariance(self, dt: float) -> np.ndarray:
        """由标量过程噪声生成恒速模型的离散过程协方差。"""
        if _is_number(self.process_noise):
            q = float(self.process_noise)
            if q < 0 or not np.isfinite(q):
                if _reject("process_noise 必须为非负有限数值，实际为 %r" % (self.process_noise,)):
                    q = float(TRACKER_PROCESS_NOISE)
            block = np.array(
                [[dt ** 4 / 4.0, dt ** 3 / 2.0], [dt ** 3 / 2.0, dt ** 2]],
                dtype=float,
            ) * q
            covariance = np.zeros((_STATE_DIM, _STATE_DIM), dtype=float)
            for axis in range(3):
                covariance[axis, axis] = block[0, 0]
                covariance[axis, axis + 3] = block[0, 1]
                covariance[axis + 3, axis] = block[1, 0]
                covariance[axis + 3, axis + 3] = block[1, 1]
            return covariance
        matrix = _as_matrix(self.process_noise, "process_noise", (_STATE_DIM, _STATE_DIM))
        return matrix

    def predict(self, dt: float) -> None:
        """预测所有当前航迹状态。"""
        if not _is_number(dt) or not np.isfinite(float(dt)) or float(dt) <= 0:
            if _reject("predict: dt 必须为正的有限数值，实际为 %r" % (dt,)):
                return
        dt = float(dt)
        transition = self._transition_matrix(dt)
        process_covariance = self._process_covariance(dt)
        for track in self.tracks:
            track.state = transition.dot(track.state)
            track.cov = transition.dot(track.cov).dot(transition.T) + process_covariance
            track.cov = (track.cov + track.cov.T) * 0.5
            track.age += 1
        self._associated_track_id = None

    def associate(self, measurements: List[np.ndarray]) -> dict:
        """以贪心最近邻方式建立航迹到量测的一对一关联。"""
        if not isinstance(measurements, list):
            if _reject("associate: measurements 必须为 list，实际为 %r" % (measurements,)):
                return {}
        normalized = []
        for index, measurement in enumerate(measurements):
            vector = _as_vector(measurement, "measurements[%d]" % index, _MEASUREMENT_DIM)
            if vector is not None:
                normalized.append((index, vector))
        if not self.tracks or not normalized:
            self._associated_track_id = None
            return {}

        candidates = []
        for track in self.tracks:
            for original_index, measurement in normalized:
                distance = float(np.linalg.norm(track.state[:3] - measurement))
                if distance <= self.association_threshold:
                    candidates.append((distance, track.id, original_index))
        candidates.sort(key=lambda item: (item[0], item[1], item[2]))
        result: Dict[int, int] = {}
        used_tracks = set()
        used_measurements = set()
        for _, track_id, measurement_index in candidates:
            if track_id in used_tracks or measurement_index in used_measurements:
                continue
            result[track_id] = measurement_index
            used_tracks.add(track_id)
            used_measurements.add(measurement_index)
        self._associated_track_id = next(iter(result)) if len(result) == 1 else None
        return result

    def update(self, measurement: np.ndarray) -> None:
        """用三维位置量测更新关联航迹。

        通常在 ``associate`` 后调用；只有一个关联结果时使用该航迹。若当前
        没有航迹则建立一条新航迹，便于单轨迹单元测试和简单调用。
        """
        vector = _as_vector(measurement, "measurement", _MEASUREMENT_DIM)
        if vector is None:
            return
        track = None
        if self._associated_track_id is not None:
            track = self._find_track(self._associated_track_id)
        if track is None and len(self.tracks) == 1:
            track = self.tracks[0]
        if track is None:
            track = self._create_track(vector, timestamp=0.0)
            self._associated_track_id = track.id
            return
        measurement_matrix = np.zeros((_MEASUREMENT_DIM, _STATE_DIM), dtype=float)
        measurement_matrix[:, :3] = np.eye(3, dtype=float)
        innovation = vector - measurement_matrix.dot(track.state)
        innovation_covariance = (
            measurement_matrix.dot(track.cov).dot(measurement_matrix.T) + self.measurement_noise
        )
        try:
            gain = np.linalg.solve(
                innovation_covariance,
                track.cov.dot(measurement_matrix.T).T,
            ).T
        except np.linalg.LinAlgError:
            if _reject("update: 量测协方差不可逆"):
                gain = np.zeros((_STATE_DIM, _MEASUREMENT_DIM), dtype=float)
        track.state = track.state + gain.dot(innovation)
        identity = np.eye(_STATE_DIM, dtype=float)
        residual = identity - gain.dot(measurement_matrix)
        # Joseph 形式保持协方差半正定，适合长时间运行。
        track.cov = (
            residual.dot(track.cov).dot(residual.T)
            + gain.dot(self.measurement_noise).dot(gain.T)
        )
        track.cov = (track.cov + track.cov.T) * 0.5
        self._missed_frames[track.id] = 0
        self._associated_track_id = track.id

    def step(
        self,
        measurements: List[np.ndarray],
        dt: float,
        timestamp: Optional[float] = None,
    ) -> List[TrackState]:
        """处理一帧量测并返回当前航迹。

        ``timestamp`` 由节点用消息时间戳传入；省略时沿用最近更新时间。空量测
        也会推进预测和丢失计数，最终按 ``max_missed_frames`` 删除航迹。
        """
        if not isinstance(measurements, list):
            if _reject("step: measurements 必须为 list，实际为 %r" % (measurements,)):
                measurements = []
        if not _is_number(dt) or not np.isfinite(float(dt)) or float(dt) <= 0:
            if _reject("step: dt 必须为正的有限数值，实际为 %r" % (dt,)):
                return self.active_tracks
        if timestamp is not None and (
            not _is_number(timestamp) or not np.isfinite(float(timestamp))
        ):
            if _reject("step: timestamp 必须为有限数值或 None，实际为 %r" % (timestamp,)):
                timestamp = None

        self.predict(float(dt))
        associations = self.associate(measurements)
        associated_measurements = set(associations.values())
        matched_track_ids = set(associations)

        for track_id, measurement_index in associations.items():
            track = self._find_track(track_id)
            if track is None:
                continue
            self._associated_track_id = track_id
            self.update(measurements[measurement_index])
            if timestamp is not None:
                track.last_update = float(timestamp)

        for track in self.tracks:
            if track.id not in matched_track_ids:
                self._missed_frames[track.id] = self._missed_frames.get(track.id, 0) + 1

        for index, measurement in enumerate(measurements):
            if index not in associated_measurements:
                vector = _as_vector(measurement, "measurements[%d]" % index, _MEASUREMENT_DIM)
                if vector is not None:
                    self._create_track(vector, timestamp=timestamp)

        self.tracks = [
            track
            for track in self.tracks
            if self._missed_frames.get(track.id, 0) <= self.max_missed_frames
        ]
        active_ids = {track.id for track in self.tracks}
        self._missed_frames = {
            track_id: missed
            for track_id, missed in self._missed_frames.items()
            if track_id in active_ids
        }
        self._associated_track_id = None
        return self.active_tracks

    def _find_track(self, track_id: int) -> Optional[TrackState]:
        return next((track for track in self.tracks if track.id == track_id), None)

    def _create_track(self, position: np.ndarray, timestamp: Optional[float]) -> TrackState:
        state = np.zeros(_STATE_DIM, dtype=float)
        state[:3] = position
        track = TrackState(
            id=self._next_id,
            state=state,
            cov=self.initial_covariance.copy(),
            age=1,
            last_update=float(timestamp) if timestamp is not None else 0.0,
        )
        self._next_id += 1
        self.tracks.append(track)
        self._missed_frames[track.id] = 0
        return track
