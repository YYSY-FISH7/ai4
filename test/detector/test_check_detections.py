"""Slow inference may extend sampling; missing messages must still time out."""
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import pytest


@pytest.mark.parametrize('publish,expected', [(True, 0), (False, 1)])
def test_bounded_sampling_preserves_required_message_count(monkeypatch, publish, expected):
    pytest.importorskip('rospy')
    path = Path(__file__).parent/'e2e_test/check_detections.py'
    spec = importlib.util.spec_from_file_location('m4_detection_checker_review', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    checker = module.Checker.__new__(module.Checker)
    checker.mode = 'empty'
    checker.duration = 6.0
    checker.timeout = 30.0
    checker.min_msgs = 5
    checker.count = checker.nonempty = 0
    clock = [0.0]
    monkeypatch.setattr(module, 'time', SimpleNamespace(monotonic=lambda: clock[0]))
    monkeypatch.setattr(module.rospy, 'loginfo', lambda *_: None)
    monkeypatch.setattr(module.rospy, 'is_shutdown', lambda: False)

    def tick(_):
        clock[0] += 1
        if publish and clock[0] % 3 == 0:
            checker.count += 1

    monkeypatch.setattr(module.rospy, 'sleep', tick)
    assert checker.run() == expected
    if publish:
        assert clock[0] == 15 and checker.count == 5
    else:
        assert clock[0] == 30 and checker.count == 0
